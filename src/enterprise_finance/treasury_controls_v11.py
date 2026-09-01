from __future__ import annotations

from collections import defaultdict

import pandas as pd

from .accounting import cash_flow
from .treasury import (
    TREASURY_PAYABLE,
    TREASURY_RECEIVABLE,
    _treasury_balances,
    append_cash_pool_journals,
    chart_of_accounts_with_treasury,
    debt_schedule,
    group_balance_sheet_with_treasury,
    legal_balance_sheet_with_treasury,
    treasury_entity_schedule,
)


def cash_flow_with_treasury(journal: pd.DataFrame) -> pd.DataFrame:
    """Classify zero-sum cash-pool movements as legal-entity financing cash flows."""
    out = cash_flow(journal).copy()
    if "intercompany_treasury" not in out.columns:
        cash = journal[journal.account.eq("1000_CASH")].copy()
        cash["cash_movement"] = cash.debit - cash.credit
        treasury = (
            cash[cash.cash_flow_category.eq("intercompany_treasury")]
            .groupby(["month", "entity"], as_index=False)
            .cash_movement.sum()
            .rename(columns={"cash_movement": "intercompany_treasury"})
        )
        out = out.merge(treasury, on=["month", "entity"], how="left")
    out["intercompany_treasury"] = out["intercompany_treasury"].fillna(0.0)
    out["financing_cash_flow"] = out.financing_cash_flow + out.intercompany_treasury
    out["net_cash_movement"] = out.net_cash_movement + out.intercompany_treasury
    return out


def _debt_gl_schedule(journal: pd.DataFrame) -> pd.DataFrame:
    debt = journal[journal.account.eq("2500_DEBT")].copy()
    months = sorted(str(x) for x in journal.month.unique())
    entities = sorted(str(x) for x in journal.entity.unique())
    if debt.empty:
        return pd.MultiIndex.from_product([months, entities], names=["month", "entity"]).to_frame(index=False).assign(gl_debt=0.0)
    debt["movement"] = debt.credit - debt.debit
    monthly = debt.groupby(["month", "entity"], as_index=False).movement.sum()
    running: dict[str, float] = defaultdict(float)
    rows: list[dict] = []
    for month in months:
        for r in monthly[monthly.month.eq(month)].itertuples(index=False):
            running[str(r.entity)] += float(r.movement)
        for entity in entities:
            rows.append({"month": month, "entity": entity, "gl_debt": running[entity]})
    return pd.DataFrame(rows)


def validate_treasury(
    base_journal: pd.DataFrame,
    adjusted_journal: pd.DataFrame,
    legal_bs: pd.DataFrame,
    group_bs: pd.DataFrame,
    debt: pd.DataFrame,
) -> dict:
    pool = adjusted_journal[adjusted_journal.journal_type.eq("treasury_cash_pool")].copy()
    if pool.empty:
        pool_journal_gap = 0.0
    else:
        by_journal = pool.groupby("journal_id", as_index=False).agg(debit=("debit", "sum"), credit=("credit", "sum"))
        pool_journal_gap = float((by_journal.debit - by_journal.credit).abs().max())

    base_cash = base_journal[base_journal.account.eq("1000_CASH")].copy()
    adjusted_cash = adjusted_journal[adjusted_journal.account.eq("1000_CASH")].copy()
    base_cash["movement"] = base_cash.debit - base_cash.credit
    adjusted_cash["movement"] = adjusted_cash.debit - adjusted_cash.credit
    base_group = base_cash.groupby("month", as_index=False).movement.sum().sort_values("month")
    adjusted_group = adjusted_cash.groupby("month", as_index=False).movement.sum().sort_values("month")
    recon = base_group.merge(adjusted_group, on="month", how="outer", suffixes=("_base", "_pool")).fillna(0.0)
    group_cash_movement_gap = float((recon.movement_base - recon.movement_pool).abs().max()) if not recon.empty else 0.0

    treasury = _treasury_balances(adjusted_journal)
    monthly_treasury = treasury.groupby("month", as_index=False).agg(
        receivable=("treasury_receivable", "sum"), payable=("treasury_payable", "sum")
    )
    ic_gap = float((monthly_treasury.receivable - monthly_treasury.payable).abs().max()) if not monthly_treasury.empty else 0.0

    legal_gap = float(legal_bs.balance_check.abs().max()) if not legal_bs.empty else 0.0
    group_gap = float(group_bs.balance_check.abs().max()) if not group_bs.empty else 0.0

    gl_debt = _debt_gl_schedule(adjusted_journal)
    debt_recon = debt.merge(gl_debt, on=["month", "entity"], how="left").fillna({"gl_debt": 0.0})
    debt_gap = float((debt_recon.gross_debt - debt_recon.gl_debt).abs().max()) if not debt_recon.empty else 0.0

    checks = {
        "treasury_pool_journal_max_gap": round(pool_journal_gap, 2),
        "treasury_group_cash_movement_max_gap": round(group_cash_movement_gap, 2),
        "treasury_ic_receivable_payable_max_gap": round(ic_gap, 2),
        "treasury_legal_balance_sheet_max_gap": round(legal_gap, 2),
        "treasury_group_balance_sheet_max_gap": round(group_gap, 2),
        "treasury_debt_schedule_max_gap": round(debt_gap, 2),
    }
    checks["passed"] = all(abs(float(v)) <= 0.05 for key, v in checks.items() if key != "passed")
    return checks


__all__ = [
    "append_cash_pool_journals",
    "cash_flow_with_treasury",
    "chart_of_accounts_with_treasury",
    "debt_schedule",
    "group_balance_sheet_with_treasury",
    "legal_balance_sheet_with_treasury",
    "treasury_entity_schedule",
    "validate_treasury",
    "TREASURY_RECEIVABLE",
    "TREASURY_PAYABLE",
]
