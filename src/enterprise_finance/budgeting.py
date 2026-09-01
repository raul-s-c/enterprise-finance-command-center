from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


SEASONALITY = {
    1: 0.88,
    2: 0.92,
    3: 0.99,
    4: 1.01,
    5: 1.03,
    6: 1.05,
    7: 0.95,
    8: 0.84,
    9: 1.04,
    10: 1.08,
    11: 1.12,
    12: 1.18,
}

DEFAULT_STRETCH = {
    "Software": 0.015,
    "Hardware": 0.010,
    "Events": 0.005,
    "Spare Parts": 0.010,
}


@dataclass(frozen=True)
class BudgetValidation:
    max_future_source_months: int
    incomplete_budget_groups: int
    duplicate_budget_rows: int
    frozen_budget_max_gap: float
    passed: bool


def _budget_settings(config: dict) -> dict:
    settings = config.get("budget", {})
    return {
        "finalization_month": int(settings.get("finalization_month", 10)),
        "minimum_history_months": int(settings.get("minimum_history_months", 6)),
        "history_months": int(settings.get("history_months", 12)),
        "margin_improvement_pct": float(settings.get("margin_improvement_pct", 0.004)),
        "mc_improvement_pct": float(settings.get("mc_improvement_pct", 0.003)),
        "opex_leverage_pct": float(settings.get("opex_leverage_pct", 0.002)),
        "stretch": {**DEFAULT_STRETCH, **settings.get("growth_stretch", {})},
    }


def _build_one_budget(
    management: pd.DataFrame,
    config: dict,
    budget_year: int,
) -> pd.DataFrame:
    settings = _budget_settings(config)
    vintage = pd.Period(f"{budget_year - 1}-{settings['finalization_month']:02d}", freq="M")
    history = management[pd.PeriodIndex(management.month, freq="M") <= vintage].copy()
    if history.empty:
        return pd.DataFrame()

    history["period"] = pd.PeriodIndex(history.month, freq="M")
    history_start = vintage - settings["history_months"] + 1
    recent = history[history.period.ge(history_start)].copy()
    if recent.empty:
        return pd.DataFrame()

    rows: list[dict] = []
    seasonal_total = float(sum(SEASONALITY.values()))
    for (entity, division), grp in recent.groupby(["entity", "division"]):
        month_count = int(grp.month.nunique())
        if month_count < settings["minimum_history_months"]:
            continue
        revenue_monthly = float(grp.revenue.sum()) / month_count
        revenue_base_annual = revenue_monthly * 12.0
        annual_growth = float(config["divisions"].get(str(division), {}).get("annual_growth", 0.03))
        stretch = float(settings["stretch"].get(str(division), 0.0))
        target_revenue = revenue_base_annual * (1.0 + annual_growth + stretch)

        revenue_total = max(float(grp.revenue.sum()), 1.0)
        mc_pct = float(grp.marginal_contribution.sum()) / revenue_total
        gp_pct = float(grp.gross_profit.sum()) / revenue_total
        opex_pct = float(grp.opex.sum()) / revenue_total
        depreciation_pct = float(grp.depreciation.sum()) / revenue_total

        target_mc_pct = float(np.clip(mc_pct + settings["mc_improvement_pct"], -0.25, 0.95))
        target_gp_pct = float(np.clip(gp_pct + settings["margin_improvement_pct"], -0.25, 0.95))
        target_opex_pct = max(opex_pct - settings["opex_leverage_pct"], 0.0)
        target_depreciation_pct = max(depreciation_pct, 0.0)

        for month_no in range(1, 13):
            month = pd.Period(f"{budget_year}-{month_no:02d}", freq="M")
            revenue = target_revenue * SEASONALITY[month_no] / seasonal_total
            mc = revenue * target_mc_pct
            gp = revenue * target_gp_pct
            opex = revenue * target_opex_pct
            depreciation = revenue * target_depreciation_pct
            ebit = gp - opex - depreciation
            rows.append({
                "budget_year": budget_year,
                "budget_vintage": str(vintage),
                "max_source_month": str(grp.period.max()),
                "month": str(month),
                "entity": str(entity),
                "division": str(division),
                "revenue_budget": round(revenue, 2),
                "marginal_contribution_budget": round(mc, 2),
                "gross_profit_budget": round(gp, 2),
                "opex_budget": round(opex, 2),
                "depreciation_budget": round(depreciation, 2),
                "ebit_budget": round(ebit, 2),
                "revenue_growth_target": round(annual_growth + stretch, 5),
                "mc_margin_target": round(target_mc_pct, 5),
                "gross_margin_target": round(target_gp_pct, 5),
                "opex_pct_target": round(target_opex_pct, 5),
            })
    return pd.DataFrame(rows)


def build_annual_budgets(management: pd.DataFrame, config: dict, end_month: str) -> pd.DataFrame:
    """Create annual budgets only when their approval vintage has been reached.

    Rebuilding a historical budget in a later close uses the same source cutoff.
    Future actuals are therefore incapable of changing an already-approved plan.
    """
    if management.empty:
        return pd.DataFrame()
    end = pd.Period(end_month, freq="M")
    settings = _budget_settings(config)
    min_year = int(pd.PeriodIndex(management.month, freq="M").year.min()) + 1
    max_year = end.year + (1 if end.month >= settings["finalization_month"] else 0)
    frames: list[pd.DataFrame] = []
    for year in range(min_year, max_year + 1):
        vintage = pd.Period(f"{year - 1}-{settings['finalization_month']:02d}", freq="M")
        if vintage > end:
            continue
        frame = _build_one_budget(management, config, year)
        if not frame.empty:
            frames.append(frame)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _actual_by_month(management: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "revenue", "marginal_contribution", "gross_profit", "opex", "depreciation", "ebit"
    ]
    return management.groupby(["month", "entity", "division"], as_index=False)[cols].sum()


def budget_performance(
    management: pd.DataFrame,
    budgets: pd.DataFrame,
    end_month: str,
) -> pd.DataFrame:
    if budgets.empty:
        return pd.DataFrame()
    actual = _actual_by_month(management)
    end = pd.Period(end_month, freq="M")
    scope = budgets[pd.PeriodIndex(budgets.month, freq="M") <= end].copy()
    scope = scope.merge(actual, on=["month", "entity", "division"], how="left")
    for metric in ["revenue", "marginal_contribution", "gross_profit", "opex", "depreciation", "ebit"]:
        budget_col = f"{metric}_budget"
        scope[f"{metric}_variance"] = scope[metric].fillna(0.0) - scope[budget_col]
        scope[f"{metric}_variance_pct"] = scope[f"{metric}_variance"] / scope[budget_col].replace(0, np.nan)
    return scope.fillna(0.0)


def _fy_outlook_for_vintage(
    actual: pd.DataFrame,
    forecasts: pd.DataFrame,
    target_year: int,
    vintage: pd.Period,
) -> pd.DataFrame:
    base_fc = forecasts[
        forecasts.scenario.eq("Base")
        & forecasts.vintage.eq(str(vintage))
        & pd.PeriodIndex(forecasts.month, freq="M").year.eq(target_year)
    ].copy()
    actual_scope = actual[
        pd.PeriodIndex(actual.month, freq="M").year.eq(target_year)
        & (pd.PeriodIndex(actual.month, freq="M") <= vintage)
    ].copy()
    actual_agg = actual_scope.groupby(["entity", "division"], as_index=False).agg(
        actual_revenue=("revenue", "sum"),
        actual_gross_profit=("gross_profit", "sum"),
        actual_opex=("opex", "sum"),
        actual_ebit=("ebit", "sum"),
    )
    if base_fc.empty:
        fc_agg = pd.DataFrame(columns=["entity", "division", "fc_revenue", "fc_gross_profit", "fc_opex", "fc_ebit"])
    else:
        base_fc["ebit_forecast"] = base_fc.gross_profit_forecast - base_fc.opex_forecast
        fc_agg = base_fc.groupby(["entity", "division"], as_index=False).agg(
            fc_revenue=("revenue_forecast", "sum"),
            fc_gross_profit=("gross_profit_forecast", "sum"),
            fc_opex=("opex_forecast", "sum"),
            fc_ebit=("ebit_forecast", "sum"),
        )
    out = actual_agg.merge(fc_agg, on=["entity", "division"], how="outer").fillna(0.0)
    for metric in ["revenue", "gross_profit", "opex", "ebit"]:
        out[f"fy_{metric}"] = out[f"actual_{metric}"] + out[f"fc_{metric}"]
    out["forecast_vintage"] = str(vintage)
    return out


def fy_plan_bridge(
    management: pd.DataFrame,
    budgets: pd.DataFrame,
    forecasts: pd.DataFrame,
    end_month: str,
) -> pd.DataFrame:
    if budgets.empty:
        return pd.DataFrame()
    end = pd.Period(end_month, freq="M")
    target_year = end.year
    budget = budgets[budgets.budget_year.eq(target_year)].copy()
    if budget.empty:
        return pd.DataFrame()
    actual = _actual_by_month(management)
    budget_agg = budget.groupby(["entity", "division"], as_index=False).agg(
        fy_budget_revenue=("revenue_budget", "sum"),
        fy_budget_gross_profit=("gross_profit_budget", "sum"),
        fy_budget_opex=("opex_budget", "sum"),
        fy_budget_ebit=("ebit_budget", "sum"),
    )
    ytd_budget = budget[pd.PeriodIndex(budget.month, freq="M") <= end].groupby(["entity", "division"], as_index=False).agg(
        ytd_budget_revenue=("revenue_budget", "sum"),
        ytd_budget_gross_profit=("gross_profit_budget", "sum"),
        ytd_budget_opex=("opex_budget", "sum"),
        ytd_budget_ebit=("ebit_budget", "sum"),
    )
    ytd_actual = actual[
        pd.PeriodIndex(actual.month, freq="M").year.eq(target_year)
        & (pd.PeriodIndex(actual.month, freq="M") <= end)
    ].groupby(["entity", "division"], as_index=False).agg(
        ytd_actual_revenue=("revenue", "sum"),
        ytd_actual_gross_profit=("gross_profit", "sum"),
        ytd_actual_opex=("opex", "sum"),
        ytd_actual_ebit=("ebit", "sum"),
    )

    out = budget_agg.merge(ytd_budget, on=["entity", "division"], how="outer").merge(
        ytd_actual, on=["entity", "division"], how="outer"
    ).fillna(0.0)

    vintages = {
        "latest": end,
        "fc_1": end - 1,
        "fc_3": end - 3,
        "fc_6": end - 6,
    }
    for label, vintage in vintages.items():
        outlook = _fy_outlook_for_vintage(actual, forecasts, target_year, vintage)
        if outlook.empty:
            for metric in ["revenue", "gross_profit", "opex", "ebit"]:
                out[f"{label}_fy_{metric}"] = 0.0
            continue
        keep = ["entity", "division", *[f"fy_{m}" for m in ["revenue", "gross_profit", "opex", "ebit"]]]
        rename = {f"fy_{m}": f"{label}_fy_{m}" for m in ["revenue", "gross_profit", "opex", "ebit"]}
        out = out.merge(outlook[keep].rename(columns=rename), on=["entity", "division"], how="left")

    out = out.fillna(0.0)
    for metric in ["revenue", "gross_profit", "opex", "ebit"]:
        out[f"ytd_{metric}_variance"] = out[f"ytd_actual_{metric}"] - out[f"ytd_budget_{metric}"]
        out[f"latest_fy_{metric}_vs_budget"] = out[f"latest_fy_{metric}"] - out[f"fy_budget_{metric}"]
    out["budget_year"] = target_year
    out["close_month"] = end_month
    return out


def validate_budgets(
    management: pd.DataFrame,
    budgets: pd.DataFrame,
    config: dict,
    end_month: str,
) -> dict:
    if budgets.empty:
        return {
            "budget_future_source_months": 0,
            "budget_incomplete_groups": 0,
            "budget_duplicate_rows": 0,
            "budget_frozen_max_gap": 0.0,
            "passed": True,
        }
    source = pd.PeriodIndex(budgets.max_source_month, freq="M")
    vintage = pd.PeriodIndex(budgets.budget_vintage, freq="M")
    future_source_count = int((source > vintage).sum())

    coverage = budgets.groupby(["budget_year", "entity", "division"]).month.nunique()
    incomplete_groups = int((coverage != 12).sum())
    duplicate_rows = int(budgets.duplicated(["budget_year", "month", "entity", "division"]).sum())

    latest_year = int(budgets.budget_year.max())
    latest_vintage = pd.Period(str(budgets.loc[budgets.budget_year.eq(latest_year), "budget_vintage"].iloc[0]), freq="M")
    truncated = management[pd.PeriodIndex(management.month, freq="M") <= latest_vintage].copy()
    rebuilt = _build_one_budget(truncated, config, latest_year)
    original = budgets[budgets.budget_year.eq(latest_year)].copy()
    compare_cols = [
        "revenue_budget", "marginal_contribution_budget", "gross_profit_budget",
        "opex_budget", "depreciation_budget", "ebit_budget",
    ]
    if rebuilt.empty or original.empty:
        frozen_gap = 0.0
    else:
        recon = original[["month", "entity", "division", *compare_cols]].merge(
            rebuilt[["month", "entity", "division", *compare_cols]],
            on=["month", "entity", "division"],
            suffixes=("_original", "_rebuilt"),
            how="outer",
        ).fillna(0.0)
        gaps = []
        for col in compare_cols:
            gaps.append((recon[f"{col}_original"] - recon[f"{col}_rebuilt"]).abs().max())
        frozen_gap = float(max(gaps)) if gaps else 0.0

    checks = {
        "budget_future_source_months": future_source_count,
        "budget_incomplete_groups": incomplete_groups,
        "budget_duplicate_rows": duplicate_rows,
        "budget_frozen_max_gap": round(frozen_gap, 2),
    }
    checks["passed"] = (
        future_source_count == 0
        and incomplete_groups == 0
        and duplicate_rows == 0
        and frozen_gap <= 0.02
    )
    return checks
