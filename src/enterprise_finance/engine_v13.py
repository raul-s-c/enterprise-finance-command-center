from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from . import engine as base_engine
from .engine_v12 import build as build_v12
from .three_statement_forecast import (
    build_three_statement_forecast,
    validate_three_statement_forecast,
)


VERSION = "0.13.0"
HORIZON = 12


def _read_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def _write_csv(df: pd.DataFrame, path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def _scenario_summary(pnl: pd.DataFrame, bs: pd.DataFrame, cf: pd.DataFrame) -> pd.DataFrame:
    if pnl.empty or bs.empty or cf.empty:
        return pd.DataFrame()
    rows: list[dict] = []
    for scenario in sorted(bs.scenario.unique()):
        p = pnl[pnl.scenario.eq(scenario)].sort_values("horizon_month")
        b = bs[bs.scenario.eq(scenario)].sort_values("horizon_month")
        c = cf[cf.scenario.eq(scenario)].sort_values("horizon_month")
        if p.empty or b.empty or c.empty:
            continue
        final_bs = b.iloc[-1]
        rows.append({
            "scenario": scenario,
            "revenue_12m": float(p.revenue.sum()),
            "ebit_12m": float(p.ebit.sum()),
            "net_income_12m": float(p.net_income.sum()),
            "operating_cash_flow_12m": float(c.operating_cash_flow.sum()),
            "free_cash_flow_12m": float(c.free_cash_flow.sum()),
            "ending_cash_12m": float(final_bs.cash),
            "ending_net_receivables_12m": float(final_bs.trade_receivables),
            "ending_net_inventory_12m": float(final_bs.inventory),
            "ending_debt_12m": float(final_bs.debt),
            "ending_contract_liabilities_12m": float(final_bs.contract_liabilities),
            "ending_assets_12m": float(final_bs.assets),
            "ending_liabilities_12m": float(final_bs.liabilities),
            "ending_equity_12m": float(final_bs.equity),
            "ending_balance_check": float(final_bs.balance_check),
        })
    return pd.DataFrame(rows)


def build(end_month: str, config_path: str = "config/company.yml", allow_live_macro: bool = True):
    """Run v0.12 and add integrated Base/Upside/Downside three-statement forecasts."""
    result = build_v12(end_month, config_path=config_path, allow_live_macro=allow_live_macro)
    config = base_engine.load_config(config_path)

    forecasts = _read_csv("data/processed/forecast_vintages.csv")
    liquidity = _read_csv("data/processed/liquidity_forecast.csv")
    management = _read_csv("data/processed/management_pnl.csv")
    balance_sheet = _read_csv("data/processed/balance_sheet.csv")

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
        forecast_pnl, forecast_bs, forecast_cf, horizon=HORIZON
    )
    summary = _scenario_summary(forecast_pnl, forecast_bs, forecast_cf)

    with open("data/processed/validation.json", "r", encoding="utf-8") as handle:
        checks = json.load(handle)
    checks.update({key: value for key, value in statement_checks.items() if key != "passed"})
    checks["three_statement_base_missing"] = int(summary[summary.scenario.eq("Base")].empty) if not summary.empty else 1
    checks["three_statement_downside_missing"] = int(summary[summary.scenario.eq("Downside")].empty) if not summary.empty else 1
    checks["passed"] = bool(
        checks.get("passed", False)
        and statement_checks["passed"]
        and checks["three_statement_base_missing"] == 0
        and checks["three_statement_downside_missing"] == 0
    )
    if not checks["passed"]:
        raise RuntimeError(f"Three-statement forecast controls failed: {checks}")

    _write_csv(forecast_pnl, "data/processed/forecast_pnl.csv")
    _write_csv(forecast_bs, "data/processed/forecast_balance_sheet.csv")
    _write_csv(forecast_cf, "data/processed/forecast_cash_flow.csv")
    _write_csv(summary, "data/processed/three_statement_forecast_summary.csv")
    with open("data/processed/validation.json", "w", encoding="utf-8") as handle:
        json.dump(checks, handle, indent=2)

    with open("web/data/dashboard.json", "r", encoding="utf-8") as handle:
        dashboard = json.load(handle)
    dashboard["meta"]["version"] = VERSION
    dashboard["forecast_pnl"] = base_engine._records(forecast_pnl)
    dashboard["forecast_balance_sheet"] = base_engine._records(forecast_bs)
    dashboard["forecast_cash_flow"] = base_engine._records(forecast_cf)
    dashboard["three_statement_forecast_summary"] = base_engine._records(summary)
    dashboard["validation"] = checks
    with open("web/data/dashboard.json", "w", encoding="utf-8") as handle:
        json.dump(dashboard, handle, separators=(",", ":"), allow_nan=False)

    with open("web/data/manifest.json", "r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    base = summary[summary.scenario.eq("Base")]
    downside = summary[summary.scenario.eq("Downside")]
    b = base.iloc[0].to_dict() if not base.empty else {}
    d = downside.iloc[0].to_dict() if not downside.empty else {}
    manifest["version"] = VERSION
    manifest["three_statement_forecast_rows"] = int(len(forecast_bs))
    manifest["base_12m_forecast_revenue"] = round(float(b.get("revenue_12m", 0.0)), 2)
    manifest["base_12m_forecast_ebit"] = round(float(b.get("ebit_12m", 0.0)), 2)
    manifest["base_12m_forecast_net_income"] = round(float(b.get("net_income_12m", 0.0)), 2)
    manifest["base_12m_forecast_free_cash_flow"] = round(float(b.get("free_cash_flow_12m", 0.0)), 2)
    manifest["base_12m_forecast_assets"] = round(float(b.get("ending_assets_12m", 0.0)), 2)
    manifest["base_12m_forecast_equity"] = round(float(b.get("ending_equity_12m", 0.0)), 2)
    manifest["downside_12m_forecast_net_income"] = round(float(d.get("net_income_12m", 0.0)), 2)
    manifest["downside_12m_forecast_free_cash_flow"] = round(float(d.get("free_cash_flow_12m", 0.0)), 2)
    manifest["downside_12m_forecast_assets"] = round(float(d.get("ending_assets_12m", 0.0)), 2)
    manifest["validation"] = checks
    with open("web/data/manifest.json", "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)

    return result
