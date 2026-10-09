"""Project-grain fixed-asset rollforward from published CAPEX and GL evidence."""
from __future__ import annotations

import pandas as pd


TOLERANCE = 0.05


def build_fixed_asset_lineage(
    journal: pd.DataFrame,
    capex_events: pd.DataFrame,
    config: dict,
    end_month: str,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Build a project register and event trace without inventing asset IDs.

    Project spend and go-live journals are source-tied. Depreciation is
    reconstructed at project level from approved project lives because the
    ledger posts one aggregated depreciation journal per entity, not one per
    asset. Opening PPE remains an entity-level pool.
    """
    end_month = str(end_month)
    required_journal = {"month", "entity", "division", "account", "journal_id", "journal_type", "debit", "credit"}
    missing = required_journal - set(journal.columns)
    if missing:
        raise ValueError(f"Missing fixed-asset journal fields: {sorted(missing)}")
    required_events = {"month", "project", "project_name", "entity", "division", "event", "amount", "go_live", "useful_life_months"}
    missing = required_events - set(capex_events.columns)
    if missing:
        raise ValueError(f"Missing CAPEX event fields: {sorted(missing)}")
    if not pd.notna(journal[["debit", "credit"]]).all().all():
        raise ValueError("Missing fixed-asset journal amount")

    close = pd.Period(end_month, freq="M")
    journal = journal.loc[journal.month.astype(str).le(end_month)].copy()
    events = capex_events.loc[capex_events.month.astype(str).le(end_month)].copy()
    events["amount"] = pd.to_numeric(events.amount, errors="coerce")
    if events.amount.isna().any() or not events.amount.map(lambda value: pd.notna(value) and abs(float(value)) < float("inf")).all():
        raise ValueError("CAPEX event amount must be finite")
    if events.duplicated(["month", "project", "event"]).any():
        raise ValueError("CAPEX project events must be unique by month, project and event")

    project_config = {str(project["id"]): project for project in config.get("capex_projects", [])}
    if set(events.project.astype(str)) - set(project_config):
        raise ValueError("CAPEX events contain project IDs absent from configuration")

    event_rows: list[dict] = []
    for event in events.sort_values(["month", "project", "event"], kind="stable").itertuples(index=False):
        project = str(event.project)
        if str(event.event) == "SPEND":
            journal_id = f"CAPEX-{event.month}-{project}"
            debit_account, credit_account = "1510_CIP", "1000_CASH"
        elif str(event.event) == "GO_LIVE":
            journal_id = f"GOLIVE-{event.month}-{project}"
            debit_account, credit_account = "1500_PPE", "1510_CIP"
        else:
            raise ValueError(f"Unsupported CAPEX event type: {event.event}")
        source = journal.loc[journal.journal_id.astype(str).eq(journal_id)]
        debit = float(source.loc[source.account.eq(debit_account), "debit"].sum())
        credit = float(source.loc[source.account.eq(credit_account), "credit"].sum())
        if abs(debit - float(event.amount)) > TOLERANCE or abs(credit - float(event.amount)) > TOLERANCE:
            raise RuntimeError(f"CAPEX source event does not match journal {journal_id}")
        event_rows.append({
            "month": str(event.month), "project": project, "project_name": str(event.project_name),
            "entity": str(event.entity), "division": str(event.division), "event": str(event.event),
            "amount": round(float(event.amount), 2), "journal_id": journal_id,
            "debit_account": debit_account, "credit_account": credit_account,
            "evidence_basis": "Posted project journal; SPEND is cash, GO_LIVE is a non-cash CIP-to-PPE transfer",
        })
    event_detail = pd.DataFrame(event_rows)

    opening = journal.loc[journal.journal_type.eq("opening")]
    opening_ppe = opening.loc[opening.account.eq("1500_PPE")].groupby("entity").debit.sum().to_dict()
    opening_accum_dep = opening.loc[opening.account.eq("1590_ACCUM_DEP")].groupby("entity").credit.sum().to_dict()
    journal_months = sorted(journal.month.astype(str).unique())
    if not journal_months:
        raise ValueError("No fixed-asset journal periods available")
    first_period = pd.Period(journal_months[0], freq="M")
    months = pd.period_range(first_period, close, freq="M")
    if len(months) != len(journal_months):
        raise ValueError("Fixed-asset close journal must contain a contiguous monthly history")

    register_rows: list[dict] = []
    for project_id, project in sorted(project_config.items()):
        start = pd.Period(str(project["start"]), freq="M")
        live = start + int(project["build_months"]) - 1
        if start < first_period:
            # Older projects are represented in the opening PPE pool. The
            # source ledger does not provide a historical project subledger.
            continue
        rows = event_detail.loc[event_detail.project.eq(project_id)] if not event_detail.empty else pd.DataFrame()
        spend = float(rows.loc[rows.event.eq("SPEND"), "amount"].sum()) if not rows.empty else 0.0
        transferred = float(rows.loc[rows.event.eq("GO_LIVE"), "amount"].sum()) if not rows.empty else 0.0
        cip = spend - transferred
        gross_ppe = transferred
        in_service_months = max(close.ordinal - live.ordinal, 0) if live <= close else 0
        depreciation_monthly = float(project["budget"]) / int(project["useful_life_months"])
        depreciation_ltd = depreciation_monthly * in_service_months
        depreciation_current = depreciation_monthly if live < close else 0.0
        net_book_value = gross_ppe - depreciation_ltd
        if min(cip, gross_ppe, depreciation_ltd, net_book_value) < -TOLERANCE:
            raise RuntimeError(f"Negative project asset balance for {project_id}")
        state = "In service" if live <= close else ("Construction in progress" if spend > 0.0 else "Planned")
        depreciation_journal_id = f"DEP-{end_month}-{project['entity']}"
        register_rows.append({
            "month": end_month, "project": project_id, "project_name": str(project["name"]),
            "entity": str(project["entity"]), "division": str(project["division"]),
            "status": state, "budget": round(float(project["budget"]), 2),
            "cash_spend_ltd": round(spend, 2), "cip_closing": round(cip, 2),
            "go_live_month": str(live), "go_live_transfer_ltd": round(transferred, 2),
            "gross_ppe": round(gross_ppe, 2), "useful_life_months": int(project["useful_life_months"]),
            "depreciation_months": int(in_service_months),
            "depreciation_ltd_modeled": round(depreciation_ltd, 2),
            "depreciation_current_month_modeled": round(depreciation_current, 2),
            "net_book_value": round(net_book_value, 2),
            "project_carrying_value": round(cip + net_book_value, 2),
            "capacity_increase_pct": float(project.get("capacity_increase_pct", 0.0)),
            "depreciation_journal_id": depreciation_journal_id,
            "depreciation_basis": "Project depreciation reconstructed from budget / useful life; source journal is aggregated by entity",
        })

    register = pd.DataFrame(register_rows)
    # The opening asset pool and project assets must explain the gross PPE,
    # accumulated depreciation and CIP ledger at legal entity grain.
    actual_ppe = journal.loc[journal.account.eq("1500_PPE")].assign(
        balance=lambda frame: frame.debit - frame.credit
    ).groupby("entity").balance.sum().to_dict()
    actual_cip = journal.loc[journal.account.eq("1510_CIP")].assign(
        balance=lambda frame: frame.debit - frame.credit
    ).groupby("entity").balance.sum().to_dict()
    actual_accum_dep = journal.loc[journal.account.eq("1590_ACCUM_DEP")].assign(
        balance=lambda frame: frame.credit - frame.debit
    ).groupby("entity").balance.sum().to_dict()
    by_entity = register.groupby("entity") if not register.empty else None
    gross_gap = cip_gap = accum_dep_residual = 0.0
    for entity in set(actual_ppe) | set(actual_cip) | set(actual_accum_dep) | set(opening_ppe):
        project_rows = by_entity.get_group(entity) if by_entity is not None and entity in by_entity.groups else pd.DataFrame()
        expected_ppe = float(opening_ppe.get(entity, 0.0)) + float(project_rows.gross_ppe.sum() if not project_rows.empty else 0.0)
        expected_cip = float(project_rows.cip_closing.sum() if not project_rows.empty else 0.0)
        project_dep = float(project_rows.depreciation_ltd_modeled.sum() if not project_rows.empty else 0.0)
        prehistory_project_dep = 0.0
        for project in project_config.values():
            go_live = pd.Period(str(project["start"]), freq="M") + int(project["build_months"]) - 1
            if str(project["entity"]) == entity and pd.Period(str(project["start"]), freq="M") < first_period:
                in_service_months = sum(period > go_live for period in months)
                prehistory_project_dep += float(project["budget"]) / int(project["useful_life_months"]) * in_service_months
        expected_accum = (
            float(opening_accum_dep.get(entity, 0.0))
            + (float(opening_ppe.get(entity, 0.0)) / 144.0) * len(months)
            + project_dep
            + prehistory_project_dep
        )
        gross_gap = max(gross_gap, abs(expected_ppe - float(actual_ppe.get(entity, 0.0))))
        cip_gap = max(cip_gap, abs(expected_cip - float(actual_cip.get(entity, 0.0))))
        accum_dep_residual = max(accum_dep_residual, abs(expected_accum - float(actual_accum_dep.get(entity, 0.0))))

    depreciation_actual = journal.loc[journal.account.eq("6100_DEPRECIATION")].assign(
        actual=lambda frame: frame.debit - frame.credit
    ).groupby(["month", "entity"]).actual.sum().to_dict()
    depreciation_gaps: list[float] = []
    entities = sorted(journal.entity.astype(str).unique())
    for period in months:
        for entity in entities:
            expected = float(opening_ppe.get(entity, 0.0)) / 144.0
            for project in project_config.values():
                if str(project["entity"]) == entity:
                    go_live = pd.Period(str(project["start"]), freq="M") + int(project["build_months"]) - 1
                    if period > go_live:
                        expected += float(project["budget"]) / int(project["useful_life_months"])
            actual = float(depreciation_actual.get((str(period), entity), 0.0))
            depreciation_gaps.append(abs(actual - expected))
    depreciation_gap = max(depreciation_gaps, default=0.0)

    checks = {
        "fixed_asset_event_journal_max_gap": 0.0,
        "fixed_asset_gross_ppe_max_gap": round(gross_gap, 2),
        "fixed_asset_cip_max_gap": round(cip_gap, 2),
        "fixed_asset_accumulated_depreciation_max_gap": round(accum_dep_residual, 2),
        "fixed_asset_depreciation_max_gap": round(depreciation_gap, 2),
        "fixed_asset_project_rows": int(len(register)),
        "fixed_asset_event_rows": int(len(event_detail)),
        "passed": bool(max(gross_gap, cip_gap, accum_dep_residual, depreciation_gap) <= TOLERANCE),
    }
    return register, event_detail, checks
