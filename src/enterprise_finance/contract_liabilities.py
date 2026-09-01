from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd

from .provisions import chart_of_accounts_with_provisions, group_balance_sheet_with_provisions, legal_balance_sheet_with_provisions


CONTRACT_LIABILITY_ACCOUNT = "2300_CONTRACT_LIABILITIES"

SOFTWARE_RECURRING_SHARE = {
    "Platform": 0.92,
    "Security": 0.90,
    "Analytics": 0.84,
    "Automation": 0.82,
}

SOFTWARE_ADVANCE_SHARE = {
    "Essential": 0.35,
    "Professional": 0.55,
    "Premium": 0.72,
}

EVENT_ADVANCE_SHARE = {
    "Deployment & Integration": 0.35,
    "Training & Enablement": 0.25,
    "Customer Experience": 0.40,
    "Managed Programs": 0.30,
}


def _policy(config: dict) -> dict:
    cfg = config.get("contract_liabilities", {})
    return {
        "software_tier_share": {**SOFTWARE_ADVANCE_SHARE, **cfg.get("software_advance_share", {})},
        "events_family_share": {**EVENT_ADVANCE_SHARE, **cfg.get("events_advance_share", {})},
        "strategic_customer_uplift": float(cfg.get("strategic_customer_uplift", 0.08)),
        "growth_customer_discount": float(cfg.get("growth_customer_discount", 0.04)),
        "max_advance_share": float(cfg.get("max_advance_share", 0.85)),
    }


def chart_of_accounts_with_contracts() -> pd.DataFrame:
    base = chart_of_accounts_with_provisions()
    extra = pd.DataFrame([{
        "account": CONTRACT_LIABILITY_ACCOUNT,
        "statement": "Balance Sheet",
        "line": "Contract Liabilities",
        "account_type": "Liability",
    }])
    return pd.concat([base, extra], ignore_index=True).drop_duplicates("account", keep="last")


def strip_provision_journals(journal: pd.DataFrame) -> pd.DataFrame:
    """Return the legal ledger before ECL/inventory provision overlays."""
    if journal.empty:
        return journal.copy()
    ids = journal.journal_id.astype(str)
    provision = (
        ids.str.startswith("ECL-")
        | ids.str.startswith("ECLCLOSE-")
        | ids.str.startswith("INVPROV-")
        | ids.str.startswith("INVPROVCLOSE-")
    )
    return journal.loc[~provision].copy().reset_index(drop=True)


def _contract_share(row: pd.Series, config: dict) -> float:
    p = _policy(config)
    division = str(row.division)
    segment = str(row.get("customer_segment", "Core"))
    if division == "Software":
        recurring = float(SOFTWARE_RECURRING_SHARE.get(str(row.product_family), 0.85))
        share = recurring * float(p["software_tier_share"].get(str(row.quality_tier), 0.50))
    elif division == "Events":
        share = float(p["events_family_share"].get(str(row.product_family), 0.30))
    else:
        return 0.0
    if segment == "Strategic":
        share += p["strategic_customer_uplift"]
    elif segment == "Growth":
        share -= p["growth_customer_discount"]
    return float(np.clip(share, 0.0, p["max_advance_share"]))


def build_contract_commitments(operations: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Create one-month-ahead customer advance obligations from current contracts.

    Each service month's operating activity defines the active commercial contract
    base. A deterministic share of that base is billed one month in advance for
    the next service month. This creates a natural closing contract liability
    without using future actual revenue.
    """
    scope = operations[operations.division.isin(["Software", "Events"])].copy()
    if scope.empty:
        return pd.DataFrame()
    scope["advance_share"] = scope.apply(lambda row: _contract_share(row, config), axis=1)
    scope["advance_amount"] = scope.revenue.astype(float) * scope.advance_share
    scope = scope[scope.advance_amount.gt(0.005)].copy()
    scope["service_month"] = (pd.PeriodIndex(scope.month, freq="M") + 1).astype(str)
    grouped = scope.groupby([
        "month", "service_month", "entity", "division", "customer", "product",
        "customer_segment", "product_family", "quality_tier",
    ], as_index=False).agg(
        advance_amount=("advance_amount", "sum"),
        source_revenue=("revenue", "sum"),
        advance_share=("advance_share", "mean"),
    )
    return grouped


def _journal_row(
    *, month: str, entity: str, division: str, journal_id: str, journal_type: str,
    account: str, debit: float = 0.0, credit: float = 0.0,
    customer: str = "", product: str = "", description: str = "",
    cash_flow_category: str = "",
) -> dict:
    return {
        "month": month,
        "entity": entity,
        "division": division,
        "journal_id": journal_id,
        "journal_type": journal_type,
        "account": account,
        "debit": round(float(debit), 2),
        "credit": round(float(credit), 2),
        "counterparty": customer or "CUSTOMER",
        "description": description,
        "cash_flow_category": cash_flow_category,
        "product": product,
        "customer": customer,
    }


def apply_contract_liability_accounting(
    journal_pre_provision: pd.DataFrame,
    operations: pd.DataFrame,
    config: dict,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Replace Software/Events collection mechanics with advance-billing mechanics.

    Revenue journals are left untouched. Existing ordinary collection journals for
    Software and Events are removed and rebuilt after customer advances have been
    applied against AR. Hardware and Spare Parts settlement is unchanged.
    """
    journal = journal_pre_provision.copy()
    remove_collection = journal.journal_type.eq("collection") & journal.division.isin(["Software", "Events"])
    base = journal.loc[~remove_collection].copy().reset_index(drop=True)
    commitments = build_contract_commitments(operations, config)
    if commitments.empty:
        return base, commitments, pd.DataFrame()

    months = sorted(operations.month.unique())
    end_month = months[-1]
    sales = operations[operations.division.isin(["Software", "Events"])].groupby(
        ["month", "entity", "division", "customer", "product"], as_index=False
    ).revenue.sum()

    commitments_by_receipt = {m: g.copy() for m, g in commitments.groupby("month")}
    open_contracts: list[dict] = []
    ar_balance: dict[tuple[str, str], float] = defaultdict(float)
    new_rows: list[dict] = []
    schedule_rows: list[dict] = []

    for month in months:
        period = pd.Period(month, freq="M")
        month_sales = sales[sales.month.eq(month)].copy()
        invoice_available = {
            (str(r.entity), str(r.division), str(r.customer), str(r.product)): float(r.revenue)
            for r in month_sales.itertuples(index=False)
        }
        release_by_ed: dict[tuple[str, str], float] = defaultdict(float)

        # Release customer advances when the related service month is reached.
        for lot in open_contracts:
            if lot["outstanding"] <= 0.005 or pd.Period(lot["service_month"], freq="M") > period:
                continue
            key = (lot["entity"], lot["division"], lot["customer"], lot["product"])
            available = invoice_available.get(key, 0.0)
            if available <= 0.005:
                continue
            applied = min(float(lot["outstanding"]), available)
            if applied <= 0.005:
                continue
            jid = f"CONTRACT-APPLY-{month}-{lot['entity']}-{lot['customer']}-{lot['product']}"
            new_rows.append(_journal_row(
                month=month, entity=lot["entity"], division=lot["division"], journal_id=jid,
                journal_type="contract_liability_application", account=CONTRACT_LIABILITY_ACCOUNT,
                debit=applied, customer=lot["customer"], product=lot["product"],
                description="Customer advance applied to recognized service",
            ))
            new_rows.append(_journal_row(
                month=month, entity=lot["entity"], division=lot["division"], journal_id=jid,
                journal_type="contract_liability_application", account="1100_AR",
                credit=applied, customer=lot["customer"], product=lot["product"],
                description="Customer advance applied to invoice",
            ))
            lot["outstanding"] -= applied
            invoice_available[key] = available - applied
            release_by_ed[(lot["entity"], lot["division"])] += applied

        sales_ed = month_sales.groupby(["entity", "division"], as_index=False).revenue.sum()
        for r in sales_ed.itertuples(index=False):
            entity, division = str(r.entity), str(r.division)
            revenue = float(r.revenue)
            release = float(release_by_ed.get((entity, division), 0.0))
            residual_billed = max(revenue - release, 0.0)
            key = (entity, division)
            available_ar = ar_balance[key] + revenue - release
            dso = float(config["divisions"][division]["dso"])
            target_end = residual_billed * dso / 30.0
            collection = min(max(available_ar - target_end, 0.0), available_ar)
            if collection > 0.005:
                jid = f"COLL-CONTRACT-{month}-{entity}-{division.replace(' ', '')}"
                new_rows.append(_journal_row(
                    month=month, entity=entity, division=division, journal_id=jid,
                    journal_type="collection", account="1000_CASH", debit=collection,
                    description="Customer collections after advance application",
                    cash_flow_category="customer_collections",
                ))
                new_rows.append(_journal_row(
                    month=month, entity=entity, division=division, journal_id=jid,
                    journal_type="collection", account="1100_AR", credit=collection,
                    description="Customer collections after advance application",
                ))
            ar_balance[key] = available_ar - collection

        # Receive next-month customer advances after current-period service settlement.
        receipt_scope = commitments_by_receipt.get(month)
        if receipt_scope is not None:
            for r in receipt_scope.itertuples(index=False):
                amount = float(r.advance_amount)
                jid = f"CONTRACT-CASH-{month}-{r.entity}-{r.customer}-{r.product}"
                new_rows.append(_journal_row(
                    month=month, entity=str(r.entity), division=str(r.division), journal_id=jid,
                    journal_type="customer_advance", account="1000_CASH", debit=amount,
                    customer=str(r.customer), product=str(r.product),
                    description=f"Customer advance for service month {r.service_month}",
                    cash_flow_category="customer_collections",
                ))
                new_rows.append(_journal_row(
                    month=month, entity=str(r.entity), division=str(r.division), journal_id=jid,
                    journal_type="customer_advance", account=CONTRACT_LIABILITY_ACCOUNT, credit=amount,
                    customer=str(r.customer), product=str(r.product),
                    description=f"Contract liability for service month {r.service_month}",
                ))
                open_contracts.append({
                    "receipt_month": month,
                    "service_month": str(r.service_month),
                    "entity": str(r.entity),
                    "division": str(r.division),
                    "customer": str(r.customer),
                    "product": str(r.product),
                    "product_family": str(r.product_family),
                    "quality_tier": str(r.quality_tier),
                    "original_amount": amount,
                    "outstanding": amount,
                })

        for lot in open_contracts:
            if lot["outstanding"] <= 0.005:
                continue
            schedule_rows.append({
                "month": month,
                "receipt_month": lot["receipt_month"],
                "service_month": lot["service_month"],
                "entity": lot["entity"],
                "division": lot["division"],
                "customer": lot["customer"],
                "product": lot["product"],
                "product_family": lot["product_family"],
                "quality_tier": lot["quality_tier"],
                "original_advance": lot["original_amount"],
                "contract_liability": lot["outstanding"],
                "months_to_service": pd.Period(lot["service_month"], freq="M").ordinal - period.ordinal,
            })

    contract_journal = pd.DataFrame(new_rows, columns=journal.columns)
    adjusted = pd.concat([base, contract_journal], ignore_index=True)
    schedule = pd.DataFrame(schedule_rows)
    return adjusted, commitments, schedule


def _contract_liability_balances(journal: pd.DataFrame) -> pd.DataFrame:
    scope = journal[journal.account.eq(CONTRACT_LIABILITY_ACCOUNT)].copy()
    if scope.empty:
        return pd.DataFrame(columns=["month", "entity", "contract_liabilities"])
    scope["movement"] = scope.credit - scope.debit
    monthly = scope.groupby(["month", "entity"], as_index=False).movement.sum()
    months = sorted(journal.month.unique())
    entities = sorted(journal.entity.unique())
    running: dict[str, float] = defaultdict(float)
    rows = []
    for month in months:
        for r in monthly[monthly.month.eq(month)].itertuples(index=False):
            running[str(r.entity)] += float(r.movement)
        for entity in entities:
            rows.append({"month": month, "entity": entity, "contract_liabilities": running[entity]})
    return pd.DataFrame(rows)


def legal_balance_sheet_with_contracts(journal: pd.DataFrame) -> pd.DataFrame:
    base = legal_balance_sheet_with_provisions(journal)
    contracts = _contract_liability_balances(journal)
    out = base.merge(contracts, on=["month", "entity"], how="left").fillna({"contract_liabilities": 0.0})
    out["liabilities"] = out.liabilities + out.contract_liabilities
    out["balance_check"] = out.assets - out.liabilities - out.equity
    return out


def group_balance_sheet_with_contracts(legal_bs: pd.DataFrame, markup: float) -> pd.DataFrame:
    base = group_balance_sheet_with_provisions(legal_bs, markup)
    contracts = legal_bs.groupby("month", as_index=False).contract_liabilities.sum()
    out = base.merge(contracts, on="month", how="left").fillna({"contract_liabilities": 0.0})
    out["liabilities"] = out.liabilities + out.contract_liabilities
    out["balance_check"] = out.assets - out.liabilities - out.equity
    return out


def contract_liability_summary(schedule: pd.DataFrame, commitments: pd.DataFrame) -> pd.DataFrame:
    if schedule.empty:
        return pd.DataFrame(columns=["month", "contract_liabilities", "software_contract_liabilities", "events_contract_liabilities", "customer_advances"])
    balance = schedule.groupby(["month", "division"], as_index=False).contract_liability.sum()
    pivot = balance.pivot_table(index="month", columns="division", values="contract_liability", aggfunc="sum", fill_value=0.0).reset_index()
    for division in ["Software", "Events"]:
        if division not in pivot.columns:
            pivot[division] = 0.0
    pivot = pivot.rename(columns={"Software": "software_contract_liabilities", "Events": "events_contract_liabilities"})
    pivot["contract_liabilities"] = pivot.software_contract_liabilities + pivot.events_contract_liabilities
    receipts = commitments.groupby("month", as_index=False).advance_amount.sum().rename(columns={"advance_amount": "customer_advances"})
    return pivot.merge(receipts, on="month", how="outer").fillna(0.0).sort_values("month")


def validate_contract_liabilities(journal: pd.DataFrame, schedule: pd.DataFrame) -> dict:
    account = _contract_liability_balances(journal)
    gl = account.groupby("month", as_index=False).contract_liabilities.sum() if not account.empty else pd.DataFrame(columns=["month", "contract_liabilities"])
    if schedule.empty:
        sched = pd.DataFrame(columns=["month", "schedule_contract_liabilities"])
        negative = 0
    else:
        sched = schedule.groupby("month", as_index=False).contract_liability.sum().rename(columns={"contract_liability": "schedule_contract_liabilities"})
        negative = int((schedule.contract_liability < -0.005).sum())
    recon = gl.merge(sched, on="month", how="outer").fillna(0.0)
    gap = float((recon.contract_liabilities - recon.schedule_contract_liabilities).abs().max()) if not recon.empty else 0.0

    contract_journals = journal[journal.journal_type.isin(["customer_advance", "contract_liability_application"])]
    by_journal = contract_journals.groupby("journal_id", as_index=False).agg(debit=("debit", "sum"), credit=("credit", "sum")) if not contract_journals.empty else pd.DataFrame()
    journal_gap = float((by_journal.debit - by_journal.credit).abs().max()) if not by_journal.empty else 0.0

    checks = {
        "contract_liability_schedule_max_gap": round(gap, 2),
        "contract_liability_journal_max_gap": round(journal_gap, 2),
        "contract_liability_negative_rows": negative,
    }
    checks["passed"] = gap <= 0.05 and journal_gap <= 0.02 and negative == 0
    return checks
