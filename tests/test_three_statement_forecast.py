import pandas as pd

from enterprise_finance.engine import load_config
from enterprise_finance.liquidity_forecast_v12 import build_liquidity_forecast
from enterprise_finance.three_statement_forecast import (
    build_three_statement_forecast,
    validate_three_statement_forecast,
)


def _fixture(end_month="2026-08"):
    config = load_config()
    scenarios = {"Base": 1.0, "Upside": 1.08, "Downside": 0.92}
    divisions = {
        "Software": (8_000_000, 6_200_000, 1_500_000),
        "Hardware": (14_000_000, 4_500_000, 1_700_000),
        "Events": (5_000_000, 1_800_000, 900_000),
        "Spare Parts": (7_000_000, 3_300_000, 800_000),
    }
    forecast_rows = []
    for scenario, mult in scenarios.items():
        for horizon in range(1, 13):
            month = str(pd.Period(end_month, freq="M") + horizon)
            for division, (revenue, gp, opex) in divisions.items():
                forecast_rows.append({
                    "vintage": end_month,
                    "scenario": scenario,
                    "month": month,
                    "horizon_month": horizon,
                    "entity": "DE01",
                    "division": division,
                    "revenue_forecast": revenue * mult,
                    "gross_profit_forecast": gp * mult,
                    "opex_forecast": opex * mult,
                })
    forecasts = pd.DataFrame(forecast_rows)

    management = pd.DataFrame([
        {
            "month": end_month,
            "entity": "DE01",
            "division": division,
            "revenue": values[0],
            "depreciation": 250_000,
        }
        for division, values in divisions.items()
    ])

    cash = 80_000_000.0
    ar_gross = 35_000_000.0
    ecl = 70_000.0
    inv_gross = 25_000_000.0
    inv_prov = 100_000.0
    markup = 1_000_000.0
    ppe = 100_000_000.0
    cip = 5_000_000.0
    accum_dep = -30_000_000.0
    ap = 22_000_000.0
    tax = 1_500_000.0
    debt = 30_000_000.0
    contracts = 6_000_000.0
    share_capital = 100_000_000.0
    assets = cash + (ar_gross - ecl) + (inv_gross - inv_prov - markup) + ppe + cip + accum_dep
    liabilities = ap + tax + debt + contracts
    retained = assets - liabilities - share_capital
    balance_sheet = pd.DataFrame([{
        "month": end_month,
        "cash": cash,
        "trade_receivables_gross": ar_gross,
        "credit_loss_allowance": ecl,
        "trade_receivables": ar_gross - ecl,
        "inventory_gross": inv_gross,
        "inventory_provision": inv_prov,
        "inventory_legal_transfer_value": inv_gross,
        "unrealized_ic_markup_reserve": markup,
        "inventory": inv_gross - inv_prov - markup,
        "ppe_gross": ppe,
        "cip": cip,
        "accumulated_depreciation": accum_dep,
        "trade_payables": ap,
        "tax_payable": tax,
        "debt": debt,
        "contract_liabilities": contracts,
        "share_capital": share_capital,
        "retained_earnings": retained,
        "assets": assets,
        "liabilities": liabilities,
        "equity": share_capital + retained,
        "balance_check": 0.0,
    }])

    actual_liquidity = pd.DataFrame([
        {
            "month": str(pd.Period(end_month, freq="M") - i),
            "ebitda": 7_000_000.0,
            "interest_expense": 120_000.0,
        }
        for i in range(10, -1, -1)
    ])
    debt_schedule = pd.DataFrame([{
        "month": end_month,
        "entity": "DE01",
        "gross_debt": debt,
        "implied_annual_interest_rate": 0.04,
    }])
    advances = pd.DataFrame([
        {"month": end_month, "division": "Software", "advance_amount": 2_000_000.0},
        {"month": end_month, "division": "Events", "advance_amount": 1_000_000.0},
    ])
    liquidity = build_liquidity_forecast(
        forecasts=forecasts,
        management=management,
        balance_sheet=balance_sheet,
        actual_liquidity=actual_liquidity,
        debt_schedule=debt_schedule,
        advances=advances,
        config=config,
        end_month=end_month,
        horizon=12,
    )
    return config, forecasts, liquidity, management, balance_sheet


def test_three_statement_forecast_balances_without_plug():
    config, forecasts, liquidity, management, balance_sheet = _fixture()
    pnl, bs, cf = build_three_statement_forecast(
        forecasts, liquidity, management, balance_sheet, config, "2026-08", 12
    )
    assert len(pnl) == 36
    assert len(bs) == 36
    assert len(cf) == 36
    assert set(bs.scenario) == {"Base", "Upside", "Downside"}
    checks = validate_three_statement_forecast(pnl, bs, cf, 12)
    assert checks["passed"], checks
    assert checks["three_statement_balance_sheet_max_gap"] <= 0.10
    assert checks["three_statement_cash_flow_max_gap"] <= 0.02
    assert checks["three_statement_cash_link_max_gap"] <= 0.02


def test_three_statement_retained_earnings_and_cash_roll_forward():
    config, forecasts, liquidity, management, balance_sheet = _fixture()
    pnl, bs, cf = build_three_statement_forecast(
        forecasts, liquidity, management, balance_sheet, config, "2026-08", 12
    )
    opening_retained = float(balance_sheet.iloc[0].retained_earnings)
    for scenario in ["Base", "Upside", "Downside"]:
        p = pnl[pnl.scenario.eq(scenario)].sort_values("horizon_month").reset_index(drop=True)
        b = bs[bs.scenario.eq(scenario)].sort_values("horizon_month").reset_index(drop=True)
        c = cf[cf.scenario.eq(scenario)].sort_values("horizon_month").reset_index(drop=True)
        expected_retained = opening_retained + p.net_income.cumsum()
        assert (b.retained_earnings - expected_retained).abs().max() <= 0.10
        assert (b.cash - c.ending_cash).abs().max() <= 0.02
        assert (c.ending_cash.iloc[1:].reset_index(drop=True) - c.opening_cash.iloc[1:].reset_index(drop=True)).abs().max() >= 0.0


def test_three_statement_uses_cent_precise_liquidity_driver_block():
    config, forecasts, liquidity, management, balance_sheet = _fixture()
    liquidity = liquidity.copy()
    liquidity["revenue"] = 0.0
    liquidity["personnel_cost"] = 0.0
    liquidity["non_people_opex"] = 0.0
    liquidity["ebitda"] = 0.0

    for idx, row in liquidity.iterrows():
        month_fc = forecasts[
            forecasts.scenario.eq(row.scenario)
            & forecasts.month.eq(row.month)
        ]
        revenue = round(sum(round(float(value), 2) for value in month_fc.revenue_forecast), 2)
        opex = round(sum(round(float(value), 2) for value in month_fc.opex_forecast), 2)
        gross_profit = round(sum(round(float(value), 2) for value in month_fc.gross_profit_forecast), 2)
        liquidity.at[idx, "revenue"] = revenue
        liquidity.at[idx, "personnel_cost"] = round(opex * 0.7, 2)
        liquidity.at[idx, "non_people_opex"] = round(opex - round(opex * 0.7, 2), 2)
        liquidity.at[idx, "ebitda"] = round(gross_profit - opex, 2)

    pnl, bs, cf = build_three_statement_forecast(
        forecasts, liquidity, management, balance_sheet, config, "2026-08", 12
    )
    checks = validate_three_statement_forecast(pnl, bs, cf, 12)

    assert checks["passed"], checks
    assert pnl.operating_forecast_revenue_rounding_gap.abs().max() <= 0.02
    assert pnl.operating_forecast_gp_rounding_gap.abs().max() <= 0.02
    assert pnl.operating_forecast_opex_rounding_gap.abs().max() <= 0.02
