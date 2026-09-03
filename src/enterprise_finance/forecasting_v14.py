from __future__ import annotations

import numpy as np
import pandas as pd

from .forecasting import (
    build_forecast_vintages as build_base_forecast_vintages,
    forecast_accuracy,
    latest_forecast,
    validate_forecast_scale,
)
from .workforce import _cfg as workforce_config


def _actual_workforce_state(
    operations: pd.DataFrame,
    vintage: str,
    entity: str,
    division: str,
    settings: dict,
) -> dict:
    hist = operations[
        operations.month.le(vintage)
        & operations.entity.eq(entity)
        & operations.division.eq(division)
    ].copy()
    if hist.empty or "personnel_cost_allocated" not in hist.columns:
        return {}
    end = pd.Period(vintage, freq="M")
    recent = hist[hist.month.ge(str(end - 5))]
    monthly = recent.groupby("month", as_index=False).agg(
        revenue=("revenue", "sum"),
        personnel=("personnel_cost_allocated", "sum"),
        non_people=("non_people_opex", "sum"),
        ending_fte=("workforce_ending_fte_allocated", "sum"),
        average_fte=("workforce_average_fte_allocated", "sum"),
    )
    latest = monthly[monthly.month.eq(vintage)]
    if latest.empty:
        return {}
    l = latest.iloc[0]
    current_fte = max(float(l.ending_fte), 0.01)
    avg_fte = max(float(l.average_fte), 0.01)
    monthly_loaded_cost = float(l.personnel) / avg_fte
    revenue_mean = float(monthly.revenue.mean()) if not monthly.empty else float(l.revenue)
    revenue_per_fte = revenue_mean * 12.0 / current_fte if current_fte else float(settings["revenue_per_fte"][division])
    non_people_pct = (
        float(monthly.non_people.sum()) / float(monthly.revenue.sum())
        if float(monthly.revenue.sum()) > 0.005
        else float(settings["non_people_opex_pct"][division])
    )
    return {
        "fte": current_fte,
        "monthly_loaded_cost": max(monthly_loaded_cost, 0.0),
        "revenue_per_fte": max(revenue_per_fte, 1.0),
        "non_people_pct": max(non_people_pct, 0.0),
    }


def build_forecast_vintages(
    config: dict,
    operations: pd.DataFrame,
    months: pd.PeriodIndex,
) -> pd.DataFrame:
    """Build the standard revenue/margin vintages and replace OPEX with workforce drivers."""
    base = build_base_forecast_vintages(config, operations, months)
    if base.empty or "personnel_cost_allocated" not in operations.columns:
        return base
    settings = workforce_config(config)
    out = base.copy()
    for col in [
        "personnel_cost_forecast", "non_people_opex_forecast", "workforce_fte_forecast",
        "workforce_hires_forecast", "workforce_attrition_forecast", "workforce_target_fte",
    ]:
        out[col] = 0.0

    for (vintage, entity, division, scenario), indexes in out.groupby(
        ["vintage", "entity", "division", "scenario"]
    ).groups.items():
        state = _actual_workforce_state(
            operations, str(vintage), str(entity), str(division), settings
        )
        if not state:
            continue
        current_fte = float(state["fte"])
        monthly_loaded = float(state["monthly_loaded_cost"])
        base_productivity = float(state["revenue_per_fte"])
        non_people_pct = float(state["non_people_pct"])

        ordered = sorted(indexes, key=lambda idx: int(out.at[idx, "horizon_month"]))
        for idx in ordered:
            h = int(out.at[idx, "horizon_month"])
            revenue = float(out.at[idx, "revenue_forecast"])
            productivity = base_productivity * (
                1.0 + float(settings["productivity_growth"])
            ) ** (h / 12.0)
            target = max(
                float(settings["minimum_fte_per_entity_division"]),
                revenue * 12.0 / max(productivity, 1.0),
            )
            attrition = current_fte * float(settings["annual_attrition"]) / 12.0
            after_attrition = max(current_fte - attrition, 0.0)
            hires = max(target - after_attrition, 0.0) * float(settings["hire_gap_closure"])
            ending_fte = after_attrition + hires
            avg_fte = (current_fte + ending_fte) / 2.0
            cost_per_fte_month = monthly_loaded * (
                1.0 + float(settings["salary_growth"])
            ) ** (h / 12.0)
            payroll = avg_fte * cost_per_fte_month
            recruitment = hires * float(settings["recruitment_cost_per_hire"])
            personnel = payroll + recruitment
            non_people_before_actions = revenue * non_people_pct
            opex_reduction = float(out.at[idx, "action_opex_reduction_pct"]) if "action_opex_reduction_pct" in out else 0.0
            non_people = non_people_before_actions * (1.0 - opex_reduction)

            out.at[idx, "workforce_target_fte"] = round(target, 4)
            out.at[idx, "workforce_hires_forecast"] = round(hires, 4)
            out.at[idx, "workforce_attrition_forecast"] = round(attrition, 4)
            out.at[idx, "workforce_fte_forecast"] = round(ending_fte, 4)
            out.at[idx, "personnel_cost_forecast"] = round(personnel, 2)
            out.at[idx, "non_people_opex_forecast"] = round(non_people, 2)
            out.at[idx, "opex_forecast"] = round(personnel + non_people, 2)
            if "action_opex_impact_forecast" in out:
                out.at[idx, "action_opex_impact_forecast"] = round(non_people_before_actions - non_people, 2)
                out.at[idx, "action_ebit_impact_forecast"] = round(
                    float(out.at[idx, "action_gross_profit_impact_forecast"]) + non_people_before_actions - non_people, 2
                )
            current_fte = ending_fte

    return out


def validate_workforce_forecast(forecasts: pd.DataFrame) -> dict:
    if forecasts.empty or "workforce_fte_forecast" not in forecasts.columns:
        return {
            "workforce_forecast_opex_identity_max_gap": 0.0,
            "workforce_forecast_negative_rows": 0,
            "passed": False,
        }
    gap = forecasts.opex_forecast - forecasts.personnel_cost_forecast - forecasts.non_people_opex_forecast
    negative = int((forecasts[[
        "personnel_cost_forecast", "non_people_opex_forecast", "workforce_fte_forecast",
        "workforce_hires_forecast", "workforce_attrition_forecast",
    ]].min(axis=1) < -0.001).sum())
    max_gap = float(gap.abs().max())
    return {
        "workforce_forecast_opex_identity_max_gap": round(max_gap, 2),
        "workforce_forecast_negative_rows": negative,
        "passed": max_gap <= 0.02 and negative == 0,
    }
