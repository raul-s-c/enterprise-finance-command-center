import pandas as pd

from enterprise_finance.engine import load_config
from enterprise_finance.liquidity_forecast_v12 import (
    build_liquidity_forecast,
    validate_liquidity_forecast,
)


def _forecast_fixture(end_month="2026-08"):
    rows=[]
    scenarios={"Base":1.0,"Upside":1.08,"Downside":0.92}
    divisions={
        "Software": (8_000_000, 6_200_000, 1_500_000),
        "Hardware": (14_000_000, 4_500_000, 1_700_000),
        "Events": (5_000_000, 1_800_000, 900_000),
        "Spare Parts": (7_000_000, 3_300_000, 800_000),
    }
    for scenario,mult in scenarios.items():
        for h in range(1,13):
            month=str(pd.Period(end_month,freq="M")+h)
            for division,(rev,gp,opex) in divisions.items():
                rows.append({
                    "vintage":end_month,"scenario":scenario,"month":month,
                    "horizon_month":h,"entity":"DE01","division":division,
                    "revenue_forecast":rev*mult,
                    "gross_profit_forecast":gp*mult,
                    "opex_forecast":opex*mult,
                })
    forecasts=pd.DataFrame(rows)
    management=pd.DataFrame([
        {"month":end_month,"entity":"DE01","division":d,"revenue":v[0],"depreciation":250_000}
        for d,v in divisions.items()
    ])
    balance_sheet=pd.DataFrame([{
        "month":end_month,"cash":80_000_000,"trade_receivables_gross":35_000_000,
        "inventory_gross":25_000_000,"trade_payables":22_000_000,
        "contract_liabilities":6_000_000,"tax_payable":1_500_000,"debt":30_000_000,
    }])
    actual_liquidity=pd.DataFrame([
        {"month":str(pd.Period(end_month,freq="M")-i),"ebitda":7_000_000,"interest_expense":120_000}
        for i in range(10,-1,-1)
    ])
    debt=pd.DataFrame([{
        "month":end_month,"entity":"DE01","gross_debt":30_000_000,
        "implied_annual_interest_rate":0.04,
    }])
    advances=pd.DataFrame([
        {"month":end_month,"division":"Software","advance_amount":2_000_000},
        {"month":end_month,"division":"Events","advance_amount":1_000_000},
    ])
    return forecasts,management,balance_sheet,actual_liquidity,debt,advances


def test_liquidity_forecast_has_one_row_per_month_and_scenario():
    config=load_config()
    args=_forecast_fixture()
    forecast=build_liquidity_forecast(
        forecasts=args[0],management=args[1],balance_sheet=args[2],
        actual_liquidity=args[3],debt_schedule=args[4],advances=args[5],
        config=config,end_month="2026-08",horizon=12,
    )
    assert len(forecast)==36
    assert set(forecast.scenario)=={"Base","Upside","Downside"}
    assert forecast.groupby("scenario").month.nunique().eq(12).all()
    assert forecast.groupby(["scenario","month"]).size().eq(1).all()
    checks=validate_liquidity_forecast(forecast,12)
    assert checks["passed"], checks
    assert checks["liquidity_forecast_cash_rollforward_max_gap"]<=0.02
    assert checks["liquidity_forecast_rcf_identity_max_gap"]<=0.02


def test_liquidity_forecast_rolls_state_and_respects_facility():
    config=load_config()
    args=_forecast_fixture()
    forecast=build_liquidity_forecast(
        forecasts=args[0],management=args[1],balance_sheet=args[2],
        actual_liquidity=args[3],debt_schedule=args[4],advances=args[5],
        config=config,end_month="2026-08",horizon=12,
    )
    for _,grp in forecast.groupby("scenario"):
        grp=grp.sort_values("horizon_month").reset_index(drop=True)
        assert (grp.opening_cash.iloc[1:].reset_index(drop=True)-grp.ending_cash.iloc[:-1].reset_index(drop=True)).abs().max()<=0.02
        assert (grp.rcf_drawn<=grp.rcf_limit+0.05).all()
        assert (grp.undrawn_rcf>=-0.05).all()
        assert (grp.liquidity_shortfall<=0.05).all()
        assert grp.covenant_status.isin(["PASS","WATCH"]).all()
