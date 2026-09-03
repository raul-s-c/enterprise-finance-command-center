from __future__ import annotations

import numpy as np
import pandas as pd

from .action_execution import incremental_intervention_effects


SCENARIOS = {
    "Base": {"growth_delta": 0.0, "margin_delta": 0.0},
    "Upside": {"growth_delta": 0.035, "margin_delta": 0.012},
    "Downside": {"growth_delta": -0.055, "margin_delta": -0.018},
}

SEASONALITY = {1:.88,2:.92,3:.99,4:1.01,5:1.03,6:1.05,7:.95,8:.84,9:1.04,10:1.08,11:1.12,12:1.18}


def _monthly_baseline(operations: pd.DataFrame, vintage: pd.Period) -> pd.DataFrame:
    """Build a six-month entity/division baseline from monthly totals, not transaction means."""
    history = operations[operations["month"] <= str(vintage)].copy()
    if history.empty:
        return pd.DataFrame()
    start = vintage - 5
    recent = history[history["month"] >= str(start)].copy()
    monthly = recent.groupby(["month", "entity", "division"], as_index=False).agg(
        revenue=("revenue", "sum"),
        gross_profit=("gross_profit", "sum"),
        marginal_contribution=("marginal_contribution", "sum"),
        opex=("opex", "sum"),
    )

    keys = history[["entity", "division"]].drop_duplicates()
    month_frame = pd.DataFrame({"month": pd.period_range(start, vintage, freq="M").astype(str)})
    grid = keys.merge(month_frame, how="cross").merge(monthly, on=["month", "entity", "division"], how="left").fillna(0.0)
    grid["seasonality"] = pd.PeriodIndex(grid.month, freq="M").month.map(SEASONALITY)
    grid["neutral_revenue"] = grid.revenue / grid.seasonality

    grouped = grid.groupby(["entity", "division"], as_index=False).agg(
        neutral_revenue=("neutral_revenue", "mean"),
        revenue_sum=("revenue", "sum"),
        gross_profit_sum=("gross_profit", "sum"),
        marginal_contribution_sum=("marginal_contribution", "sum"),
        opex_sum=("opex", "sum"),
        observed_months=("month", "nunique"),
    )
    denom = grouped.revenue_sum.replace(0, np.nan)
    grouped["gross_margin"] = (grouped.gross_profit_sum / denom).fillna(0.0)
    grouped["mc_margin"] = (grouped.marginal_contribution_sum / denom).fillna(0.0)
    grouped["opex_pct"] = (grouped.opex_sum / denom).fillna(0.0)
    return grouped


def _forecast_one_vintage(operations: pd.DataFrame, vintage: pd.Period, horizon: int, config: dict, prior_forecasts: list[dict]) -> list[dict]:
    history = operations[operations["month"] <= str(vintage)].copy()
    if history.empty:
        return []
    grouped = _monthly_baseline(operations, vintage)
    if grouped.empty:
        return []

    prior = pd.DataFrame(prior_forecasts)
    bias_map: dict[tuple[str, str], float] = {}
    if not prior.empty:
        actual_monthly = operations.groupby(["month", "entity", "division"], as_index=False).revenue.sum().rename(columns={"revenue": "actual_revenue"})
        realized = prior[prior["month"] <= str(vintage)].merge(actual_monthly, on=["month", "entity", "division"], how="inner")
        realized = realized[(realized["scenario"] == "Base") & realized.actual_revenue.gt(0)]
        if not realized.empty:
            realized["bias"] = realized.revenue_forecast / realized.actual_revenue - 1.0
            for key, grp in realized.groupby(["entity", "division"]):
                bias_map[key] = float(np.clip(grp.tail(12).bias.median(), -0.12, 0.12))

    rows: list[dict] = []
    for h in range(1, horizon + 1):
        target = vintage + h
        for _, base in grouped.iterrows():
            entity, division = str(base.entity), str(base.division)
            annual_growth = float(config["divisions"][division]["annual_growth"])
            base_growth = (1 + annual_growth) ** (h / 12.0)
            correction = 1.0 / (1.0 + bias_map.get((entity, division), 0.0))
            for scenario, assumptions in SCENARIOS.items():
                scenario_growth = (1 + float(assumptions["growth_delta"])) ** (h / 12.0)
                revenue = float(base.neutral_revenue) * SEASONALITY[target.month] * base_growth * scenario_growth * correction
                gp_pct = float(base.gross_margin) + float(assumptions["margin_delta"])
                mc_pct = float(base.mc_margin) + float(assumptions["margin_delta"]) * 0.7
                opex_pct = float(base.opex_pct)
                action_effect = incremental_intervention_effects(config, str(vintage), str(target), entity, division)
                revenue_before_actions = revenue
                gross_profit_before_actions = revenue * gp_pct
                mc_before_actions = revenue * mc_pct
                opex_before_actions = revenue * opex_pct
                revenue *= (1.0 + float(action_effect["price_uplift_pct"])) * (1.0 + float(action_effect["volume_uplift_pct"]))
                direct_cost = max(revenue_before_actions - gross_profit_before_actions, 0.0)
                variable_cost = max(revenue_before_actions - mc_before_actions, 0.0)
                gross_profit = revenue - direct_cost * (revenue / max(revenue_before_actions, 1.0)) * (1.0 - float(action_effect["variable_cost_reduction_pct"]))
                marginal_contribution = revenue - variable_cost * (revenue / max(revenue_before_actions, 1.0)) * (1.0 - float(action_effect["variable_cost_reduction_pct"]))
                opex = revenue * opex_pct * (1.0 - float(action_effect["opex_reduction_pct"]))
                rows.append({
                    "vintage": str(vintage), "month": str(target), "horizon_month": h,
                    "entity": entity, "division": division, "scenario": scenario,
                    "revenue_forecast": round(revenue, 2),
                    "gross_profit_forecast": round(gross_profit, 2),
                    "marginal_contribution_forecast": round(marginal_contribution, 2),
                    "opex_forecast": round(opex, 2),
                    "bias_correction": round(correction, 5),
                    "active_action_count": int(action_effect["active_action_count"]),
                    "action_opex_reduction_pct": round(float(action_effect["opex_reduction_pct"]), 6),
                    "action_revenue_impact_forecast": round(revenue - revenue_before_actions, 2),
                    "action_gross_profit_impact_forecast": round(gross_profit - gross_profit_before_actions, 2),
                    "action_opex_impact_forecast": round(opex_before_actions - opex, 2),
                    "action_ebit_impact_forecast": round((gross_profit - gross_profit_before_actions) + (opex_before_actions - opex), 2),
                })
    return rows


def build_forecast_vintages(config: dict, operations: pd.DataFrame, months: pd.PeriodIndex) -> pd.DataFrame:
    horizon = int(config["group"]["forecast_months"])
    rows: list[dict] = []
    for idx, vintage in enumerate(months):
        if idx < 5:
            continue
        rows.extend(_forecast_one_vintage(operations, vintage, horizon, config, rows))
    return pd.DataFrame(rows)


def forecast_accuracy(forecasts: pd.DataFrame, operations: pd.DataFrame, end_month: str) -> pd.DataFrame:
    if forecasts.empty:
        return pd.DataFrame(columns=["vintage", "month", "horizon_month", "entity", "division", "actual_revenue", "revenue_forecast", "error", "abs_pct_error", "bias_pct"])
    actual = operations.groupby(["month", "entity", "division"], as_index=False).revenue.sum().rename(columns={"revenue": "actual_revenue"})
    base = forecasts[(forecasts.scenario == "Base") & (forecasts.month <= end_month)].merge(actual, on=["month", "entity", "division"], how="left")
    base = base[base.actual_revenue.notna()].copy()
    base["error"] = base.revenue_forecast - base.actual_revenue
    base["abs_pct_error"] = (base.error.abs() / base.actual_revenue.replace(0, np.nan)).fillna(0.0)
    base["bias_pct"] = (base.error / base.actual_revenue.replace(0, np.nan)).fillna(0.0)
    return base[["vintage", "month", "horizon_month", "entity", "division", "actual_revenue", "revenue_forecast", "error", "abs_pct_error", "bias_pct"]]


def latest_forecast(forecasts: pd.DataFrame, end_month: str) -> pd.DataFrame:
    return forecasts[forecasts.vintage.eq(end_month)].copy()


def validate_forecast_scale(forecasts: pd.DataFrame, operations: pd.DataFrame, end_month: str) -> dict:
    """Catch unit/grain errors that can still pass ordinary no-lookahead checks."""
    if forecasts.empty:
        return {"forecast_next_month_scale_ratio": 0.0, "forecast_scale_out_of_range": 1, "passed": False}
    end = pd.Period(end_month, freq="M")
    latest = forecasts[(forecasts.vintage.eq(end_month)) & forecasts.scenario.eq("Base")]
    next_month = latest[latest.horizon_month.eq(1)]
    actual_monthly = operations.groupby("month", as_index=False).revenue.sum()
    trailing = actual_monthly[(actual_monthly.month >= str(end - 5)) & (actual_monthly.month <= end_month)]
    baseline = float(trailing.revenue.mean()) if not trailing.empty else 0.0
    next_revenue = float(next_month.revenue_forecast.sum()) if not next_month.empty else 0.0
    ratio = next_revenue / baseline if baseline else 0.0
    out_of_range = int(not (0.55 <= ratio <= 1.65))
    return {
        "forecast_next_month_scale_ratio": round(ratio, 4),
        "forecast_scale_out_of_range": out_of_range,
        "passed": out_of_range == 0,
    }
