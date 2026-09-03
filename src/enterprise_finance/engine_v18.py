from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import yaml

from . import engine as base_engine
from .action_execution import (
    build_action_plans,
    build_benefit_history,
    build_forecast_bridge,
    validate_action_execution,
)
from .engine_v17 import build as build_v17


VERSION = "0.18.0"


def _read_optional(path: str) -> pd.DataFrame:
    source = Path(path)
    return pd.read_csv(source, low_memory=False).fillna("") if source.exists() else pd.DataFrame()


def _write_csv(frame: pd.DataFrame, path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def _runtime_config(config_path: str, plans: pd.DataFrame) -> str:
    config = base_engine.load_config(config_path)
    config["management_interventions"] = json.loads(plans.to_json(orient="records"))
    target = Path("data/runtime/v018_company.yml")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(config, handle, sort_keys=False, allow_unicode=True)
    return str(target)


def _actual_action_impact(operations: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "month", "entity", "division", "action_revenue_impact", "action_gross_profit_impact",
        "action_opex_impact", "action_ebit_impact", "active_action_count",
    ]
    required = {
        "management_action_revenue_impact", "management_action_gross_profit_impact",
        "management_action_opex_impact", "management_action_ebit_impact", "management_action_count",
    }
    if operations.empty or not required <= set(operations.columns):
        return pd.DataFrame(columns=columns)
    out = operations.groupby(["month", "entity", "division"], as_index=False).agg(
        action_revenue_impact=("management_action_revenue_impact", "sum"),
        action_gross_profit_impact=("management_action_gross_profit_impact", "sum"),
        action_opex_impact=("management_action_opex_impact", "sum"),
        action_ebit_impact=("management_action_ebit_impact", "sum"),
        active_action_count=("management_action_count", "max"),
    )
    return out[columns]


def build(end_month: str, config_path: str = "config/company.yml", allow_live_macro: bool = True):
    """Run v0.17 with approved interventions, then measure execution and benefits."""
    previous_actions = _read_optional("data/processed/management_actions.csv")
    previous_plans = _read_optional("data/processed/management_action_plans.csv")
    previous_benefits = _read_optional("data/processed/management_action_benefits.csv")

    preliminary_plans = build_action_plans(previous_actions, end_month, previous_plans)
    execution_config = _runtime_config(config_path, preliminary_plans)
    result = build_v17(end_month, config_path=execution_config, allow_live_macro=allow_live_macro)

    actions = _read_optional("data/processed/management_actions.csv")
    review_history = _read_optional("data/processed/performance_review_history.csv")
    operations = _read_optional("data/runtime/operational.csv.gz")
    forecasts = _read_optional("data/processed/forecast_vintages.csv")

    plans = build_action_plans(actions, end_month, preliminary_plans)
    benefits = build_benefit_history(plans, actions, review_history, end_month, previous_benefits)
    forecast_bridge = build_forecast_bridge(forecasts, end_month)
    actual_impact = _actual_action_impact(operations)
    execution_checks = validate_action_execution(plans, actions, benefits, forecast_bridge, end_month)
    execution_checks["action_execution_actual_impact_missing"] = int(actual_impact.empty)
    execution_checks["passed"] = bool(
        execution_checks["passed"] and execution_checks["action_execution_actual_impact_missing"] == 0
    )

    with open("data/processed/validation.json", encoding="utf-8") as handle:
        checks = json.load(handle)
    checks.update({key: value for key, value in execution_checks.items() if key != "passed"})
    checks["passed"] = bool(checks.get("passed", False) and execution_checks["passed"])
    if not checks["passed"]:
        raise RuntimeError(f"Management action execution controls failed: {checks}")

    _write_csv(plans, "data/processed/management_action_plans.csv")
    _write_csv(benefits, "data/processed/management_action_benefits.csv")
    _write_csv(forecast_bridge, "data/processed/management_action_forecast_bridge.csv")
    _write_csv(actual_impact, "data/processed/management_action_actual_impact.csv")
    with open("data/processed/validation.json", "w", encoding="utf-8") as handle:
        json.dump(checks, handle, indent=2)

    current_benefits = benefits[benefits.snapshot_month.eq(end_month)]
    latest_actual = actual_impact[actual_impact.month.eq(end_month)]
    base_bridge = forecast_bridge[
        forecast_bridge.scenario.eq("Base") & forecast_bridge.horizon_month.le(12)
    ]
    rate_columns = [
        "price_uplift_pct", "volume_uplift_pct", "variable_cost_reduction_pct", "opex_reduction_pct"
    ]
    operationalized = int((plans[rate_columns].apply(pd.to_numeric, errors="coerce").fillna(0.0).sum(axis=1) > 0).sum())
    summary = {
        "approved_plans": int(plans.approval_status.eq("Approved").sum()),
        "operationalized_plans": operationalized,
        "governance_only_plans": int(len(plans) - operationalized),
        "implementing_plans": int(plans.execution_status.eq("Implementing").sum()),
        "benefits_tracking_plans": int(plans.execution_status.eq("Benefits tracking").sum()),
        "validated_plans": int(plans.execution_status.eq("Benefits validated").sum()),
        "gross_expected_benefit_eur": round(float(pd.to_numeric(plans.expected_benefit_eur, errors="coerce").fillna(0.0).sum()), 2),
        "directional_actions_improving": int((pd.to_numeric(current_benefits.observed_metric_improvement, errors="coerce").fillna(0.0) > 0).sum()),
        "latest_additive_actual_ebit_impact": round(float(latest_actual.action_ebit_impact.sum()), 2) if not latest_actual.empty else 0.0,
        "base_12m_action_revenue_impact": round(float(base_bridge.action_revenue_impact.sum()), 2),
        "base_12m_action_ebit_impact": round(float(base_bridge.action_ebit_impact.sum()), 2),
    }

    with open("web/data/dashboard.json", encoding="utf-8") as handle:
        dashboard = json.load(handle)
    dashboard["meta"]["version"] = VERSION
    dashboard["management_action_plans"] = base_engine._records(plans)
    dashboard["management_action_benefits"] = base_engine._records(benefits)
    dashboard["management_action_forecast_bridge"] = base_engine._records(forecast_bridge)
    dashboard["management_action_actual_impact"] = base_engine._records(actual_impact)
    dashboard["management_action_execution_summary"] = summary
    dashboard["validation"] = checks
    with open("web/data/dashboard.json", "w", encoding="utf-8") as handle:
        json.dump(dashboard, handle, separators=(",", ":"), allow_nan=False)

    with open("web/data/manifest.json", encoding="utf-8") as handle:
        manifest = json.load(handle)
    manifest.update({
        "version": VERSION,
        "management_action_plan_rows": int(len(plans)),
        "management_action_benefit_rows": int(len(benefits)),
        "management_action_forecast_bridge_rows": int(len(forecast_bridge)),
        **summary,
        "validation": checks,
    })
    with open("web/data/manifest.json", "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
    return result
