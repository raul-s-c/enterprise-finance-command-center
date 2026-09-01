import pandas as pd

from enterprise_finance.accounting import build_accounting
from enterprise_finance.engine import load_config, month_range
from enterprise_finance.macro import build_macro
from enterprise_finance.model import simulate_operations
from enterprise_finance.reporting import management_pnl
from enterprise_finance.treasury import (
    append_cash_pool_journals,
    cash_flow_with_treasury,
    debt_schedule,
    group_balance_sheet_with_treasury,
    legal_balance_sheet_with_treasury,
    treasury_entity_schedule,
    validate_treasury,
)


def _fixture(periods=8):
    config = load_config()
    months = month_range("2026-08", periods)
    macro = build_macro(months, int(config["group"]["seed"]), allow_live=False)
    simulation = simulate_operations(config, months, macro)
    accounting = build_accounting(config, months, macro, simulation.operations)
    management = management_pnl(simulation.operations, accounting.journal)
    return config, accounting.journal, management


def _group_cash_by_month(journal):
    cash = journal[journal.account.eq("1000_CASH")].copy()
    cash["movement"] = cash.debit - cash.credit
    return cash.groupby("month", as_index=False).movement.sum()


def test_cash_pool_is_zero_sum_and_legal_balance_sheets_remain_balanced():
    config, base_journal, management = _fixture(8)
    adjusted, pool = append_cash_pool_journals(base_journal, config)
    assert not pool.empty
    assert adjusted.journal_type.eq("treasury_cash_pool").any()

    before = _group_cash_by_month(base_journal)
    after = _group_cash_by_month(adjusted)
    recon = before.merge(after, on="month", suffixes=("_before", "_after"))
    assert (recon.movement_before - recon.movement_after).abs().max() <= 0.01

    legal = legal_balance_sheet_with_treasury(adjusted)
    group = group_balance_sheet_with_treasury(
        legal, float(config["transfer_pricing"]["manufacturing_cost_plus"])
    )
    assert legal.balance_check.abs().max() <= 0.05
    assert group.balance_check.abs().max() <= 0.05

    debt, maturity, liquidity = debt_schedule(adjusted, management, config)
    checks = validate_treasury(base_journal, adjusted, legal, group, debt)
    assert checks["passed"]
    assert checks["treasury_pool_journal_max_gap"] <= 0.02
    assert checks["treasury_group_cash_movement_max_gap"] <= 0.02
    assert checks["treasury_ic_receivable_payable_max_gap"] <= 0.02
    assert checks["treasury_debt_schedule_max_gap"] <= 0.02
    assert not maturity.empty
    assert not liquidity.empty


def test_treasury_schedule_enforces_operating_cash_minimums_and_builds_covenants():
    config, base_journal, management = _fixture(8)
    adjusted, _ = append_cash_pool_journals(base_journal, config)
    debt, _, liquidity = debt_schedule(adjusted, management, config)
    entity = treasury_entity_schedule(adjusted, debt, config)

    latest_month = entity.month.max()
    latest = entity[entity.month.eq(latest_month)]
    hq = str(config["treasury"]["hq_entity"])
    subsidiaries = latest[~latest.entity.eq(hq)]
    assert (subsidiaries.cash + 0.05 >= subsidiaries.minimum_cash).all()
    assert (latest.cash >= -0.05).all()

    latest_liquidity = liquidity[liquidity.month.eq(latest_month)].iloc[0]
    assert latest_liquidity.liquidity_headroom >= 0
    assert latest_liquidity.undrawn_rcf >= 0
    assert latest_liquidity.covenant_status in {"PASS", "WATCH"}
    assert "net_leverage" in liquidity.columns
    assert "interest_coverage" in liquidity.columns

    cf = cash_flow_with_treasury(adjusted)
    assert "intercompany_treasury" in cf.columns
    group_pool_cash = cf.groupby("month").intercompany_treasury.sum()
    assert group_pool_cash.abs().max() <= 0.01
