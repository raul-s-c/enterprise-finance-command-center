from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from . import engine as base_engine
from .engine_v11 import build as build_v11
from .liquidity_forecast_v12 import build_liquidity_forecast, validate_liquidity_forecast


VERSION = "0.12.0"
HORIZON = 12


def _read_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def _write_csv(df: pd.DataFrame, path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def _scenario_summary(forecast: pd.DataFrame) -> pd.DataFrame:
    if forecast.empty:
        return pd.DataFrame()
    rows: list[dict] = []
    for scenario, group in forecast.groupby("scenario"):
        group = group.sort_values("horizon_month")
        final = group.iloc[-1]
        rows.append({
            "scenario": str(scenario),
            "ending_cash_12m": float(final.ending_cash),
            "gross_debt_12m": float(final.gross_debt),
            "net_debt_12m": float(final.net_debt),
            "liquidity_headroom_12m": float(final.liquidity_headroom),
            "deployable_cash_12m": float(final.deployable_cash),
            "net_leverage_12m": float(final.net_leverage),
            "interest_coverage_12m": float(final.interest_coverage),
            "undrawn_rcf_12m": float(final.undrawn_rcf),
            "covenant_status_12m": str(final.covenant_status),
            "minimum_liquidity_headroom": float(group.liquidity_headroom.min()),
            "minimum_cash": float(group.ending_cash.min()),
            "maximum_rcf_drawn": float(group.rcf_drawn.max()),
            "forecast_capex_12m": float(group.capex.sum()),
            "forecast_operating_cash_flow_12m": float(group.operating_cash_flow.sum()),
            "scheduled_debt_repayment_12m": float(group.scheduled_debt_repayment.sum()),
        })
    return pd.DataFrame(rows)


def _capital_allocation(forecast: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Translate forecast liquidity into a conservative capital-allocation envelope.

    This is not an automatic management decision. It quantifies the cash that
    remains after minimum operating cash, the strategic liquidity buffer and the
    forecast's own operating/CAPEX/debt requirements.
    """
    summary = _scenario_summary(forecast)
    if summary.empty:
        return summary
    downside = summary[summary.scenario.eq("Downside")]
    downside_deployable = float(downside.iloc[0].deployable_cash_12m) if not downside.empty else 0.0
    downside_headroom = float(downside.iloc[0].minimum_liquidity_headroom) if not downside.empty else 0.0
    policy = config.get("treasury", {})
    strategic_buffer = float(policy.get("strategic_liquidity_buffer", 15_000_000.0))
    allocation_limit = max(min(downside_deployable, downside_headroom), 0.0)
    summary["strategic_liquidity_buffer"] = strategic_buffer
    summary["downside_protected_allocation_capacity"] = allocation_limit
    summary["capital_allocation_status"] = summary.apply(
        lambda row: "Capacity available" if allocation_limit > 0.0 else "Preserve liquidity",
        axis=1,
    )
    return summary


def build(end_month: str, config_path: str = "config/company.yml", allow_live_macro: bool = True):
    """Run v0.11 Treasury and add a 12-month driver-based liquidity forecast."""
    result = build_v11(end_month, config_path=config_path, allow_live_macro=allow_live_macro)
    config = base_engine.load_config(config_path)

    forecasts = _read_csv("data/processed/forecast_vintages.csv")
    management = _read_csv("data/processed/management_pnl.csv")
    balance_sheet = _read_csv("data/processed/balance_sheet.csv")
    actual_liquidity = _read_csv("data/processed/liquidity_covenants.csv")
    debt = _read_csv("data/processed/debt_schedule.csv")
    advances = _read_csv("data/processed/customer_advances.csv")

    liquidity_forecast = build_liquidity_forecast(
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
    forecast_checks = validate_liquidity_forecast(liquidity_forecast, horizon=HORIZON)
    scenario_summary = _scenario_summary(liquidity_forecast)
    capital_allocation = _capital_allocation(liquidity_forecast, config)

    base = scenario_summary[scenario_summary.scenario.eq("Base")]
    downside = scenario_summary[scenario_summary.scenario.eq("Downside")]
    missing_base = int(base.empty)
    missing_downside = int(downside.empty)

    with open("data/processed/validation.json", "r", encoding="utf-8") as handle:
        checks = json.load(handle)
    checks.update({key: value for key, value in forecast_checks.items() if key != "passed"})
    checks["liquidity_forecast_base_missing"] = missing_base
    checks["liquidity_forecast_downside_missing"] = missing_downside
    checks["passed"] = bool(
        checks.get("passed", False)
        and forecast_checks["passed"]
        and missing_base == 0
        and missing_downside == 0
    )
    if not checks["passed"]:
        raise RuntimeError(f"Liquidity forecast controls failed: {checks}")

    _write_csv(liquidity_forecast, "data/processed/liquidity_forecast.csv")
    _write_csv(scenario_summary, "data/processed/liquidity_forecast_summary.csv")
    _write_csv(capital_allocation, "data/processed/capital_allocation_capacity.csv")
    with open("data/processed/validation.json", "w", encoding="utf-8") as handle:
        json.dump(checks, handle, indent=2)

    with open("web/data/dashboard.json", "r", encoding="utf-8") as handle:
        dashboard = json.load(handle)
    dashboard["meta"]["version"] = VERSION
    dashboard["liquidity_forecast"] = base_engine._records(liquidity_forecast)
    dashboard["liquidity_forecast_summary"] = base_engine._records(scenario_summary)
    dashboard["capital_allocation_capacity"] = base_engine._records(capital_allocation)
    dashboard["validation"] = checks
    with open("web/data/dashboard.json", "w", encoding="utf-8") as handle:
        json.dump(dashboard, handle, separators=(",", ":"), allow_nan=False)

    with open("web/data/manifest.json", "r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    base_values = base.iloc[0].to_dict() if not base.empty else {}
    downside_values = downside.iloc[0].to_dict() if not downside.empty else {}
    allocation_capacity = (
        float(capital_allocation.downside_protected_allocation_capacity.iloc[0])
        if not capital_allocation.empty else 0.0
    )
    manifest["version"] = VERSION
    manifest["liquidity_forecast_rows"] = int(len(liquidity_forecast))
    manifest["base_12m_ending_cash"] = round(float(base_values.get("ending_cash_12m", 0.0)), 2)
    manifest["base_12m_liquidity_headroom"] = round(float(base_values.get("liquidity_headroom_12m", 0.0)), 2)
    manifest["base_12m_net_leverage"] = round(float(base_values.get("net_leverage_12m", 0.0)), 4)
    manifest["base_12m_interest_coverage"] = round(float(base_values.get("interest_coverage_12m", 0.0)), 4)
    manifest["base_12m_deployable_cash"] = round(float(base_values.get("deployable_cash_12m", 0.0)), 2)
    manifest["downside_minimum_liquidity_headroom"] = round(float(downside_values.get("minimum_liquidity_headroom", 0.0)), 2)
    manifest["downside_12m_ending_cash"] = round(float(downside_values.get("ending_cash_12m", 0.0)), 2)
    manifest["downside_12m_covenant_status"] = str(downside_values.get("covenant_status_12m", ""))
    manifest["downside_protected_allocation_capacity"] = round(allocation_capacity, 2)
    manifest["validation"] = checks
    with open("web/data/manifest.json", "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)

    return result
