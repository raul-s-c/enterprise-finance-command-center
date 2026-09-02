import pandas as pd

from enterprise_finance.performance_review import (
    build_performance_review,
    validate_performance_review,
)


END_MONTH = "2026-08"


def _fixtures():
    budget = pd.DataFrame(
        [
            {
                "month": END_MONTH,
                "entity": "DE01",
                "division": "Hardware",
                "revenue": 8_500_000.0,
                "revenue_budget": 10_000_000.0,
                "gross_profit": 2_300_000.0,
                "gross_profit_budget": 3_000_000.0,
                "opex": 1_700_000.0,
                "opex_budget": 1_200_000.0,
                "ebit": 500_000.0,
                "ebit_budget": 1_600_000.0,
            },
            {
                "month": END_MONTH,
                "entity": "ES01",
                "division": "Software",
                "revenue": 5_300_000.0,
                "revenue_budget": 5_000_000.0,
                "gross_profit": 3_800_000.0,
                "gross_profit_budget": 3_500_000.0,
                "opex": 1_000_000.0,
                "opex_budget": 1_100_000.0,
                "ebit": 2_600_000.0,
                "ebit_budget": 2_200_000.0,
            },
        ]
    )
    pvm = pd.DataFrame(
        [
            {
                "current_month": END_MONTH,
                "comparison_month": "2025-08",
                "division": "Hardware",
                "revenue_change": -1_200_000.0,
                "price_effect": 200_000.0,
                "volume_effect": -1_100_000.0,
                "mix_effect": -300_000.0,
            },
            {
                "current_month": END_MONTH,
                "comparison_month": "2025-08",
                "division": "Software",
                "revenue_change": 400_000.0,
                "price_effect": 250_000.0,
                "volume_effect": 100_000.0,
                "mix_effect": 50_000.0,
            },
        ]
    )
    cc = pd.DataFrame(
        [
            {
                "month": END_MONTH,
                "entity": "DE01",
                "division": "Hardware",
                "constant_currency_revenue": 8_700_000.0,
                "revenue_fx_effect": -200_000.0,
                "constant_currency_ebit": 550_000.0,
                "ebit_fx_effect": -50_000.0,
            },
            {
                "month": END_MONTH,
                "entity": "ES01",
                "division": "Software",
                "constant_currency_revenue": 5_300_000.0,
                "revenue_fx_effect": 0.0,
                "constant_currency_ebit": 2_600_000.0,
                "ebit_fx_effect": 0.0,
            },
        ]
    )
    working_capital = pd.DataFrame(
        [
            {"month": "2026-07", "net_working_capital": 20_000_000.0},
            {"month": END_MONTH, "net_working_capital": 23_500_000.0},
        ]
    )
    cash_flow = pd.DataFrame(
        [
            {"month": "2026-07", "entity": "DE01", "free_cash_flow": 2_000_000.0},
            {"month": "2026-07", "entity": "ES01", "free_cash_flow": 1_000_000.0},
            {"month": END_MONTH, "entity": "DE01", "free_cash_flow": 500_000.0},
            {"month": END_MONTH, "entity": "ES01", "free_cash_flow": 400_000.0},
        ]
    )
    workforce = pd.DataFrame(
        [
            {
                "month": "2026-07",
                "revenue_per_fte": 110_000.0,
                "personnel_cost": 2_000_000.0,
                "ending_fte": 200.0,
            },
            {
                "month": END_MONTH,
                "revenue_per_fte": 92_000.0,
                "personnel_cost": 2_300_000.0,
                "ending_fte": 210.0,
            },
        ]
    )
    fy_bridge = pd.DataFrame(
        [
            {
                "close_month": END_MONTH,
                "entity": "DE01",
                "division": "Hardware",
                "latest_fy_revenue": 102_000_000.0,
                "fy_budget_revenue": 110_000_000.0,
                "latest_fy_ebit": 11_000_000.0,
                "fy_budget_ebit": 16_000_000.0,
            },
            {
                "close_month": END_MONTH,
                "entity": "ES01",
                "division": "Software",
                "latest_fy_revenue": 65_000_000.0,
                "fy_budget_revenue": 63_000_000.0,
                "latest_fy_ebit": 29_000_000.0,
                "fy_budget_ebit": 28_000_000.0,
            },
        ]
    )
    accuracy = pd.DataFrame(
        [
            {"month": END_MONTH, "horizon_month": 1, "abs_pct_error": 0.12},
            {"month": END_MONTH, "horizon_month": 1, "abs_pct_error": 0.08},
            {"month": END_MONTH, "horizon_month": 3, "abs_pct_error": 0.20},
        ]
    )
    return {
        "budget_performance": budget,
        "price_volume_mix": pvm,
        "constant_currency": cc,
        "working_capital": working_capital,
        "cash_flow": cash_flow,
        "workforce_summary": workforce,
        "fy_plan_bridge": fy_bridge,
        "forecast_accuracy": accuracy,
    }


def test_performance_review_is_source_tied_and_actionable():
    fixtures = _fixtures()
    review, actions, summary = build_performance_review(**fixtures, end_month=END_MONTH)
    expected_review, _, _ = build_performance_review(**fixtures, end_month=END_MONTH)
    checks = validate_performance_review(review, actions, summary, expected_review, END_MONTH)

    assert checks["passed"], checks
    assert not review.empty
    assert not actions.empty
    assert len(review.review_id) == review.review_id.nunique()
    assert set(review[review.action_required].review_id) <= set(actions.review_id)
    assert set(actions.priority) <= {"P1", "P2"}
    assert set(actions.status) == {"Open"}
    assert set(actions.owner_role.astype(str)) != {""}
    assert summary.iloc[0].review_month == END_MONTH


def test_review_contains_group_and_filterable_scopes():
    review, _, _ = build_performance_review(**_fixtures(), end_month=END_MONTH)

    assert {"Group", "Entity", "Division", "Entity Division"} <= set(review.scope_level)
    group = review[review.scope_level.eq("Group")]
    assert {"Revenue", "EBIT", "Price effect", "Revenue FX effect", "Free cash flow"} <= set(group.metric)
    hardware = review[review.scope_level.eq("Division") & review.division.eq("Hardware")]
    assert {"Revenue", "Volume effect", "Revenue FX effect"} <= set(hardware.metric)


def test_review_control_detects_source_value_drift():
    fixtures = _fixtures()
    review, actions, summary = build_performance_review(**fixtures, end_month=END_MONTH)
    expected_review = review.copy()
    review = review.copy()
    review.loc[0, "actual_value"] += 100.0

    checks = validate_performance_review(review, actions, summary, expected_review, END_MONTH)

    assert not checks["passed"]
    assert checks["performance_review_source_max_gap"] == 100.0


def test_review_control_detects_missing_required_action():
    fixtures = _fixtures()
    review, actions, summary = build_performance_review(**fixtures, end_month=END_MONTH)
    expected_review = review.copy()
    actions = actions.iloc[1:].copy()

    checks = validate_performance_review(review, actions, summary, expected_review, END_MONTH)

    assert not checks["passed"]
    assert checks["performance_review_required_actions_missing"] == 1


def test_clean_close_can_have_an_empty_action_register():
    fixtures = _fixtures()
    budget = fixtures["budget_performance"].copy()
    for metric in ["revenue", "gross_profit", "ebit"]:
        budget[f"{metric}_budget"] = budget[metric]
    budget["opex_budget"] = budget.opex
    fixtures["budget_performance"] = budget
    fixtures["price_volume_mix"].loc[:, ["price_effect", "volume_effect", "mix_effect"]] = 0.0
    fixtures["constant_currency"].loc[:, ["revenue_fx_effect", "ebit_fx_effect"]] = 0.0
    fixtures["working_capital"].loc[1, "net_working_capital"] = fixtures["working_capital"].loc[0, "net_working_capital"]
    fixtures["cash_flow"].loc[fixtures["cash_flow"].month.eq(END_MONTH), "free_cash_flow"] = 1_500_000.0
    fixtures["workforce_summary"].loc[1, ["revenue_per_fte", "personnel_cost", "ending_fte"]] = fixtures["workforce_summary"].loc[0, ["revenue_per_fte", "personnel_cost", "ending_fte"]].to_numpy()
    fixtures["fy_plan_bridge"]["latest_fy_revenue"] = fixtures["fy_plan_bridge"].fy_budget_revenue
    fixtures["fy_plan_bridge"]["latest_fy_ebit"] = fixtures["fy_plan_bridge"].fy_budget_ebit
    fixtures["forecast_accuracy"]["abs_pct_error"] = 0.04

    review, actions, summary = build_performance_review(**fixtures, end_month=END_MONTH)
    checks = validate_performance_review(review, actions, summary, review.copy(), END_MONTH)

    assert actions.empty
    assert checks["passed"], checks
