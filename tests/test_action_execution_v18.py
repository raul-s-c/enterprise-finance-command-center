import pandas as pd

from enterprise_finance.action_execution import (
    build_action_plans,
    build_benefit_history,
    build_forecast_bridge,
    incremental_intervention_effects,
    intervention_effects,
    validate_action_execution,
)


def _action(metric: str = "EBIT", status: str = "Open") -> dict:
    return {
        "action_id": "ACT-202608-EBIT", "action_key": "GROUP|ALL|ALL|EBIT|BUDGET",
        "review_id": "REV-202608-EBIT", "origin_review_id": "REV-202608-EBIT",
        "review_month": "2026-08", "scope_level": "Group", "entity": "All", "division": "All",
        "priority": "P1", "owner_role": "CFO", "opened_month": "2026-08", "last_seen_month": "2026-08",
        "due_month": "2026-10", "closed_month": "", "cancelled_month": "", "status": status,
        "age_months": 0, "carry_forward_months": 0, "overdue_months": 0, "overdue": False,
        "escalation_level": "None", "occurrence_count": 1, "action": "Recover EBIT.",
        "expected_outcome": "Return EBIT to budget.", "closure_evidence": "", "trigger_metric": metric,
        "trigger_value": -1_000_000.0, "source_dataset": "budget_performance.csv",
    }


def _review(review_id: str, value: float) -> dict:
    return {
        "review_id": review_id, "review_month": "2026-08", "scope_level": "Group", "entity": "All",
        "division": "All", "category": "Monthly P&L vs Budget", "metric": "EBIT", "comparison": "Budget",
        "unit": "EUR", "actual_value": value, "benchmark_value": 0.0, "variance": value,
        "materiality_pct": 0.2, "favorable": False, "severity": "Critical", "action_required": True,
        "source_dataset": "budget_performance.csv", "source_key": "key", "headline": "EBIT missed.",
        "explanation": "Controlled source.",
    }


def test_plan_is_deterministic_and_intervention_starts_after_approval():
    actions = pd.DataFrame([_action()])
    first = build_action_plans(actions, "2026-08")
    repeated = build_action_plans(actions, "2026-08", first)
    pd.testing.assert_frame_equal(first, repeated)
    plan = first.iloc[0]
    assert plan.approval_status == "Approved"
    assert plan.effective_month == "2026-09"
    assert plan.expected_benefit_eur == 300_000.0

    config = {"management_interventions": first.to_dict("records")}
    assert intervention_effects(config, "2026-08", "DE01", "Software")["active_action_count"] == 0
    september = intervention_effects(config, "2026-09", "DE01", "Software")
    november = intervention_effects(config, "2026-11", "DE01", "Software")
    assert september["active_action_count"] == 1
    assert 0 < september["opex_reduction_pct"] < november["opex_reduction_pct"]
    assert incremental_intervention_effects(config, "2026-07", "2026-09", "DE01", "Software")["active_action_count"] == 0
    assert incremental_intervention_effects(config, "2026-08", "2026-09", "DE01", "Software")["active_action_count"] == 1


def test_scope_and_governance_only_actions_do_not_create_unrelated_operating_effects():
    entity_action = _action("OPEX")
    entity_action.update(scope_level="Entity", entity="US01", action_id="ACT-US-OPEX")
    forecast_action = _action("One-month revenue MAPE")
    forecast_action.update(action_id="ACT-MAPE", action_key="GROUP|MAPE", trigger_value=0.09)
    plans = build_action_plans(pd.DataFrame([entity_action, forecast_action]), "2026-08")
    config = {"management_interventions": plans.to_dict("records")}
    us = intervention_effects(config, "2026-10", "US01", "Software")
    de = intervention_effects(config, "2026-10", "DE01", "Software")
    assert us["opex_reduction_pct"] > 0
    assert de["opex_reduction_pct"] == 0
    assert plans.loc[plans.action_id.eq("ACT-MAPE"), "expected_benefit_eur"].iloc[0] == 0


def test_pre_release_plan_is_migrated_once_to_the_v018_policy():
    actions = pd.DataFrame([_action("Revenue per FTE")])
    legacy = build_action_plans(actions, "2026-08")
    legacy.loc[0, "policy_version"] = ""
    legacy.loc[0, "benefit_unit"] = "EUR"
    legacy.loc[0, "expected_benefit_eur"] = 99.0
    migrated = build_action_plans(actions, "2026-08", legacy)
    assert migrated.iloc[0].policy_version == "0.18"
    assert migrated.iloc[0].benefit_unit == "Non-financial"
    assert migrated.iloc[0].expected_benefit_eur == 0.0


def test_directional_benefits_remain_non_additive_and_controls_pass():
    actions = pd.DataFrame([_action()])
    plans = build_action_plans(actions, "2026-08")
    reviews = pd.DataFrame([_review("REV-202608-EBIT", -1_000_000.0)])
    benefits = build_benefit_history(plans, actions, reviews, "2026-08")
    forecasts = pd.DataFrame([{
        "vintage": "2026-08", "month": "2026-09", "horizon_month": 1, "scenario": "Base", "entity": "DE01", "division": "Software",
        "action_revenue_impact_forecast": 100.0, "action_gross_profit_impact_forecast": 60.0,
        "action_opex_impact_forecast": 20.0, "action_ebit_impact_forecast": 80.0,
        "active_action_count": 1,
    }])
    bridge = build_forecast_bridge(forecasts, "2026-08")
    checks = validate_action_execution(plans, actions, benefits, bridge, "2026-08")
    assert checks["passed"], checks
    assert not bool(benefits.iloc[0].portfolio_additive)
    assert bridge.iloc[0].action_ebit_impact == 80.0


def test_controls_reject_orphan_plan_and_missing_execution_evidence():
    actions = pd.DataFrame([_action()])
    plans = build_action_plans(actions, "2026-08")
    plans.loc[0, "action_id"] = "ACT-ORPHAN"
    plans.loc[0, "execution_evidence"] = ""
    reviews = pd.DataFrame([_review("REV-202608-EBIT", -1_000_000.0)])
    benefits = build_benefit_history(plans, actions, reviews, "2026-08")
    bridge = pd.DataFrame([{
        "month": "2026-09", "horizon_month": 1, "scenario": "Base", "entity": "DE01", "division": "Software", "action_revenue_impact": 0.0,
        "action_gross_profit_impact": 0.0, "action_opex_impact": 0.0, "action_ebit_impact": 0.0,
        "active_action_count": 0,
    }])
    checks = validate_action_execution(plans, actions, benefits, bridge, "2026-08")
    assert not checks["passed"]
    assert checks["action_execution_orphan_plans"] == 1
    assert checks["action_execution_actions_without_plan"] == 1
    assert checks["action_execution_missing_evidence"] == 1
