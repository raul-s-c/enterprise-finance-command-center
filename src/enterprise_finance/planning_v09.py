from __future__ import annotations

import pandas as pd

from .budgeting_v09 import actual_monthly


def _remaining_plan(actual: pd.DataFrame, forecasts: pd.DataFrame, year: int, vintage: pd.Period) -> pd.DataFrame:
    remaining = max(12 - vintage.month, 0) if vintage.year == year else (12 if vintage.year < year else 0)
    base = forecasts[
        forecasts.scenario.eq("Base")
        & forecasts.vintage.eq(str(vintage))
        & (pd.PeriodIndex(forecasts.month, freq="M").year == year)
    ].copy()
    if base.empty:
        fc = pd.DataFrame(columns=["entity", "division", "fc_revenue", "fc_gross_profit", "fc_opex"])
    else:
        fc = base.groupby(["entity", "division"], as_index=False).agg(
            fc_revenue=("revenue_forecast", "sum"),
            fc_gross_profit=("gross_profit_forecast", "sum"),
            fc_opex=("opex_forecast", "sum"),
        )

    hist = actual[pd.PeriodIndex(actual.month, freq="M") <= vintage].copy()
    hist["period"] = pd.PeriodIndex(hist.month, freq="M")
    recent = hist[hist.period.ge(vintage - 2)]
    if recent.empty:
        runrate = pd.DataFrame(columns=["entity", "division", "rr_revenue", "rr_gross_profit", "rr_opex", "rr_depreciation", "rr_ebit"])
    else:
        runrate = recent.groupby(["entity", "division"], as_index=False).agg(
            rr_revenue=("revenue", "mean"),
            rr_gross_profit=("gross_profit", "mean"),
            rr_opex=("opex", "mean"),
            rr_depreciation=("depreciation", "mean"),
            rr_ebit=("ebit", "mean"),
        )

    groups = pd.concat([fc[["entity", "division"]], runrate[["entity", "division"]]], ignore_index=True).drop_duplicates()
    out = groups.merge(fc, on=["entity", "division"], how="left").merge(runrate, on=["entity", "division"], how="left")
    for col in ["rr_revenue", "rr_gross_profit", "rr_opex", "rr_depreciation", "rr_ebit"]:
        out[col] = out[col].fillna(0.0)

    has_commercial_fc = out.fc_revenue.notna() | out.fc_gross_profit.notna() | out.fc_opex.notna()
    out["fc_revenue"] = out.fc_revenue.where(has_commercial_fc, out.rr_revenue * remaining).fillna(0.0)
    out["fc_gross_profit"] = out.fc_gross_profit.where(has_commercial_fc, out.rr_gross_profit * remaining).fillna(0.0)
    out["fc_opex"] = out.fc_opex.where(has_commercial_fc, out.rr_opex * remaining).fillna(0.0)
    out["fc_depreciation"] = out.rr_depreciation * remaining
    out["fc_ebit"] = out["fc_gross_profit"] - out["fc_opex"] - out["fc_depreciation"]
    out.loc[~has_commercial_fc, "fc_ebit"] = out.loc[~has_commercial_fc, "rr_ebit"] * remaining
    return out[["entity", "division", "fc_revenue", "fc_gross_profit", "fc_opex", "fc_depreciation", "fc_ebit"]]


def fy_outlook(management: pd.DataFrame, forecasts: pd.DataFrame, year: int, vintage: pd.Period) -> pd.DataFrame:
    actual = actual_monthly(management)
    scope = actual[
        (pd.PeriodIndex(actual.month, freq="M").year == year)
        & (pd.PeriodIndex(actual.month, freq="M") <= vintage)
    ]
    act = scope.groupby(["entity", "division"], as_index=False).agg(
        actual_revenue=("revenue", "sum"),
        actual_gross_profit=("gross_profit", "sum"),
        actual_opex=("opex", "sum"),
        actual_depreciation=("depreciation", "sum"),
        actual_ebit=("ebit", "sum"),
    )
    rem = _remaining_plan(actual, forecasts, year, vintage)
    out = act.merge(rem, on=["entity", "division"], how="outer").fillna(0.0)
    for metric in ["revenue", "gross_profit", "opex", "depreciation", "ebit"]:
        out[f"fy_{metric}"] = out[f"actual_{metric}"] + out[f"fc_{metric}"]
    out["forecast_vintage"] = str(vintage)
    return out


def fy_plan_bridge(management: pd.DataFrame, budgets: pd.DataFrame, forecasts: pd.DataFrame, end_month: str) -> pd.DataFrame:
    if budgets.empty:
        return pd.DataFrame()
    end = pd.Period(end_month, freq="M")
    year = end.year
    budget = budgets[budgets.budget_year.eq(year)].copy()
    if budget.empty:
        return pd.DataFrame()
    actual = actual_monthly(management)

    out = budget.groupby(["entity", "division"], as_index=False).agg(
        fy_budget_revenue=("revenue_budget", "sum"),
        fy_budget_gross_profit=("gross_profit_budget", "sum"),
        fy_budget_opex=("opex_budget", "sum"),
        fy_budget_depreciation=("depreciation_budget", "sum"),
        fy_budget_ebit=("ebit_budget", "sum"),
    )
    ytd_budget = budget[pd.PeriodIndex(budget.month, freq="M") <= end].groupby(["entity", "division"], as_index=False).agg(
        ytd_budget_revenue=("revenue_budget", "sum"),
        ytd_budget_gross_profit=("gross_profit_budget", "sum"),
        ytd_budget_opex=("opex_budget", "sum"),
        ytd_budget_depreciation=("depreciation_budget", "sum"),
        ytd_budget_ebit=("ebit_budget", "sum"),
    )
    ytd_actual = actual[
        (pd.PeriodIndex(actual.month, freq="M").year == year)
        & (pd.PeriodIndex(actual.month, freq="M") <= end)
    ].groupby(["entity", "division"], as_index=False).agg(
        ytd_actual_revenue=("revenue", "sum"),
        ytd_actual_gross_profit=("gross_profit", "sum"),
        ytd_actual_opex=("opex", "sum"),
        ytd_actual_depreciation=("depreciation", "sum"),
        ytd_actual_ebit=("ebit", "sum"),
    )
    out = out.merge(ytd_budget, on=["entity", "division"], how="outer").merge(ytd_actual, on=["entity", "division"], how="outer").fillna(0.0)

    for label, vintage in {"latest": end, "fc_1": end - 1, "fc_3": end - 3, "fc_6": end - 6}.items():
        f = fy_outlook(management, forecasts, year, vintage)
        metrics = ["revenue", "gross_profit", "opex", "depreciation", "ebit"]
        rename = {f"fy_{m}": f"{label}_fy_{m}" for m in metrics}
        out = out.merge(f[["entity", "division", *rename.keys()]].rename(columns=rename), on=["entity", "division"], how="left")

    out = out.fillna(0.0)
    for metric in ["revenue", "gross_profit", "opex", "depreciation", "ebit"]:
        out[f"ytd_{metric}_variance"] = out[f"ytd_actual_{metric}"] - out[f"ytd_budget_{metric}"]
        out[f"latest_fy_{metric}_vs_budget"] = out[f"latest_fy_{metric}"] - out[f"fy_budget_{metric}"]
    out["budget_year"] = year
    out["close_month"] = end_month
    return out
