from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from . import engine as base_engine
from .engine_v15 import build as build_v15
from .performance_review import build_performance_review, validate_performance_review


VERSION = "0.16.0"


def _read_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def _write_csv(frame: pd.DataFrame, path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def build(end_month: str, config_path: str = "config/company.yml", allow_live_macro: bool = True):
    """Run v0.15 and add a source-tied monthly performance review and action register."""
    result = build_v15(end_month, config_path=config_path, allow_live_macro=allow_live_macro)

    inputs = {
        "budget_performance": _read_csv("data/processed/budget_performance.csv"),
        "price_volume_mix": _read_csv("data/processed/price_volume_mix.csv"),
        "constant_currency": _read_csv("data/processed/constant_currency_analysis.csv"),
        "working_capital": _read_csv("data/processed/working_capital.csv"),
        "cash_flow": _read_csv("data/processed/cash_flow.csv"),
        "workforce_summary": _read_csv("data/processed/workforce_summary.csv"),
        "fy_plan_bridge": _read_csv("data/processed/fy_plan_bridge.csv"),
        "forecast_accuracy": _read_csv("data/processed/forecast_accuracy.csv"),
    }
    review, actions, summary = build_performance_review(**inputs, end_month=end_month)
    expected_review, _, _ = build_performance_review(**inputs, end_month=end_month)
    review_checks = validate_performance_review(review, actions, summary, expected_review, end_month)

    with open("data/processed/validation.json", "r", encoding="utf-8") as handle:
        checks = json.load(handle)
    checks.update({key: value for key, value in review_checks.items() if key != "passed"})
    checks["monthly_performance_review_missing"] = int(review.empty)
    checks["passed"] = bool(
        checks.get("passed", False)
        and review_checks["passed"]
        and checks["monthly_performance_review_missing"] == 0
    )
    if not checks["passed"]:
        raise RuntimeError(f"Monthly performance review controls failed: {checks}")

    _write_csv(review, "data/processed/monthly_performance_review.csv")
    _write_csv(actions, "data/processed/management_actions.csv")
    _write_csv(summary, "data/processed/performance_review_summary.csv")
    with open("data/processed/validation.json", "w", encoding="utf-8") as handle:
        json.dump(checks, handle, indent=2)

    with open("web/data/dashboard.json", "r", encoding="utf-8") as handle:
        dashboard = json.load(handle)
    dashboard["meta"]["version"] = VERSION
    dashboard["performance_review"] = base_engine._records(review)
    dashboard["management_actions"] = base_engine._records(actions)
    dashboard["performance_review_summary"] = base_engine._records(summary)
    dashboard["validation"] = checks
    with open("web/data/dashboard.json", "w", encoding="utf-8") as handle:
        json.dump(dashboard, handle, separators=(",", ":"), allow_nan=False)

    overview = summary.iloc[0]
    with open("web/data/manifest.json", "r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    manifest["version"] = VERSION
    manifest["performance_review_rows"] = int(len(review))
    manifest["management_action_rows"] = int(len(actions))
    manifest["group_adverse_insights"] = int(overview.group_adverse_insights)
    manifest["open_management_actions"] = int(overview.open_actions)
    manifest["p1_management_actions"] = int(overview.p1_actions)
    manifest["latest_revenue_vs_budget"] = round(float(overview.revenue_vs_budget), 2)
    manifest["latest_ebit_vs_budget"] = round(float(overview.ebit_vs_budget), 2)
    manifest["latest_fy_ebit_vs_budget"] = round(float(overview.fy_ebit_vs_budget), 2)
    manifest["latest_free_cash_flow"] = round(float(overview.free_cash_flow), 2)
    manifest["latest_net_working_capital_change"] = round(float(overview.net_working_capital_change), 2)
    manifest["validation"] = checks
    with open("web/data/manifest.json", "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)

    return result
