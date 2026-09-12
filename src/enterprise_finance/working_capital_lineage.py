"""Authoritative working-capital movements; no invented invoice settlements."""
from __future__ import annotations

import numpy as np
import pandas as pd

ACCOUNTS = {"1100_AR": "Receivables", "2100_AP": "Payables", "1200_INVENTORY": "Inventory"}
KEYS = ["entity", "division", "account"]


def build_working_capital_lineage(journal: pd.DataFrame, end_month: str):
    """Return closing-month source postings and full-history legal rollforwards.

    Amounts use debit-positive GL signs, including negative payable balances.
    Journal IDs identify postings, not externally supplied supplier invoices.
    """
    required = ["month", *KEYS, "journal_id", "journal_type", "debit", "credit"]
    missing = set(required) - set(journal.columns)
    if missing:
        raise ValueError(f"Missing lineage source fields: {sorted(missing)}")
    source = journal.loc[journal.account.isin(ACCOUNTS) & journal.month.le(end_month)].copy()
    if not np.isfinite(source[["debit", "credit"]].to_numpy(dtype=float)).all():
        raise ValueError("Non-finite working-capital posting")
    if source[["month", *KEYS, "journal_id"]].isna().any().any():
        raise ValueError("Missing working-capital source identity")
    source["movement"] = source.debit - source.credit
    monthly = source.groupby(["month", *KEYS], as_index=False)[["debit", "credit", "movement"]].sum()
    rows = []
    months = pd.period_range(journal.month.min(), end_month, freq="M").astype(str)
    for key, scope in monthly.groupby(KEYS, sort=True):
        opening = 0.0
        indexed = scope.set_index("month")
        for month in months:
            debit = float(indexed.loc[month, "debit"]) if month in indexed.index else 0.0
            credit = float(indexed.loc[month, "credit"]) if month in indexed.index else 0.0
            closing = opening + debit - credit
            rows.append(dict(zip(KEYS, key), month=month, opening_balance=opening,
                             debits=debit, credits=credit, closing_balance=closing))
            opening = closing
    rollforward = pd.DataFrame(rows, columns=[*KEYS, "month", "opening_balance", "debits", "credits", "closing_balance"])
    detail = source.loc[source.month.eq(end_month)].copy()
    detail["component"] = detail.account.map(ACCOUNTS)
    detail["evidence_basis"] = "Posted GL movement; not an invoice settlement allocation"
    columns = [*required, "component", "movement", "evidence_basis"]
    columns += [c for c in ["customer", "product", "counterparty", "description", "cash_flow_category"] if c in detail]
    detail = detail[columns].fillna("")
    # Independently reconcile final balances to all source postings, not rounded values.
    expected = source.groupby(KEYS).movement.sum()
    actual = rollforward.loc[rollforward.month.eq(end_month)].set_index(KEYS).closing_balance
    gap = float((actual.subtract(expected, fill_value=0)).abs().max()) if len(expected) else 0.0
    checks = {"working_capital_lineage_max_gap": gap, "passed": gap <= 0.05}
    return detail, rollforward, checks
