import pandas as pd

from enterprise_finance.accounting import balance_sheet, validate_journal
from enterprise_finance.accounting_v14 import build_accounting, validate_workforce_accounting
from enterprise_finance.engine import load_config, month_range
from enterprise_finance.forecasting_v14 import build_forecast_vintages, validate_workforce_forecast
from enterprise_finance.liquidity_workforce_v14 import build_liquidity_forecast, validate_liquidity_forecast
from enterprise_finance.macro import build_macro
from enterprise_finance.model import simulate_operations
from enterprise_finance.workforce import (
    allocation_checks,
    build_workforce_schedule,
    enrich_operations_with_workforce,
    workforce_rollforward_checks,
)


def _actual_fixture(periods=8):
    config = load_config()
    months = month_range("2026-08", periods)
    macro = build_macro(months, config["group"]["seed"], allow_live=False)
    base = simulate_operations(config, months, macro)
    workforce = build_workforce_schedule(base.operations, config, macro)
    operations = enrich_operations_with_workforce(base.operations, workforce, config)
    return config, months, macro, base, workforce, operations


def test_workforce_rollforward_and_cost_allocation():
    config, months, macro, base, workforce, operations = _actual_fixture(8)
    roll = workforce_rollforward_checks(workforce)
    allocation = allocation_checks(operations, workforce)
    assert roll["passed"], roll
    assert allocation["passed"], allocation
    assert workforce.ending_fte.sum() > 0
    assert workforce.personnel_cost.sum() > 0
    assert operations.personnel_cost_allocated.sum() > 0
    assert operations.non_people_opex.sum() > 0
    assert (operations.opex - operations.personnel_cost_allocated - operations.non_people_opex).abs().max() <= 0.02


def test_payroll_is_paid_directly_and_never_creates_trade_ap():
    config, months, macro, base, workforce, operations = _actual_fixture(6)
    accounting = build_accounting(config, months, macro, operations)
    controls = validate_workforce_accounting(accounting.journal, operations)
    assert controls["passed"], controls
    assert controls["workforce_payroll_ap_rows"] == 0
    payroll = accounting.journal[accounting.journal.journal_type.eq("payroll")]
    assert not payroll.empty
    assert set(payroll.account.unique()) == {"6000_OPEX", "1000_CASH"}
    journal_controls = validate_journal(accounting.journal)
    assert journal_controls["journal_balance_max_gap"] <= 0.02
    bs = balance_sheet(accounting.journal)
    assert bs.balance_check.abs().max() <= 0.05


def test_workforce_drives_rolling_forecast_opex():
    config, months, macro, base, workforce, operations = _actual_fixture(8)
    forecasts = build_forecast_vintages(config, operations, months)
    controls = validate_workforce_forecast(forecasts)
    assert controls["passed"], controls
    latest = forecasts[forecasts.vintage.eq(str(months[-1]))]
    assert not latest.empty
    assert latest.personnel_cost_forecast.sum() > 0
    assert latest.non_people_opex_forecast.sum() > 0
    assert latest.workforce_fte_forecast.sum() > 0
    assert (latest.opex_forecast - latest.personnel_cost_forecast - latest.non_people_opex_forecast).abs().max() <= 0.02


def test_liquidity_separates_payroll_from_supplier_cash():
    config = load_config()
    end_month = "2026-08"
    rows = []
    for scenario, mult in [("Base", 1.0), ("Upside", 1.06), ("Downside", 0.94)]:
        for h in range(1, 13):
            month = str(pd.Period(end_month, freq="M") + h)
            for division, revenue, gp, personnel, non_people in [
                ("Software", 8_000_000, 6_200_000, 900_000, 450_000),
                ("Hardware", 14_000_000, 4_500_000, 650_000, 420_000),
            ]:
                rows.append({
                    "vintage": end_month, "scenario": scenario, "month": month,
                    "horizon_month": h, "entity": "DE01", "division": division,
                    "revenue_forecast": revenue * mult,
                    "gross_profit_forecast": gp * mult,
                    "marginal_contribution_forecast": gp * 1.08 * mult,
                    "personnel_cost_forecast": personnel * mult,
                    "non_people_opex_forecast": non_people * mult,
                    "opex_forecast": (personnel + non_people) * mult,
                })
    forecasts = pd.DataFrame(rows)
    management = pd.DataFrame([
        {"month": end_month, "division": "Software", "revenue": 8_000_000, "depreciation": 250_000},
        {"month": end_month, "division": "Hardware", "revenue": 14_000_000, "depreciation": 250_000},
    ])
    bs = pd.DataFrame([{
        "month": end_month, "cash": 80_000_000, "trade_receivables_gross": 30_000_000,
        "inventory_gross": 22_000_000, "trade_payables": 20_000_000,
        "contract_liabilities": 4_000_000, "tax_payable": 1_000_000, "debt": 25_000_000,
    }])
    liq_hist = pd.DataFrame([
        {"month": str(pd.Period(end_month, freq="M") - i), "ebitda": 6_000_000, "interest_expense": 100_000}
        for i in range(10, -1, -1)
    ])
    debt = pd.DataFrame([{"month": end_month, "gross_debt": 25_000_000, "implied_annual_interest_rate": 0.04}])
    advances = pd.DataFrame([{"month": end_month, "division": "Software", "advance_amount": 1_000_000}])
    liquidity = build_liquidity_forecast(forecasts, management, bs, liq_hist, debt, advances, config, end_month, 12)
    controls = validate_liquidity_forecast(liquidity, 12)
    assert controls["passed"], controls
    assert liquidity.payroll_cash.sum() > 0
    assert liquidity.workforce_liquidity_payroll_cash_max_gap.sum() if "workforce_liquidity_payroll_cash_max_gap" in liquidity.columns else True
    assert liquidity.payroll_cash_identity_gap.abs().max() <= 0.02
