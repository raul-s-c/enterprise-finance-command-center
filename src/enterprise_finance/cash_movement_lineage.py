"""Current-close cash movement lineage to modeled invoice, accrual and project evidence.

AR/AP applications are analytical allocations of aggregate cash postings, not
bank-matched receipts, remittances or invoice settlements.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


TOLERANCE = 0.05
CATEGORIES = {
    "customer_collections": "customer_collections",
    "supplier_payments": "supplier_payments",
    "capex": "capex",
    "interest": "interest",
    "tax": "tax",
    "debt_repayment": "debt_repayment",
    "intercompany_settlement": "intercompany_settlement",
    "intercompany_treasury": "intercompany_treasury",
    "opening": "opening",
}
ALLOCATION_BASIS = {
    "customer_collections": (
        "Risk-aware oldest-receivable allocation of aggregate posted collections; "
        "not bank-matched remittance evidence."
    ),
    "supplier_payments": (
        "Modeled oldest-accrual allocation of aggregate AP reductions; "
        "not supplier-remittance or invoice-settlement evidence."
    ),
    "capex": (
        "Posted project SPEND journal; GO_LIVE is a non-cash CIP-to-PPE transfer and is excluded."
    ),
}


def _require(frame: pd.DataFrame, required: set[str], label: str) -> None:
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing {label} cash-lineage fields: {sorted(missing)}")


def _text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def build_cash_movement_lineage(
    journal: pd.DataFrame,
    ar_applications: pd.DataFrame,
    ap_applications: pd.DataFrame,
    capex_events: pd.DataFrame,
    expected_cash_flow: pd.DataFrame,
    end_month: str,
) -> tuple[pd.DataFrame, dict[str, float | int | bool]]:
    """Explain current-month cash journals through supported source allocations."""
    _require(
        journal,
        {
            "month", "entity", "division", "journal_id", "account", "debit",
            "credit", "cash_flow_category", "counterparty", "description",
        },
        "journal",
    )
    _require(
        ar_applications,
        {
            "application_month", "entity", "division", "source_journal_id",
            "allocation_type", "applied_amount", "invoice_id", "customer",
        },
        "AR application",
    )
    _require(
        ap_applications,
        {
            "application_month", "entity", "posted_division", "reduction_journal_id",
            "accrual_journal_id", "applied_amount", "supplier", "supplier_name",
        },
        "AP application",
    )
    _require(
        capex_events,
        {"month", "journal_id", "event", "project", "project_name", "amount"},
        "CAPEX event",
    )
    _require(
        expected_cash_flow,
        {"month", "entity", *CATEGORIES.values()},
        "cash-flow summary",
    )

    for name, frame, columns in [
        ("journal", journal, ["debit", "credit"]),
        ("AR application", ar_applications, ["applied_amount"]),
        ("AP application", ap_applications, ["applied_amount"]),
        ("CAPEX event", capex_events, ["amount"]),
        ("cash-flow summary", expected_cash_flow, list(CATEGORIES.values())),
    ]:
        if not frame.empty and not np.isfinite(frame[columns].to_numpy(dtype=float)).all():
            raise ValueError(f"Non-finite amount in {name} cash-lineage input")

    close = str(end_month)
    cash = journal.loc[
        journal.account.eq("1000_CASH")
        & journal.month.astype(str).eq(close)
        & journal.cash_flow_category.fillna("").astype(str).str.strip().ne("")
    ].copy()
    cash["cash_amount"] = cash.debit.astype(float) - cash.credit.astype(float)
    cash["journal_id"] = cash.journal_id.map(_text)
    if cash.journal_id.eq("").any() or cash.journal_id.duplicated().any():
        raise ValueError("Current-close cash journal IDs must be unique and non-empty")

    ar = ar_applications.loc[
        ar_applications.application_month.astype(str).eq(close)
        & ar_applications.allocation_type.astype(str).eq("cash_collection")
    ].copy()
    ar["source_journal_id"] = ar.source_journal_id.map(_text)
    ap = ap_applications.loc[
        ap_applications.application_month.astype(str).eq(close)
    ].copy()
    ap["reduction_journal_id"] = ap.reduction_journal_id.map(_text)
    spend = capex_events.loc[
        capex_events.month.astype(str).eq(close) & capex_events.event.astype(str).eq("SPEND")
    ].copy()
    spend["journal_id"] = spend.journal_id.map(_text)

    rows: list[dict[str, object]] = []
    unlinked = {"customer_collections": 0, "supplier_payments": 0, "capex": 0}
    max_journal_gap = 0.0

    def append(
        source: pd.Series,
        amount: float,
        record_type: str,
        record_id: str,
        counterparty: str,
        basis: str,
        division: str | None = None,
    ) -> None:
        rows.append({
            "month": close,
            "entity": _text(source.entity),
            "division": division or _text(source.division),
            "cash_flow_category": _text(source.cash_flow_category),
            "source_journal_id": _text(source.journal_id),
            "source_record_type": record_type,
            "source_record_id": record_id,
            "counterparty": counterparty,
            "movement_amount": round(float(amount), 2),
            "allocation_basis": basis,
        })

    for _, source in cash.iterrows():
        journal_id = _text(source.journal_id)
        category = _text(source.cash_flow_category)
        amount = float(source.cash_amount)
        if abs(amount) <= 0.005:
            continue
        matches: list[tuple[pd.Series, str, str, str, str]] = []
        if category == "customer_collections":
            applications = ar.loc[ar.source_journal_id.eq(journal_id)]
            matches = [
                (item, "Customer invoice allocation", _text(item.invoice_id), _text(item.customer), _text(item.division) or _text(source.division))
                for _, item in applications.iterrows()
            ]
        elif category == "supplier_payments":
            applications = ap.loc[ap.reduction_journal_id.eq(journal_id)]
            matches = [
                (
                    item, "Supplier accrual allocation", _text(item.accrual_journal_id),
                    _text(item.supplier_name) or _text(item.supplier),
                    _text(item.posted_division) or _text(source.division),
                )
                for _, item in applications.iterrows()
            ]
        elif category == "capex":
            events = spend.loc[spend.journal_id.eq(journal_id)]
            matches = [
                (item, "CAPEX project event", _text(item.project), _text(item.project_name), _text(item.division) or _text(source.division))
                for _, item in events.iterrows()
            ]

        if category in unlinked and not matches:
            unlinked[category] += 1
        if matches:
            allocated = sum(abs(float(item.applied_amount if hasattr(item, "applied_amount") else item.amount)) for item, *_ in matches)
            gap = abs(abs(amount) - allocated)
            max_journal_gap = max(max_journal_gap, gap)
            if gap > TOLERANCE:
                continue
            for item, record_type, record_id, counterparty, movement_division in matches:
                raw_amount = float(item.applied_amount if hasattr(item, "applied_amount") else item.amount)
                append(
                    source, np.copysign(abs(raw_amount), amount), record_type, record_id,
                    counterparty, ALLOCATION_BASIS[category], movement_division,
                )
        else:
            append(
                source, amount, "Cash journal posting", journal_id, _text(source.counterparty),
                "Posted cash-account journal; no supporting subledger allocation is published.",
            )

    lineage = pd.DataFrame(rows, columns=[
        "month", "entity", "division", "cash_flow_category", "source_journal_id",
        "source_record_type", "source_record_id", "counterparty", "movement_amount",
        "allocation_basis",
    ])

    duplicate_rows = int(lineage.duplicated([
        "source_journal_id", "source_record_type", "source_record_id"
    ]).sum()) if not lineage.empty else 0
    missing_source_ids = int(
        (lineage.source_journal_id.map(_text).eq("") | lineage.source_record_id.map(_text).eq("")).sum()
    ) if not lineage.empty else 0
    if lineage.empty:
        journal_gap = 0.0
    else:
        detail_by_journal = lineage.groupby("source_journal_id").movement_amount.sum()
        source_by_journal = cash.set_index("journal_id").cash_amount
        journal_gap = float(
            pd.concat([detail_by_journal.rename("detail"), source_by_journal.rename("source")], axis=1)
            .fillna(0).eval("(detail - source).abs()").max()
        )

    actual = cash.groupby(["entity", "cash_flow_category"], as_index=False).cash_amount.sum()
    expected = expected_cash_flow.loc[expected_cash_flow.month.astype(str).eq(close)].copy()
    summary_gap = 0.0
    missing_summary = 0
    if expected.duplicated("entity").any():
        raise ValueError("Current-close cash-flow summary must have one row per entity")
    for category, field in CATEGORIES.items():
        left = actual.loc[actual.cash_flow_category.eq(category)].set_index("entity").cash_amount
        right = expected.set_index("entity")[field].astype(float)
        entities = set(left.index) | set(right.index)
        if not entities:
            continue
        for entity in entities:
            if entity not in right.index:
                missing_summary += 1
            gap = abs(float(left.get(entity, 0.0)) - float(right.get(entity, 0.0)))
            summary_gap = max(summary_gap, gap)

    checks: dict[str, float | int | bool] = {
        "cash_movement_lineage_max_gap": round(max_journal_gap, 6),
        "cash_movement_journal_max_gap": round(journal_gap, 6),
        "cash_movement_cashflow_max_gap": round(summary_gap, 6),
        "cash_movement_unlinked_collection_journals": unlinked["customer_collections"],
        "cash_movement_unlinked_supplier_journals": unlinked["supplier_payments"],
        "cash_movement_unlinked_capex_journals": unlinked["capex"],
        "cash_movement_missing_summary_entities": missing_summary,
        "cash_movement_duplicate_lineage_rows": duplicate_rows,
        "cash_movement_missing_source_ids": missing_source_ids,
        "cash_movement_lineage_rows": int(len(lineage)),
    }
    checks["passed"] = bool(
        max_journal_gap <= TOLERANCE
        and journal_gap <= TOLERANCE
        and summary_gap <= TOLERANCE
        and not any(unlinked.values())
        and missing_summary == 0
        and duplicate_rows == 0
        and missing_source_ids == 0
    )
    return lineage, checks
