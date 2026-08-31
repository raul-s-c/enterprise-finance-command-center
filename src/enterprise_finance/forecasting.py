from __future__ import annotations

import numpy as np
import pandas as pd


SCENARIOS = {
    "Base": {"growth_delta": 0.0, "margin_delta": 0.0},
    "Upside": {"growth_delta": 0.035, "margin_delta": 0.012},
    "Downside": {"growth_delta": -0.055, "margin_delta": -0.018},
}


def _forecast_one_vintage(operations: pd.DataFrame, vintage: pd.Period, horizon: int, config: dict, prior_forecasts: list[dict]) -> list[dict]:
    history = operations[operations["month"] <= str(vintage)].copy()
    if history.empty:
        return []
    recent = history[history["month"] >= str(vintage - 5)]
    grouped = recent.groupby(["entity", "division"], as_index=False).agg(
        revenue=("revenue", "mean"), gross_profit=("gross_profit", "mean"),
        marginal_contribution=("marginal_contribution", "mean"), opex=("opex", "mean"),
    )
    prior = pd.DataFrame(prior_forecasts)
    bias_map: dict[tuple[str, str], float] = {}
    if not prior.empty:
        realized = prior[prior["month"] <= str(vintage)].merge(
            operations.groupby(["month", "entity", "division"], as_index=False).revenue.sum().rename(columns={"revenue": "actual_revenue"}),
            on=["month", "entity", "division"], how="inner",
        )
        realized = realized[(realized["scenario"] == "Base") & realized.actual_revenue.gt(0)]
        if not realized.empty:
            realized["bias"] = realized.revenue_forecast / realized.actual_revenue - 1.0
            for key, grp in realized.groupby(["entity", "division"]):
                bias_map[key] = float(np.clip(grp.tail(12).bias.median(), -0.12, 0.12))

    seasonality = {1: .88, 2: .92, 3: .99, 4: 1.01, 5: 1.03, 6: 1.05, 7: .95, 8: .84, 9: 1.04, 10: 1.08, 11: 1.12, 12: 1.18}
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
                revenue = float(base.revenue) * base_growth * scenario_growth * (seasonality[target.month] / seasonality[vintage.month]) * correction
                gp_pct = float(base.gross_profit) / max(float(base.revenue), 1.0) + float(assumptions["margin_delta"])
                mc_pct = float(base.marginal_contribution) / max(float(base.revenue), 1.0) + float(assumptions["margin_delta"]) * 0.7
                opex_pct = float(base.opex) / max(float(base.revenue), 1.0)
                rows.append({
                    "vintage": str(vintage), "month": str(target), "horizon_month": h,
                    "entity": entity, "division": division, "scenario": scenario,
                    "revenue_forecast": round(revenue, 2), "gross_profit_forecast": round(revenue * gp_pct, 2),
                    "marginal_contribution_forecast": round(revenue * mc_pct, 2), "opex_forecast": round(revenue * opex_pct, 2),
                    "bias_correction": round(correction, 5),
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
