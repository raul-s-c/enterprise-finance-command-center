from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from . import engine as base_engine
from .budgeting_v09 import build_annual_budgets, budget_performance, validate_budgets
from .engine_v08 import build as build_v08
from .planning_v09 import fy_plan_bridge


VERSION = "0.9.0"


def _read_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def _write_csv(df: pd.DataFrame, path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def build(end_month: str, config_path: str = "config/company.yml", allow_live_macro: bool = True):
    """Run v0.8 and add a frozen annual Budget plus FY planning bridges."""
    result = build_v08(end_month, config_path=config_path, allow_live_macro=allow_live_macro)
    config = base_engine.load_config(config_path)
    management = _read_csv("data/processed/management_pnl.csv")
    forecasts = _read_csv("data/processed/forecast_vintages.csv")

    budgets = build_annual_budgets(management, config, end_month)
    performance = budget_performance(management, budgets, end_month)
    fy_bridge = fy_plan_bridge(management, budgets, forecasts, end_month)
    budget_checks = validate_budgets(management, budgets, config)

    current_year = pd.Period(end_month, freq="M").year
    current_budget = budgets[budgets.budget_year.eq(current_year)] if not budgets.empty else pd.DataFrame()
    current_budget_missing = int(current_budget.empty)
    fy_bridge_missing = int(fy_bridge.empty)

    with open("data/processed/validation.json", "r", encoding="utf-8") as handle:
        checks = json.load(handle)
    checks.update({key: value for key, value in budget_checks.items() if key != "passed"})
    checks["current_year_budget_missing"] = current_budget_missing
    checks["fy_plan_bridge_missing"] = fy_bridge_missing
    checks["passed"] = bool(
        checks.get("passed", False)
        and budget_checks["passed"]
        and current_budget_missing == 0
        and fy_bridge_missing == 0
    )
    if not checks["passed"]:
        raise RuntimeError(f"Budget and plan controls failed: {checks}")

    _write_csv(budgets, "data/processed/annual_budget.csv")
    _write_csv(performance, "data/processed/budget_performance.csv")
    _write_csv(fy_bridge, "data/processed/fy_plan_bridge.csv")
    with open("data/processed/validation.json", "w", encoding="utf-8") as handle:
        json.dump(checks, handle, indent=2)

    with open("web/data/dashboard.json", "r", encoding="utf-8") as handle:
        dashboard = json.load(handle)
    perf_scope = performance[performance.budget_year.eq(current_year)] if not performance.empty else performance
    dashboard["meta"]["version"] = VERSION
    dashboard["meta"]["budget_year"] = current_year
    dashboard["meta"]["budget_vintage"] = str(current_budget.budget_vintage.iloc[0]) if not current_budget.empty else ""
    dashboard["annual_budget"] = base_engine._records(current_budget)
    dashboard["budget_performance"] = base_engine._records(perf_scope)
    dashboard["fy_plan_bridge"] = base_engine._records(fy_bridge)
    dashboard["budget_years"] = sorted(int(x) for x in budgets.budget_year.unique()) if not budgets.empty else []
    dashboard["validation"] = checks
    with open("web/data/dashboard.json", "w", encoding="utf-8") as handle:
        json.dump(dashboard, handle, separators=(",", ":"), allow_nan=False)

    with open("web/data/manifest.json", "r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    agg = fy_bridge.select_dtypes(include="number").sum(numeric_only=True) if not fy_bridge.empty else pd.Series(dtype=float)
    manifest["version"] = VERSION
    manifest["budget_rows"] = int(len(budgets))
    manifest["budget_years"] = sorted(int(x) for x in budgets.budget_year.unique()) if not budgets.empty else []
    manifest["current_budget_year"] = current_year
    manifest["current_budget_vintage"] = str(current_budget.budget_vintage.iloc[0]) if not current_budget.empty else ""
    manifest["fy_budget_revenue"] = round(float(agg.get("fy_budget_revenue", 0.0)), 2)
    manifest["fy_budget_ebit"] = round(float(agg.get("fy_budget_ebit", 0.0)), 2)
    manifest["ytd_actual_revenue"] = round(float(agg.get("ytd_actual_revenue", 0.0)), 2)
    manifest["ytd_budget_revenue"] = round(float(agg.get("ytd_budget_revenue", 0.0)), 2)
    manifest["ytd_revenue_variance"] = round(float(agg.get("ytd_revenue_variance", 0.0)), 2)
    manifest["ytd_actual_ebit"] = round(float(agg.get("ytd_actual_ebit", 0.0)), 2)
    manifest["ytd_budget_ebit"] = round(float(agg.get("ytd_budget_ebit", 0.0)), 2)
    manifest["ytd_ebit_variance"] = round(float(agg.get("ytd_ebit_variance", 0.0)), 2)
    manifest["latest_fy_revenue"] = round(float(agg.get("latest_fy_revenue", 0.0)), 2)
    manifest["latest_fy_ebit"] = round(float(agg.get("latest_fy_ebit", 0.0)), 2)
    manifest["latest_fy_revenue_vs_budget"] = round(float(agg.get("latest_fy_revenue_vs_budget", 0.0)), 2)
    manifest["latest_fy_ebit_vs_budget"] = round(float(agg.get("latest_fy_ebit_vs_budget", 0.0)), 2)
    manifest["fc1_fy_revenue"] = round(float(agg.get("fc_1_fy_revenue", 0.0)), 2)
    manifest["fc3_fy_revenue"] = round(float(agg.get("fc_3_fy_revenue", 0.0)), 2)
    manifest["fc6_fy_revenue"] = round(float(agg.get("fc_6_fy_revenue", 0.0)), 2)
    manifest["validation"] = checks
    with open("web/data/manifest.json", "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)

    return result.__class__(
        result.end_month,
        result.actual_months,
        result.forecast_months,
        result.operational_rows,
        result.journal_rows,
        result.forecast_rows,
        True,
    )
