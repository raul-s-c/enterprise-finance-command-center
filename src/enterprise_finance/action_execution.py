from __future__ import annotations

from functools import reduce
from operator import mul
import re

import pandas as pd


PLAN_COLUMNS = [
    "policy_version", "plan_id", "action_id", "action_key", "source_review_id", "scope_level", "entity", "division",
    "priority", "owner_role", "intervention_type", "primary_driver", "approved_month", "effective_month",
    "target_month", "benefit_end_month", "ramp_months", "approval_status", "execution_status",
    "price_uplift_pct", "volume_uplift_pct", "variable_cost_reduction_pct", "opex_reduction_pct",
    "expected_benefit_eur", "benefit_unit", "baseline_metric_value", "target_metric_value",
    "expected_outcome", "execution_evidence", "last_updated_month",
]

BENEFIT_COLUMNS = [
    "snapshot_month", "plan_id", "action_id", "scope_level", "entity", "division", "trigger_metric",
    "benefit_unit", "baseline_metric_value", "current_metric_value", "observed_metric_improvement",
    "expected_benefit_eur", "directional_realized_benefit_eur", "realization_pct", "execution_status",
    "attribution_method", "portfolio_additive",
]

BRIDGE_COLUMNS = [
    "month", "horizon_month", "scenario", "entity", "division", "action_revenue_impact", "action_gross_profit_impact",
    "action_opex_impact", "action_ebit_impact", "active_action_count",
]


def _text(value: object) -> str:
    return "" if pd.isna(value) else str(value)


def _number(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _period(value: object, fallback: str) -> pd.Period:
    try:
        return pd.Period(_text(value), freq="M")
    except (TypeError, ValueError):
        return pd.Period(fallback, freq="M")


def _slug(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", "-", _text(value).upper()).strip("-")


def _profile(metric: str, priority: str) -> dict[str, object]:
    name = metric.lower()
    scale = 1.0 if priority == "P1" else 0.65
    profile: dict[str, object] = {
        "intervention_type": "Performance recovery",
        "primary_driver": "Integrated performance",
        "price_uplift_pct": 0.0,
        "volume_uplift_pct": 0.0,
        "variable_cost_reduction_pct": 0.0,
        "opex_reduction_pct": 0.0,
        "recovery_share": 0.30 if priority == "P1" else 0.20,
    }
    if "forecast" in name or "mape" in name:
        profile.update(intervention_type="Forecast process correction", primary_driver="Forecast accuracy", recovery_share=0.0)
    elif "fx" in name:
        profile.update(intervention_type="FX exposure mitigation", primary_driver="FX exposure", recovery_share=0.0)
    elif "working capital" in name:
        profile.update(intervention_type="Working-capital release", primary_driver="Cash conversion", recovery_share=0.20)
    elif "free cash flow" in name:
        profile.update(intervention_type="Cash recovery", primary_driver="Cash conversion", recovery_share=0.20)
    elif "revenue per fte" in name:
        profile.update(
            intervention_type="Productivity recovery", primary_driver="Productivity",
            volume_uplift_pct=0.0025 * scale, opex_reduction_pct=0.0020 * scale,
        )
    elif "opex" in name:
        profile.update(
            intervention_type="Cost control", primary_driver="Operating expense",
            opex_reduction_pct=0.0080 * scale,
        )
    elif "gross profit" in name or "mix effect" in name:
        profile.update(
            intervention_type="Margin recovery", primary_driver="Variable cost and mix",
            variable_cost_reduction_pct=0.0060 * scale,
        )
    elif "price effect" in name:
        profile.update(
            intervention_type="Pricing recovery", primary_driver="Price",
            price_uplift_pct=0.0040 * scale,
        )
    elif "volume effect" in name or name == "revenue":
        profile.update(
            intervention_type="Commercial recovery", primary_driver="Volume",
            volume_uplift_pct=0.0040 * scale,
        )
    elif "ebit" in name:
        profile.update(
            intervention_type="Integrated EBIT recovery", primary_driver="Revenue, margin and OPEX",
            price_uplift_pct=0.0015 * scale, variable_cost_reduction_pct=0.0020 * scale,
            opex_reduction_pct=0.0030 * scale,
        )
    return profile


def _execution_status(action_status: str, effective: pd.Period, target: pd.Period, end: pd.Period) -> str:
    if action_status == "Cancelled":
        return "Cancelled"
    if end < effective:
        return "Approved"
    if action_status == "Closed":
        return "Benefits validated"
    if end <= target:
        return "Implementing"
    return "Benefits tracking"


def build_action_plans(
    actions: pd.DataFrame,
    end_month: str,
    previous_plans: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Create or carry forward one controlled execution plan per action cycle."""
    previous = previous_plans.copy() if previous_plans is not None else pd.DataFrame(columns=PLAN_COLUMNS)
    for column in PLAN_COLUMNS:
        if column not in previous:
            previous[column] = ""
    prior = {str(row.action_id): row for _, row in previous.iterrows()}
    end = pd.Period(end_month, freq="M")
    rows: list[dict] = []
    for _, action in actions.iterrows():
        action_id = _text(action.get("action_id"))
        old = prior.get(action_id)
        if old is not None and _text(old.get("policy_version")) == "0.18":
            record = old.to_dict()
        else:
            priority = _text(action.get("priority")) or "P2"
            profile = _profile(_text(action.get("trigger_metric")), priority)
            approved = _period(action.get("opened_month"), end_month)
            effective = approved + 1
            target = _period(action.get("due_month"), str(effective + 2))
            if target < effective:
                target = effective + 2
            trigger = _number(action.get("trigger_value"))
            metric_name = _text(action.get("trigger_metric")).lower()
            unit = "EUR" if abs(trigger) >= 1.0 and "mape" not in metric_name and "per fte" not in metric_name else "Non-financial"
            expected = abs(trigger) * float(profile.pop("recovery_share")) if unit == "EUR" else 0.0
            record = {
                "policy_version": "0.18",
                "plan_id": f"PLN-{_slug(action_id)}",
                "action_id": action_id,
                "action_key": _text(action.get("action_key")),
                "source_review_id": _text(action.get("origin_review_id")) or _text(action.get("review_id")),
                "scope_level": _text(action.get("scope_level")),
                "entity": _text(action.get("entity")),
                "division": _text(action.get("division")),
                "priority": priority,
                "owner_role": _text(action.get("owner_role")),
                "approved_month": str(approved),
                "effective_month": str(effective),
                "target_month": str(target),
                "benefit_end_month": str(effective + 11),
                "ramp_months": 3,
                "approval_status": "Approved",
                "expected_benefit_eur": round(expected, 2),
                "benefit_unit": unit,
                "baseline_metric_value": trigger,
                "target_metric_value": round(trigger + (abs(trigger) * 0.30 if trigger < 0 else -abs(trigger) * 0.30), 4),
                "expected_outcome": _text(action.get("expected_outcome")),
                "execution_evidence": f"Approved deterministic intervention linked to {_text(action.get('source_dataset'))}.",
                **profile,
            }
        effective = _period(record.get("effective_month"), end_month)
        target = _period(record.get("target_month"), str(effective + 2))
        record.update(
            action_key=_text(action.get("action_key")),
            owner_role=_text(action.get("owner_role")),
            execution_status=_execution_status(_text(action.get("status")), effective, target, end),
            last_updated_month=end_month,
        )
        rows.append({column: record.get(column, "") for column in PLAN_COLUMNS})
    return pd.DataFrame(rows, columns=PLAN_COLUMNS)


def _scope_matches(plan: dict, entity: str, division: str) -> bool:
    level = _text(plan.get("scope_level"))
    if level == "Group":
        return True
    if level == "Entity":
        return _text(plan.get("entity")) == entity
    if level == "Division":
        return _text(plan.get("division")) == division
    return _text(plan.get("entity")) == entity and _text(plan.get("division")) == division


def _progress(plan: dict, month: str) -> float:
    current = pd.Period(month, freq="M")
    start = _period(plan.get("effective_month"), month)
    finish = _period(plan.get("benefit_end_month"), str(start + 11))
    if current < start or current > finish or _text(plan.get("execution_status")) == "Cancelled":
        return 0.0
    elapsed = (current.year - start.year) * 12 + current.month - start.month + 1
    return min(max(elapsed / max(int(_number(plan.get("ramp_months"), 3)), 1), 0.0), 1.0)


def intervention_effects(config: dict, month: str, entity: str, division: str) -> dict[str, object]:
    plans = config.get("management_interventions", []) or []
    matched = [p for p in plans if _text(p.get("approval_status")) == "Approved" and _scope_matches(p, entity, division)]
    progresses = [(plan, _progress(plan, month)) for plan in matched]
    progresses = [(plan, progress) for plan, progress in progresses if progress > 0]
    def combined(field: str) -> float:
        rates = [max(min(_number(plan.get(field)) * progress, 0.05), 0.0) for plan, progress in progresses]
        return 1.0 - reduce(mul, (1.0 - rate for rate in rates), 1.0)
    return {
        "price_uplift_pct": combined("price_uplift_pct"),
        "volume_uplift_pct": combined("volume_uplift_pct"),
        "variable_cost_reduction_pct": combined("variable_cost_reduction_pct"),
        "opex_reduction_pct": combined("opex_reduction_pct"),
        "active_action_count": len(progresses),
    }


def incremental_intervention_effects(config: dict, vintage: str, target: str, entity: str, division: str) -> dict[str, object]:
    visible_config = dict(config)
    visible_config["management_interventions"] = [
        plan for plan in (config.get("management_interventions", []) or [])
        if _text(plan.get("approved_month")) <= vintage
    ]
    before = intervention_effects(visible_config, vintage, entity, division)
    after = intervention_effects(visible_config, target, entity, division)
    result: dict[str, object] = {"active_action_count": after["active_action_count"]}
    for field in ["price_uplift_pct", "volume_uplift_pct", "variable_cost_reduction_pct", "opex_reduction_pct"]:
        result[field] = max(float(after[field]) - float(before[field]), 0.0)
    return result


def build_benefit_history(
    plans: pd.DataFrame,
    actions: pd.DataFrame,
    review_history: pd.DataFrame,
    end_month: str,
    previous_history: pd.DataFrame | None = None,
) -> pd.DataFrame:
    prior = previous_history.copy() if previous_history is not None else pd.DataFrame(columns=BENEFIT_COLUMNS)
    action_map = {str(row.action_id): row for _, row in actions.iterrows()}
    review_map = {str(row.review_id): row for _, row in review_history.iterrows()} if "review_id" in review_history else {}
    rows: list[dict] = []
    for _, plan in plans.iterrows():
        action = action_map.get(str(plan.action_id))
        source = review_map.get(str(plan.source_review_id))
        current = review_map.get(_text(action.get("review_id")) if action is not None else "")
        baseline = _number(source.get("actual_value")) if source is not None else _number(plan.baseline_metric_value)
        current_value = _number(current.get("actual_value"), baseline) if current is not None else baseline
        favorable_higher = bool(source.get("favorable", False)) if source is not None else baseline < 0
        metric = _text(action.get("trigger_metric")) if action is not None else ""
        if metric in {"OPEX", "One-month revenue MAPE"}:
            improvement = baseline - current_value
        else:
            improvement = current_value - baseline
        expected = _number(plan.expected_benefit_eur)
        directional = min(max(improvement, 0.0), expected) if _text(plan.benefit_unit) == "EUR" else 0.0
        rows.append({
            "snapshot_month": end_month,
            "plan_id": plan.plan_id,
            "action_id": plan.action_id,
            "scope_level": plan.scope_level,
            "entity": plan.entity,
            "division": plan.division,
            "trigger_metric": metric,
            "benefit_unit": plan.benefit_unit,
            "baseline_metric_value": round(baseline, 4),
            "current_metric_value": round(current_value, 4),
            "observed_metric_improvement": round(improvement, 4),
            "expected_benefit_eur": round(expected, 2),
            "directional_realized_benefit_eur": round(directional, 2),
            "realization_pct": round(directional / expected, 4) if expected else 0.0,
            "execution_status": plan.execution_status,
            "attribution_method": "Directional trigger improvement; non-additive",
            "portfolio_additive": False,
        })
    current_frame = pd.DataFrame(rows, columns=BENEFIT_COLUMNS)
    combined = pd.concat([prior, current_frame], ignore_index=True)
    return combined.drop_duplicates(["snapshot_month", "plan_id"], keep="last")


def build_forecast_bridge(forecasts: pd.DataFrame, end_month: str) -> pd.DataFrame:
    current = forecasts[forecasts.vintage.eq(end_month)].copy() if not forecasts.empty else pd.DataFrame()
    required = {
        "action_revenue_impact_forecast", "action_gross_profit_impact_forecast",
        "action_opex_impact_forecast", "action_ebit_impact_forecast", "active_action_count",
    }
    if current.empty or not required <= set(current.columns):
        return pd.DataFrame(columns=BRIDGE_COLUMNS)
    out = current.groupby(["month", "horizon_month", "scenario", "entity", "division"], as_index=False).agg(
        action_revenue_impact=("action_revenue_impact_forecast", "sum"),
        action_gross_profit_impact=("action_gross_profit_impact_forecast", "sum"),
        action_opex_impact=("action_opex_impact_forecast", "sum"),
        action_ebit_impact=("action_ebit_impact_forecast", "sum"),
        active_action_count=("active_action_count", "max"),
    )
    return out[BRIDGE_COLUMNS]


def validate_action_execution(
    plans: pd.DataFrame,
    actions: pd.DataFrame,
    benefits: pd.DataFrame,
    bridge: pd.DataFrame,
    end_month: str,
) -> dict:
    active_action_ids = set(actions.action_id.astype(str))
    plan_ids = set(plans.action_id.astype(str))
    current_benefits = benefits[benefits.snapshot_month.eq(end_month)] if not benefits.empty else benefits
    numeric_rates = ["price_uplift_pct", "volume_uplift_pct", "variable_cost_reduction_pct", "opex_reduction_pct"]
    checks = {
        "action_execution_missing_plan_columns": len(set(PLAN_COLUMNS) - set(plans.columns)),
        "action_execution_duplicate_plan_ids": int(plans.plan_id.duplicated().sum()) if "plan_id" in plans else len(plans),
        "action_execution_duplicate_action_ids": int(plans.action_id.duplicated().sum()) if "action_id" in plans else len(plans),
        "action_execution_actions_without_plan": len(active_action_ids - plan_ids),
        "action_execution_orphan_plans": len(plan_ids - active_action_ids),
        "action_execution_invalid_approval": int((~plans.approval_status.isin(["Approved", "Rejected"])).sum()),
        "action_execution_invalid_dates": int((plans.effective_month.astype(str) <= plans.approved_month.astype(str)).sum()),
        "action_execution_invalid_rates": int(((plans[numeric_rates].apply(pd.to_numeric, errors="coerce").fillna(-1) < 0).any(axis=1) | (plans[numeric_rates].apply(pd.to_numeric, errors="coerce").fillna(1) > 0.05).any(axis=1)).sum()),
        "action_execution_missing_evidence": int(plans.execution_evidence.astype(str).str.strip().eq("").sum()),
        "action_execution_missing_current_benefit": len(set(plans.plan_id.astype(str)) - set(current_benefits.plan_id.astype(str))) if not current_benefits.empty else len(plans),
        "action_execution_duplicate_benefit_rows": int(benefits.duplicated(["snapshot_month", "plan_id"]).sum()) if not benefits.empty else 0,
        "action_execution_additive_directional_rows": int(current_benefits.portfolio_additive.astype(str).str.lower().eq("true").sum()) if not current_benefits.empty else 0,
        "action_execution_negative_expected_benefit": int((pd.to_numeric(plans.expected_benefit_eur, errors="coerce").fillna(-1) < 0).sum()),
        "action_execution_forecast_bridge_missing": int(bridge.empty),
        "action_execution_forecast_bridge_duplicate_rows": int(bridge.duplicated(["month", "scenario", "entity", "division"]).sum()) if not bridge.empty else 0,
    }
    checks["passed"] = all(value == 0 for value in checks.values())
    return checks
