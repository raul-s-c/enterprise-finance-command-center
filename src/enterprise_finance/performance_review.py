from __future__ import annotations

import re
from typing import Iterable

import pandas as pd


REVIEW_COLUMNS = [
    "review_id",
    "review_month",
    "scope_level",
    "entity",
    "division",
    "category",
    "metric",
    "comparison",
    "unit",
    "actual_value",
    "benchmark_value",
    "variance",
    "materiality_pct",
    "favorable",
    "severity",
    "action_required",
    "source_dataset",
    "source_key",
    "headline",
    "explanation",
]

ACTION_COLUMNS = [
    "action_id",
    "review_id",
    "review_month",
    "scope_level",
    "entity",
    "division",
    "priority",
    "owner_role",
    "due_month",
    "status",
    "action",
    "expected_outcome",
    "trigger_metric",
    "trigger_value",
    "source_dataset",
]


def _slug(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", "-", str(value).upper()).strip("-")


def _euro(value: float) -> str:
    value = float(value)
    absolute = abs(value)
    if absolute >= 1_000_000:
        return f"€{absolute / 1_000_000:.1f}m"
    if absolute >= 1_000:
        return f"€{absolute / 1_000:.1f}k"
    return f"€{absolute:,.0f}"


def _severity(materiality_pct: float) -> str:
    value = abs(float(materiality_pct))
    if value >= 0.15:
        return "Critical"
    if value >= 0.05:
        return "High"
    if value >= 0.03:
        return "Medium"
    return "Low"


def _scope_frames(frame: pd.DataFrame) -> Iterable[tuple[str, str, str, pd.DataFrame]]:
    yield "Group", "All", "All", frame
    for entity, rows in frame.groupby("entity", sort=True):
        yield "Entity", str(entity), "All", rows
    for division, rows in frame.groupby("division", sort=True):
        yield "Division", "All", str(division), rows
    for (entity, division), rows in frame.groupby(["entity", "division"], sort=True):
        yield "Entity Division", str(entity), str(division), rows


def _scope_name(scope_level: str, entity: str, division: str) -> str:
    if scope_level == "Group":
        return "Group"
    if scope_level == "Entity":
        return entity
    if scope_level == "Division":
        return division
    return f"{entity} / {division}"


def _review_row(
    *,
    review_month: str,
    scope_level: str,
    entity: str,
    division: str,
    category: str,
    metric: str,
    comparison: str,
    unit: str,
    actual_value: float,
    benchmark_value: float,
    variance: float,
    favorable: bool,
    source_dataset: str,
    source_key: str,
    headline: str,
    explanation: str,
    materiality_denominator: float | None = None,
) -> dict:
    denominator = max(
        abs(float(materiality_denominator if materiality_denominator is not None else benchmark_value)),
        1.0,
    )
    materiality = abs(float(variance)) / denominator
    severity = _severity(materiality)
    review_id = "-".join(
        [
            "REV",
            review_month.replace("-", ""),
            _slug(category),
            _slug(scope_level),
            _slug(entity),
            _slug(division),
            _slug(metric),
        ]
    )
    return {
        "review_id": review_id,
        "review_month": review_month,
        "scope_level": scope_level,
        "entity": entity,
        "division": division,
        "category": category,
        "metric": metric,
        "comparison": comparison,
        "unit": unit,
        "actual_value": round(float(actual_value), 4),
        "benchmark_value": round(float(benchmark_value), 4),
        "variance": round(float(variance), 4),
        "materiality_pct": round(materiality, 6),
        "favorable": bool(favorable),
        "severity": severity,
        "action_required": bool(not favorable and severity in {"Critical", "High"}),
        "source_dataset": source_dataset,
        "source_key": source_key,
        "headline": headline,
        "explanation": explanation,
    }


def _budget_reviews(budget: pd.DataFrame, end_month: str) -> list[dict]:
    current = budget[budget.month.eq(end_month)].copy()
    if current.empty:
        return []
    rows: list[dict] = []
    definitions = [
        ("Revenue", "revenue", True),
        ("Gross profit", "gross_profit", True),
        ("OPEX", "opex", False),
        ("EBIT", "ebit", True),
    ]
    for scope_level, entity, division, scoped in _scope_frames(current):
        scope = _scope_name(scope_level, entity, division)
        for label, key, higher_is_better in definitions:
            actual = float(scoped[key].sum())
            benchmark = float(scoped[f"{key}_budget"].sum())
            variance = actual - benchmark
            favorable = variance >= 0 if higher_is_better else variance <= 0
            if label == "OPEX":
                verb = "below" if favorable else "above"
                headline = f"{scope} OPEX was {_euro(variance)} {verb} budget."
            else:
                verb = "exceeded" if favorable else "missed"
                headline = f"{scope} {label.lower()} {verb} budget by {_euro(variance)}."
            explanation = (
                f"Actual {label.lower()} was {_euro(actual)} versus {_euro(benchmark)} budget. "
                f"The variance represents {abs(variance) / max(abs(benchmark), 1.0):.1%} of the benchmark."
            )
            rows.append(
                _review_row(
                    review_month=end_month,
                    scope_level=scope_level,
                    entity=entity,
                    division=division,
                    category="Monthly P&L vs Budget",
                    metric=label,
                    comparison="Budget",
                    unit="EUR",
                    actual_value=actual,
                    benchmark_value=benchmark,
                    variance=variance,
                    favorable=favorable,
                    source_dataset="budget_performance.csv",
                    source_key=f"{end_month}|{entity}|{division}|{key}",
                    headline=headline,
                    explanation=explanation,
                )
            )
    return rows


def _pvm_reviews(
    pvm: pd.DataFrame,
    end_month: str,
    revenue_denominator: float,
    division_revenue: dict[str, float],
) -> list[dict]:
    current = pvm[pvm.current_month.eq(end_month)].copy()
    if current.empty:
        return []
    rows: list[dict] = []
    for scope_level, division, scoped in [
        ("Group", "All", current),
        *[("Division", str(name), part) for name, part in current.groupby("division", sort=True)],
    ]:
        scope = "Group" if scope_level == "Group" else division
        denominator = revenue_denominator if scope_level == "Group" else max(abs(division_revenue.get(division, 0.0)), 1.0)
        for label, key in [("Price", "price_effect"), ("Volume", "volume_effect"), ("Mix", "mix_effect")]:
            effect = float(scoped[key].sum())
            favorable = effect >= 0
            verb = "added" if favorable else "reduced"
            headline = f"{scope} {label.lower()} {verb} year-on-year revenue by {_euro(effect)}."
            explanation = (
                f"The {label.lower()} effect explains {_euro(effect)} of the revenue bridge versus the prior year. "
                "Price, volume and mix reconcile exactly to the reported revenue change."
            )
            rows.append(
                _review_row(
                    review_month=end_month,
                    scope_level=scope_level,
                    entity="All",
                    division=division,
                    category="Commercial Drivers",
                    metric=f"{label} effect",
                    comparison="Prior year",
                    unit="EUR",
                    actual_value=effect,
                    benchmark_value=0.0,
                    variance=effect,
                    favorable=favorable,
                    source_dataset="price_volume_mix.csv",
                    source_key=f"{end_month}|{division}|{key}",
                    headline=headline,
                    explanation=explanation,
                    materiality_denominator=denominator,
                )
            )
    return rows


def _fx_reviews(cc: pd.DataFrame, end_month: str) -> list[dict]:
    current = cc[cc.month.eq(end_month)].copy()
    if current.empty:
        return []
    rows: list[dict] = []
    for scope_level, entity, division, scoped in _scope_frames(current):
        scope = _scope_name(scope_level, entity, division)
        for label, effect_key, base_key in [
            ("Revenue FX effect", "revenue_fx_effect", "constant_currency_revenue"),
            ("EBIT FX effect", "ebit_fx_effect", "constant_currency_ebit"),
        ]:
            effect = float(scoped[effect_key].sum())
            base = float(scoped[base_key].sum())
            favorable = effect >= 0
            verb = "increased" if favorable else "reduced"
            headline = f"FX translation {verb} {scope.lower()} {label.split()[0].lower()} by {_euro(effect)}."
            explanation = (
                f"Reported performance differs from the close translated at prior-year FX by {_euro(effect)}. "
                "This is a translation view and does not represent a cash remeasurement gain or loss."
            )
            rows.append(
                _review_row(
                    review_month=end_month,
                    scope_level=scope_level,
                    entity=entity,
                    division=division,
                    category="FX Translation",
                    metric=label,
                    comparison="Prior-year FX",
                    unit="EUR",
                    actual_value=effect,
                    benchmark_value=0.0,
                    variance=effect,
                    favorable=favorable,
                    source_dataset="constant_currency_analysis.csv",
                    source_key=f"{end_month}|{entity}|{division}|{effect_key}",
                    headline=headline,
                    explanation=explanation,
                    materiality_denominator=base,
                )
            )
    return rows


def _monthly_group_reviews(
    working_capital: pd.DataFrame,
    cash_flow: pd.DataFrame,
    workforce: pd.DataFrame,
    end_month: str,
) -> list[dict]:
    rows: list[dict] = []
    previous_month = str(pd.Period(end_month, freq="M") - 1)

    wc_current = working_capital[working_capital.month.eq(end_month)]
    wc_previous = working_capital[working_capital.month.eq(previous_month)]
    if not wc_current.empty and not wc_previous.empty:
        actual = float(wc_current.net_working_capital.sum())
        benchmark = float(wc_previous.net_working_capital.sum())
        variance = actual - benchmark
        favorable = variance <= 0
        verb = "released" if favorable else "absorbed"
        rows.append(
            _review_row(
                review_month=end_month,
                scope_level="Group",
                entity="All",
                division="All",
                category="Cash Conversion",
                metric="Net working capital change",
                comparison="Prior month",
                unit="EUR",
                actual_value=actual,
                benchmark_value=benchmark,
                variance=variance,
                favorable=favorable,
                source_dataset="working_capital.csv",
                source_key=f"{end_month}|net_working_capital",
                headline=f"Net working capital {verb} {_euro(variance)} month on month.",
                explanation=(
                    f"Net working capital closed at {_euro(actual)} versus {_euro(benchmark)} in {previous_month}. "
                    "The movement is based on reconciled receivables, inventory and payables."
                ),
            )
        )

    cash_current = cash_flow[cash_flow.month.eq(end_month)]
    cash_previous = cash_flow[cash_flow.month.eq(previous_month)]
    if not cash_current.empty and not cash_previous.empty:
        actual = float(cash_current.free_cash_flow.sum())
        benchmark = float(cash_previous.free_cash_flow.sum())
        variance = actual - benchmark
        favorable = variance >= 0
        verb = "increased" if favorable else "decreased"
        rows.append(
            _review_row(
                review_month=end_month,
                scope_level="Group",
                entity="All",
                division="All",
                category="Cash Conversion",
                metric="Free cash flow",
                comparison="Prior month",
                unit="EUR",
                actual_value=actual,
                benchmark_value=benchmark,
                variance=variance,
                favorable=favorable,
                source_dataset="cash_flow.csv",
                source_key=f"{end_month}|free_cash_flow",
                headline=f"Free cash flow {verb} by {_euro(variance)} month on month.",
                explanation=(
                    f"Free cash flow was {_euro(actual)} versus {_euro(benchmark)} in {previous_month}, "
                    "including operating cash generation and CAPEX."
                ),
            )
        )

    wf_current = workforce[workforce.month.eq(end_month)]
    wf_previous = workforce[workforce.month.eq(previous_month)]
    if not wf_current.empty and not wf_previous.empty:
        for label, key, higher_is_better, unit in [
            ("Revenue per FTE", "revenue_per_fte", True, "EUR/FTE"),
            ("Personnel cost", "personnel_cost", False, "EUR"),
            ("Ending FTE", "ending_fte", True, "FTE"),
        ]:
            actual = float(wf_current[key].sum())
            benchmark = float(wf_previous[key].sum())
            variance = actual - benchmark
            favorable = variance >= 0 if higher_is_better else variance <= 0
            direction = "increased" if variance >= 0 else "decreased"
            amount = _euro(variance) if unit != "FTE" else f"{abs(variance):.1f} FTE"
            rows.append(
                _review_row(
                    review_month=end_month,
                    scope_level="Group",
                    entity="All",
                    division="All",
                    category="Workforce Productivity",
                    metric=label,
                    comparison="Prior month",
                    unit=unit,
                    actual_value=actual,
                    benchmark_value=benchmark,
                    variance=variance,
                    favorable=favorable,
                    source_dataset="workforce_summary.csv",
                    source_key=f"{end_month}|{key}",
                    headline=f"{label} {direction} by {amount} month on month.",
                    explanation=(
                        f"The workforce schedule reports {actual:,.1f} versus {benchmark:,.1f} in {previous_month}. "
                        "FTE, payroll and recruitment cost roll forward from operating demand and attrition."
                    ),
                )
            )
    return rows


def _outlook_reviews(fy_bridge: pd.DataFrame, end_month: str) -> list[dict]:
    current = fy_bridge[fy_bridge.close_month.eq(end_month)].copy()
    if current.empty:
        return []
    rows: list[dict] = []
    for label, actual_key, budget_key in [
        ("FY revenue outlook", "latest_fy_revenue", "fy_budget_revenue"),
        ("FY EBIT outlook", "latest_fy_ebit", "fy_budget_ebit"),
    ]:
        actual = float(current[actual_key].sum())
        benchmark = float(current[budget_key].sum())
        variance = actual - benchmark
        favorable = variance >= 0
        verb = "above" if favorable else "below"
        rows.append(
            _review_row(
                review_month=end_month,
                scope_level="Group",
                entity="All",
                division="All",
                category="FY Outlook",
                metric=label,
                comparison="FY Budget",
                unit="EUR",
                actual_value=actual,
                benchmark_value=benchmark,
                variance=variance,
                favorable=favorable,
                source_dataset="fy_plan_bridge.csv",
                source_key=f"{end_month}|{actual_key}",
                headline=f"{label} is {_euro(variance)} {verb} budget.",
                explanation=(
                    f"Latest full-year outlook is {_euro(actual)} versus {_euro(benchmark)} budget, "
                    "combining year-to-date actuals with the latest rolling forecast."
                ),
            )
        )
    return rows


def _forecast_accuracy_review(accuracy: pd.DataFrame, end_month: str) -> list[dict]:
    current = accuracy[accuracy.month.eq(end_month) & accuracy.horizon_month.eq(1)].copy()
    if current.empty:
        return []
    mape = float(current.abs_pct_error.mean())
    target = 0.05
    variance = mape - target
    favorable = variance <= 0
    verb = "within" if favorable else "above"
    return [
        _review_row(
            review_month=end_month,
            scope_level="Group",
            entity="All",
            division="All",
            category="Forecast Discipline",
            metric="One-month revenue MAPE",
            comparison="5% tolerance",
            unit="Percent",
            actual_value=mape,
            benchmark_value=target,
            variance=variance,
            favorable=favorable,
            source_dataset="forecast_accuracy.csv",
            source_key=f"{end_month}|horizon_1|abs_pct_error",
            headline=f"One-month revenue forecast error was {mape:.1%}, {verb} the 5.0% tolerance.",
            explanation=(
                f"Mean absolute percentage error across {len(current)} entity-division observations was {mape:.1%}. "
                "The metric uses only forecasts created one month before the close."
            ),
        )
    ]


def _action_owner_and_text(row: pd.Series) -> tuple[str, str]:
    metric = str(row.metric)
    scope = _scope_name(str(row.scope_level), str(row.entity), str(row.division))
    if metric == "Revenue":
        return "Commercial Director", f"Recover the {scope} revenue shortfall through account-level pipeline conversion and pricing actions."
    if metric == "Gross profit":
        return "Operations Director", f"Launch a {scope} gross-margin recovery plan covering sourcing, production efficiency and commercial terms."
    if metric == "OPEX":
        return "Financial Controller", f"Review {scope} discretionary spend and commit an OPEX recovery plan without disrupting critical operations."
    if metric == "EBIT":
        return "CFO", f"Own the integrated {scope} EBIT recovery bridge across revenue, margin and OPEX."
    if "effect" in metric.lower() and "FX" not in metric:
        return "Commercial Director", f"Correct the adverse {scope.lower()} {metric.lower()} through portfolio, pricing and demand actions."
    if "FX" in metric:
        return "Treasury Director", f"Review natural hedges, pricing clauses and exposure concentration behind the adverse {scope.lower()} FX translation effect."
    if metric == "Net working capital change":
        return "Working Capital Lead", "Reduce cash absorption through overdue receivable, slow-moving inventory and supplier-term actions."
    if metric == "Free cash flow":
        return "Treasury Director", "Rebuild the monthly cash bridge and secure owners for the largest operating and investing cash gaps."
    if metric in {"Revenue per FTE", "Ending FTE", "Personnel cost"}:
        return "HR Director", "Align hiring, attrition coverage and workforce deployment with the latest demand and productivity outlook."
    if metric == "FY revenue outlook":
        return "FP&A Director", "Convert the full-year revenue gap into entity and division recovery commitments in the rolling forecast."
    if metric == "FY EBIT outlook":
        return "CFO", "Approve a full-year EBIT recovery plan with quantified revenue, margin, cost and cash levers."
    return "FP&A Director", "Recalibrate forecast drivers and document the largest sources of one-month forecast error."


def _management_actions(review: pd.DataFrame, end_month: str) -> pd.DataFrame:
    required = review[review.action_required].copy()
    if required.empty:
        return pd.DataFrame(columns=ACTION_COLUMNS)
    actions: list[dict] = []
    for _, row in required.sort_values(["severity", "materiality_pct"], ascending=[True, False]).iterrows():
        owner, action_text = _action_owner_and_text(row)
        priority = "P1" if row.severity == "Critical" else "P2"
        due_offset = 1 if priority == "P1" else 2
        due_month = str(pd.Period(end_month, freq="M") + due_offset)
        actions.append(
            {
                "action_id": str(row.review_id).replace("REV-", "ACT-", 1),
                "review_id": row.review_id,
                "review_month": end_month,
                "scope_level": row.scope_level,
                "entity": row.entity,
                "division": row.division,
                "priority": priority,
                "owner_role": owner,
                "due_month": due_month,
                "status": "Open",
                "action": action_text,
                "expected_outcome": f"Return {str(row.metric).lower()} to the stated benchmark or tolerance.",
                "trigger_metric": row.metric,
                "trigger_value": round(float(row.variance), 4),
                "source_dataset": row.source_dataset,
            }
        )
    return pd.DataFrame(actions, columns=ACTION_COLUMNS)


def _summary(review: pd.DataFrame, actions: pd.DataFrame, end_month: str) -> pd.DataFrame:
    group = review[review.scope_level.eq("Group")]

    def metric_value(metric: str, field: str = "variance") -> float:
        found = group[group.metric.eq(metric)]
        return float(found.iloc[0][field]) if not found.empty else 0.0

    adverse = group[~group.favorable]
    top = adverse.sort_values(["materiality_pct", "variance"], ascending=[False, True])
    return pd.DataFrame(
        [
            {
                "review_month": end_month,
                "group_insights": int(len(group)),
                "group_adverse_insights": int(len(adverse)),
                "open_actions": int(len(actions[actions.status.eq("Open")])),
                "p1_actions": int(len(actions[actions.priority.eq("P1")])),
                "revenue_vs_budget": metric_value("Revenue"),
                "ebit_vs_budget": metric_value("EBIT"),
                "fy_ebit_vs_budget": metric_value("FY EBIT outlook"),
                "free_cash_flow": metric_value("Free cash flow", "actual_value"),
                "net_working_capital_change": metric_value("Net working capital change"),
                "top_adverse_review_id": str(top.iloc[0].review_id) if not top.empty else "",
            }
        ]
    )


def build_performance_review(
    budget_performance: pd.DataFrame,
    price_volume_mix: pd.DataFrame,
    constant_currency: pd.DataFrame,
    working_capital: pd.DataFrame,
    cash_flow: pd.DataFrame,
    workforce_summary: pd.DataFrame,
    fy_plan_bridge: pd.DataFrame,
    forecast_accuracy: pd.DataFrame,
    end_month: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    current_budget = budget_performance[budget_performance.month.eq(end_month)]
    revenue_denominator = max(abs(float(current_budget.revenue.sum())), 1.0)
    division_revenue = current_budget.groupby("division").revenue.sum().abs().to_dict()
    rows = [
        *_budget_reviews(budget_performance, end_month),
        *_pvm_reviews(price_volume_mix, end_month, revenue_denominator, division_revenue),
        *_fx_reviews(constant_currency, end_month),
        *_monthly_group_reviews(working_capital, cash_flow, workforce_summary, end_month),
        *_outlook_reviews(fy_plan_bridge, end_month),
        *_forecast_accuracy_review(forecast_accuracy, end_month),
    ]
    review = pd.DataFrame(rows, columns=REVIEW_COLUMNS)
    if not review.empty:
        severity_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
        review["_severity_order"] = review.severity.map(severity_order)
        review = review.sort_values(
            ["scope_level", "favorable", "_severity_order", "materiality_pct", "category", "metric"],
            ascending=[True, True, True, False, True, True],
        ).drop(columns="_severity_order").reset_index(drop=True)
        base_required = ~review.favorable & review.severity.isin(["Critical", "High"])
        group_required = review.scope_level.eq("Group") & base_required
        scoped_required = (
            review.scope_level.isin(["Entity", "Division"])
            & base_required
            & review.unit.eq("EUR")
            & review.variance.abs().ge(revenue_denominator * 0.01)
        )
        fy_required = (
            review.scope_level.eq("Group")
            & ~review.favorable
            & review.category.eq("FY Outlook")
            & review.materiality_pct.ge(0.03)
        )
        review["action_required"] = group_required | scoped_required | fy_required
    actions = _management_actions(review, end_month)
    summary = _summary(review, actions, end_month)
    return review, actions, summary


def validate_performance_review(
    review: pd.DataFrame,
    actions: pd.DataFrame,
    summary: pd.DataFrame,
    expected_review: pd.DataFrame,
    end_month: str,
) -> dict:
    required_review = set(REVIEW_COLUMNS)
    required_actions = set(ACTION_COLUMNS)
    missing_review_columns = len(required_review - set(review.columns))
    missing_action_columns = len(required_actions - set(actions.columns))
    duplicate_review_ids = int(review.review_id.duplicated().sum()) if "review_id" in review else len(review)
    duplicate_action_ids = int(actions.action_id.duplicated().sum()) if "action_id" in actions else len(actions)
    current_month_missing = int(review.empty or not review.review_month.eq(end_month).all())

    compare_columns = ["actual_value", "benchmark_value", "variance"]
    if missing_review_columns == 0 and not expected_review.empty:
        comparison = expected_review[["review_id", *compare_columns]].merge(
            review[["review_id", *compare_columns]], on="review_id", how="outer", suffixes=("_expected", "_actual"), indicator=True
        )
        missing_rows = int(comparison._merge.ne("both").sum())
        gaps = []
        for column in compare_columns:
            gaps.append((comparison[f"{column}_expected"] - comparison[f"{column}_actual"]).abs().max())
        source_max_gap = max([float(value) for value in gaps if pd.notna(value)], default=0.0)
    else:
        missing_rows = len(expected_review)
        source_max_gap = float("inf")

    required_ids = set(review.loc[review.action_required, "review_id"]) if missing_review_columns == 0 else set()
    action_review_ids = set(actions.review_id) if missing_action_columns == 0 else set()
    required_actions_missing = len(required_ids - action_review_ids)
    action_orphans = len(action_review_ids - set(review.review_id)) if missing_review_columns == 0 else len(action_review_ids)
    invalid_action_fields = 0
    if missing_action_columns == 0 and not actions.empty:
        invalid_action_fields = int(
            (~actions.priority.isin(["P1", "P2"])
            | ~actions.status.isin(["Open", "In progress", "Closed"])
            | actions.owner_role.astype(str).str.strip().eq("")
            | actions.action.astype(str).str.strip().eq("")
            | actions.due_month.astype(str).str.strip().eq(""))
            .sum()
        )
    summary_missing = int(summary.empty or not summary.review_month.eq(end_month).all())

    checks = {
        "performance_review_missing_columns": int(missing_review_columns),
        "management_actions_missing_columns": int(missing_action_columns),
        "performance_review_duplicate_ids": duplicate_review_ids,
        "management_action_duplicate_ids": duplicate_action_ids,
        "performance_review_current_month_missing": current_month_missing,
        "performance_review_source_rows_missing": missing_rows,
        "performance_review_source_max_gap": round(source_max_gap, 4),
        "performance_review_required_actions_missing": required_actions_missing,
        "management_action_orphans": action_orphans,
        "management_action_invalid_fields": invalid_action_fields,
        "performance_review_summary_missing": summary_missing,
    }
    checks["passed"] = bool(
        all(value == 0 for key, value in checks.items() if key != "performance_review_source_max_gap")
        and checks["performance_review_source_max_gap"] <= 0.01
    )
    return checks
