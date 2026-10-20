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


def test_forecast_inventory_uses_the_same_trailing_demand_policy_as_actuals():
    import pandas as pd

    from enterprise_finance.liquidity_workforce_v14 import build_liquidity_forecast

    config = load_config()
    end_month = "2026-10"
    hardware_direct = [9_000_000, 12_000_000, 4_000_000, 6_000_000]
    rows = []
    for h, direct in enumerate(hardware_direct, start=1):
        rows.append({
            "vintage": end_month, "scenario": "Base", "month": str(pd.Period(end_month, freq="M") + h),
            "horizon_month": h, "entity": "CZ01", "division": "Hardware",
            "revenue_forecast": direct + 5_000_000, "gross_profit_forecast": 5_000_000,
            "marginal_contribution_forecast": 5_500_000, "personnel_cost_forecast": 600_000,
            "non_people_opex_forecast": 400_000, "opex_forecast": 1_000_000,
        })
    management = pd.DataFrame([
        {"month": month, "division": "Hardware", "revenue": 14_000_000, "gross_profit": 5_000_000, "depreciation": 200_000}
        for month in ["2026-09", "2026-10"]
    ])
    bs = pd.DataFrame([{
        "month": end_month, "cash": 80_000_000, "trade_receivables_gross": 30_000_000, "inventory_gross": 22_000_000,
        "trade_payables": 20_000_000, "contract_liabilities": 0.0, "tax_payable": 0.0, "debt": 10_000_000,
    }])
    history = pd.DataFrame([{"month": str(pd.Period(end_month, freq="M") - i), "ebitda": 4_000_000, "interest_expense": 30_000} for i in range(10, -1, -1)])
    debt = pd.DataFrame([{"month": end_month, "gross_debt": 10_000_000, "implied_annual_interest_rate": 0.04}])
    advances = pd.DataFrame([{"month": end_month, "division": "Hardware", "advance_amount": 0.0}])

    liquidity = build_liquidity_forecast(pd.DataFrame(rows), management, bs, history, debt, advances, config, end_month, 4)

    dio = float(config["divisions"]["Hardware"]["dio"])
    window = [9_000_000, 9_000_000]
    expected = []
    for direct in hardware_direct:
        window = (window + [direct])[-INVENTORY_DEMAND_WINDOW_MONTHS:]
        expected.append(round(sum(window) / len(window) * dio / 30.0, 2))
    assert liquidity.sort_values("horizon_month").ending_inventory.round(2).tolist() == expected
    january = liquidity.loc[liquidity.month.eq("2027-01"), "ending_inventory"].iloc[0]
    assert january > 4_000_000 * dio / 30.0 * 1.5
