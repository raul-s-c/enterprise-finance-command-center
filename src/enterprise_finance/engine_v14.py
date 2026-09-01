from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from . import engine as base_engine
from .accounting_v14 import validate_workforce_accounting
from .engine_v12 import _capital_allocation, _scenario_summary as liquidity_scenario_summary
from .engine_v13 import build as build_v13, _scenario_summary as statement_scenario_summary
from .forecasting_v14 import validate_workforce_forecast
from .liquidity_workforce_v14 import build_liquidity_forecast, validate_liquidity_forecast
from .three_statement_forecast import build_three_statement_forecast, validate_three_statement_forecast
from .workforce import allocation_checks, build_workforce_schedule, workforce_rollforward_checks


VERSION = "0.14.0"
HORIZON = 12


def _read_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def _write_csv(df: pd.DataFrame, path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def _workforce_summary(schedule: pd.DataFrame) -> pd.DataFrame:
    if schedule.empty:
        return pd.DataFrame()
    out = schedule.groupby("month", as_index=False).agg(
        opening_fte=("opening_fte", "sum"),
        hires=("hires", "sum"),
        attrition=("attrition", "sum"),
        ending_fte=("ending_fte", "sum"),
        average_fte=("average_fte", "sum"),
        payroll_cost=("payroll_cost", "sum"),
        recruitment_cost=("recruitment_cost", "sum"),
        personnel_cost=("personnel_cost", "sum"),
        revenue=("revenue", "sum"),
    )
    out["revenue_per_fte"] = out.revenue / out.average_fte.replace(0.0, pd.NA)
    out["personnel_cost_pct_revenue"] = out.personnel_cost / out.revenue.replace(0.0, pd.NA)
    return out.fillna(0.0)


def build(end_month: str, config_path: str = "config/company.yml", allow_live_macro: bool = True):
    """Run v0.13 on workforce-driven actuals and replace forward cash with payroll-aware liquidity."""
    result = build_v13(end_month, config_path=config_path, allow_live_macro=allow_live_macro)
    config = base_engine.load_config(config_path)

    operations = _read_csv("data/runtime/operational.csv.gz")
    journal = _read_csv("data/runtime/journal.csv.gz")
    macro = _read_csv("data/processed/macro.csv")
    forecasts = _read_csv("data/processed/forecast_vintages.csv")
    management = _read_csv("data/processed/management_pnl.csv")
    balance_sheet = _read_csv("data/processed/balance_sheet.csv")
    actual_liquidity = _read_csv("data/processed/liquidity_covenants.csv")
    debt = _read_csv("data/processed/debt_schedule.csv")
    advances = _read_csv("data/processed/customer_advances.csv")

    workforce = build_workforce_schedule(operations, config, macro)
    workforce_summary = _workforce_summary(workforce)
    workforce_forecast = forecasts[
        forecasts.vintage.eq(end_month)
        & forecasts.horizon_month.le(HORIZON)
    ].copy()

    roll_checks = workforce_rollforward_checks(workforce)
    allocation_control = allocation_checks(operations, workforce)
    accounting_control = validate_workforce_accounting(journal, operations)
    forecast_control = validate_workforce_forecast(forecasts)

    liquidity = build_liquidity_forecast(
        forecasts=forecasts,
        management=management,
        balance_sheet=balance_sheet,
        actual_liquidity=actual_liquidity,
        debt_schedule=debt,
        advances=advances,
        config=config,
        end_month=end_month,
        horizon=HORIZON,
    )
    liquidity_checks = validate_liquidity_forecast(liquidity, HORIZON)
    liquidity_summary = liquidity_scenario_summary(liquidity)
    capital_allocation = _capital_allocation(liquidity, config)

    forecast_pnl, forecast_bs, forecast_cf = build_three_statement_forecast(
        forecasts=forecasts,
        liquidity=liquidity,
        management=management,
        balance_sheet=balance_sheet,
        config=config,
        end_month=end_month,
        horizon=HORIZON,
    )
    statement_checks = validate_three_statement_forecast(
        forecast_pnl, forecast_bs, forecast_cf, HORIZON
    )
    statement_summary = statement_scenario_summary(forecast_pnl, forecast_bs, forecast_cf)

    with open("data/processed/validation.json", "r", encoding="utf-8") as handle:
        checks = json.load(handle)
    for control in [roll_checks, allocation_control, accounting_control, forecast_control, liquidity_checks, statement_checks]:
        checks.update({k: v for k, v in control.items() if k != "passed"})
    checks["workforce_schedule_missing"] = int(workforce.empty)
    checks["workforce_forecast_missing"] = int(workforce_forecast.empty)
    checks["passed"] = bool(
        checks.get("passed", False)
        and all(c["passed"] for c in [roll_checks, allocation_control, accounting_control, forecast_control, liquidity_checks, statement_checks])
        and checks["workforce_schedule_missing"] == 0
        and checks["workforce_forecast_missing"] == 0
    )
    if not checks["passed"]:
        raise RuntimeError(f"Workforce planning controls failed: {checks}")

    _write_csv(workforce, "data/processed/workforce_schedule.csv")
    _write_csv(workforce_summary, "data/processed/workforce_summary.csv")
    _write_csv(workforce_forecast, "data/processed/workforce_forecast.csv")
    _write_csv(liquidity, "data/processed/liquidity_forecast.csv")
    _write_csv(liquidity_summary, "data/processed/liquidity_forecast_summary.csv")
    _write_csv(capital_allocation, "data/processed/capital_allocation_capacity.csv")
    _write_csv(forecast_pnl, "data/processed/forecast_pnl.csv")
    _write_csv(forecast_bs, "data/processed/forecast_balance_sheet.csv")
    _write_csv(forecast_cf, "data/processed/forecast_cash_flow.csv")
    _write_csv(statement_summary, "data/processed/three_statement_forecast_summary.csv")
    with open("data/processed/validation.json", "w", encoding="utf-8") as handle:
        json.dump(checks, handle, indent=2)

    with open("web/data/dashboard.json", "r", encoding="utf-8") as handle:
        dashboard = json.load(handle)
    latest_detail = workforce[workforce.month.eq(end_month)].sort_values(["entity", "division", "function"])
    dashboard["meta"]["version"] = VERSION
    dashboard["workforce_summary"] = base_engine._records(workforce_summary)
    dashboard["workforce_detail"] = base_engine._records(latest_detail)
    dashboard["workforce_forecast"] = base_engine._records(workforce_forecast)
    dashboard["liquidity_forecast"] = base_engine._records(liquidity)
    dashboard["liquidity_forecast_summary"] = base_engine._records(liquidity_summary)
    dashboard["capital_allocation_capacity"] = base_engine._records(capital_allocation)
    dashboard["forecast_pnl"] = base_engine._records(forecast_pnl)
    dashboard["forecast_balance_sheet"] = base_engine._records(forecast_bs)
    dashboard["forecast_cash_flow"] = base_engine._records(forecast_cf)
    dashboard["three_statement_forecast_summary"] = base_engine._records(statement_summary)
    dashboard["validation"] = checks
    with open("web/data/dashboard.json", "w", encoding="utf-8") as handle:
        json.dump(dashboard, handle, separators=(",", ":"), allow_nan=False)

    latest = workforce_summary[workforce_summary.month.eq(end_month)]
    base_fc = workforce_forecast[workforce_forecast.scenario.eq("Base")]
    base_liq = liquidity_summary[liquidity_summary.scenario.eq("Base")]
    base_stmt = statement_summary[statement_summary.scenario.eq("Base")]
    with open("web/data/manifest.json", "r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    manifest["version"] = VERSION
    manifest["workforce_schedule_rows"] = int(len(workforce))
    manifest["workforce_forecast_rows"] = int(len(workforce_forecast))
    if not latest.empty:
        r = latest.iloc[0]
        manifest["latest_fte"] = round(float(r.ending_fte), 2)
        manifest["latest_workforce_hires"] = round(float(r.hires), 2)
        manifest["latest_workforce_attrition"] = round(float(r.attrition), 2)
        manifest["latest_personnel_cost"] = round(float(r.personnel_cost), 2)
        manifest["latest_revenue_per_fte"] = round(float(r.revenue_per_fte), 2)
        manifest["latest_personnel_cost_pct_revenue"] = round(float(r.personnel_cost_pct_revenue), 4)
    manifest["base_12m_personnel_cost"] = round(float(base_fc.personnel_cost_forecast.sum()), 2) if not base_fc.empty else 0.0
    manifest["base_12m_workforce_hires"] = round(float(base_fc.workforce_hires_forecast.sum()), 2) if not base_fc.empty else 0.0
    if not base_liq.empty:
        manifest["base_12m_ending_cash"] = round(float(base_liq.iloc[0].ending_cash_12m), 2)
    if not base_stmt.empty:
        manifest["base_12m_forecast_ebit"] = round(float(base_stmt.iloc[0].ebit_12m), 2)
        manifest["base_12m_forecast_free_cash_flow"] = round(float(base_stmt.iloc[0].free_cash_flow_12m), 2)
    manifest["validation"] = checks
    with open("web/data/manifest.json", "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)

    return result
