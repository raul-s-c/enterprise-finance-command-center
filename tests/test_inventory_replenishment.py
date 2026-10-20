from enterprise_finance.accounting import (
    INVENTORY_DEMAND_WINDOW_MONTHS,
    balance_sheet,
    build_accounting,
    validate_journal,
)
from enterprise_finance.engine import load_config, month_range
from enterprise_finance.macro import build_macro
from enterprise_finance.model import simulate_operations


def _factory_months(end="2026-03", periods=9):
    config = load_config()
    months = month_range(end, periods)
    macro = build_macro(months, config["group"]["seed"], allow_live=False)
    simulation = simulate_operations(config, months, macro)
    accounting = build_accounting(config, months, macro, simulation.operations)
    return config, months, accounting


def test_replenishment_plans_on_trailing_demand_so_january_production_does_not_collapse():
    assert INVENTORY_DEMAND_WINDOW_MONTHS == 3
    _, months, accounting = _factory_months()
    factory = accounting.factory[accounting.factory.month > str(months[0])]
    for factory_id, rows in factory.groupby("factory"):
        median = rows.produced_units.median()
        january = rows.loc[rows.month.str.endswith("-01"), "produced_units"]
        assert not january.empty
        assert (january >= 0.4 * median).all(), f"{factory_id} January production collapses: {january.tolist()} vs median {median}"


def test_practical_capacity_keeps_steady_state_utilization_realistic():
    _, months, accounting = _factory_months()
    factory = accounting.factory[accounting.factory.month > str(months[0])]
    assert factory.utilization.max() <= 1.0
    assert factory.groupby("factory").utilization.median().between(0.45, 0.95).all()


def test_replenishment_change_keeps_ledger_balanced_and_inventory_non_negative():
    _, _, accounting = _factory_months()
    assert validate_journal(accounting.journal)["journal_balance_max_gap"] <= 0.02
    sheet = balance_sheet(accounting.journal)
    assert (sheet.inventory >= -0.01).all()
