from __future__ import annotations

import numpy as np
import pandas as pd


SEASONALITY = {1:.88,2:.92,3:.99,4:1.01,5:1.03,6:1.05,7:.95,8:.84,9:1.04,10:1.08,11:1.12,12:1.18}
DEFAULT_STRETCH = {"Software":.015,"Hardware":.010,"Events":.005,"Spare Parts":.010}


def _settings(config: dict) -> dict:
    s = config.get("budget", {})
    return {
        "finalization_month": int(s.get("finalization_month", 10)),
        "history_months": int(s.get("history_months", 12)),
        "minimum_history_months": int(s.get("minimum_history_months", 6)),
        "margin_improvement_pct": float(s.get("margin_improvement_pct", .004)),
        "mc_improvement_pct": float(s.get("mc_improvement_pct", .003)),
        "opex_leverage_pct": float(s.get("opex_leverage_pct", .002)),
        "factory_absorption_improvement_pct": float(s.get("factory_absorption_improvement_pct", .10)),
        "cost_center_efficiency_pct": float(s.get("cost_center_efficiency_pct", .01)),
        "stretch": {**DEFAULT_STRETCH, **s.get("growth_stretch", {})},
    }


def build_one_budget(management: pd.DataFrame, config: dict, budget_year: int) -> pd.DataFrame:
    s = _settings(config)
    vintage = pd.Period(f"{budget_year-1}-{s['finalization_month']:02d}", freq="M")
    hist = management[pd.PeriodIndex(management.month, freq="M") <= vintage].copy()
    if hist.empty:
        return pd.DataFrame()
    hist["period"] = pd.PeriodIndex(hist.month, freq="M")
    recent = hist[hist.period.ge(vintage - s["history_months"] + 1)].copy()
    if recent.empty:
        return pd.DataFrame()

    rows: list[dict] = []
    seasonal_total = float(sum(SEASONALITY.values()))
    for (entity, division), grp in recent.groupby(["entity", "division"]):
        months = int(grp.month.nunique())
        if months < s["minimum_history_months"]:
            continue
        total_rev = float(grp.revenue.sum())
        max_source = str(grp.period.max())

        if abs(total_rev) < 1.0:
            avg_mc = float(grp.marginal_contribution.sum()) / months
            avg_gp = float(grp.gross_profit.sum()) / months
            avg_opex = float(grp.opex.sum()) / months
            avg_dep = float(grp.depreciation.sum()) / months
            planned_gp = avg_gp * (1.0 - s["factory_absorption_improvement_pct"] if avg_gp < 0 else 1.0)
            planned_opex = avg_opex * (1.0 - s["cost_center_efficiency_pct"])
            for m in range(1, 13):
                rows.append({
                    "budget_year": budget_year, "budget_vintage": str(vintage), "max_source_month": max_source,
                    "month": f"{budget_year}-{m:02d}", "entity": str(entity), "division": str(division),
                    "budget_model": "Cost center run-rate", "revenue_budget": 0.0,
                    "marginal_contribution_budget": round(avg_mc,2), "gross_profit_budget": round(planned_gp,2),
                    "opex_budget": round(planned_opex,2), "depreciation_budget": round(avg_dep,2),
                    "ebit_budget": round(planned_gp-planned_opex-avg_dep,2), "revenue_growth_target": 0.0,
                    "mc_margin_target": 0.0, "gross_margin_target": 0.0, "opex_pct_target": 0.0,
                })
            continue

        annual_growth = float(config["divisions"].get(str(division), {}).get("annual_growth", .03))
        stretch = float(s["stretch"].get(str(division), 0.0))
        annual_target = total_rev / months * 12.0 * (1.0 + annual_growth + stretch)
        mc_pct = float(grp.marginal_contribution.sum()) / total_rev
        gp_pct = float(grp.gross_profit.sum()) / total_rev
        opex_pct = float(grp.opex.sum()) / total_rev
        dep_pct = float(grp.depreciation.sum()) / total_rev
        target_mc = float(np.clip(mc_pct + s["mc_improvement_pct"], -.25, .95))
        target_gp = float(np.clip(gp_pct + s["margin_improvement_pct"], -.25, .95))
        target_opex = max(opex_pct - s["opex_leverage_pct"], 0.0)
        target_dep = max(dep_pct, 0.0)
        for m in range(1, 13):
            revenue = annual_target * SEASONALITY[m] / seasonal_total
            mc = revenue * target_mc
            gp = revenue * target_gp
            opex = revenue * target_opex
            dep = revenue * target_dep
            rows.append({
                "budget_year": budget_year, "budget_vintage": str(vintage), "max_source_month": max_source,
                "month": f"{budget_year}-{m:02d}", "entity": str(entity), "division": str(division),
                "budget_model": "Driver-based commercial", "revenue_budget": round(revenue,2),
                "marginal_contribution_budget": round(mc,2), "gross_profit_budget": round(gp,2),
                "opex_budget": round(opex,2), "depreciation_budget": round(dep,2),
                "ebit_budget": round(gp-opex-dep,2), "revenue_growth_target": round(annual_growth+stretch,5),
                "mc_margin_target": round(target_mc,5), "gross_margin_target": round(target_gp,5),
                "opex_pct_target": round(target_opex,5),
            })
    return pd.DataFrame(rows)


def build_annual_budgets(management: pd.DataFrame, config: dict, end_month: str) -> pd.DataFrame:
    if management.empty:
        return pd.DataFrame()
    end = pd.Period(end_month, freq="M")
    s = _settings(config)
    first_year = int(pd.PeriodIndex(management.month, freq="M").year.min()) + 1
    last_year = end.year + (1 if end.month >= s["finalization_month"] else 0)
    frames = []
    for year in range(first_year, last_year + 1):
        vintage = pd.Period(f"{year-1}-{s['finalization_month']:02d}", freq="M")
        if vintage <= end:
            frame = build_one_budget(management, config, year)
            if not frame.empty:
                frames.append(frame)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def actual_monthly(management: pd.DataFrame) -> pd.DataFrame:
    cols = ["revenue","marginal_contribution","gross_profit","opex","depreciation","ebit"]
    return management.groupby(["month","entity","division"], as_index=False)[cols].sum()


def budget_performance(management: pd.DataFrame, budgets: pd.DataFrame, end_month: str) -> pd.DataFrame:
    if budgets.empty:
        return pd.DataFrame()
    end = pd.Period(end_month, freq="M")
    actual = actual_monthly(management)
    out = budgets[pd.PeriodIndex(budgets.month, freq="M") <= end].merge(actual, on=["month","entity","division"], how="left")
    for metric in ["revenue","marginal_contribution","gross_profit","opex","depreciation","ebit"]:
        out[metric] = out[metric].fillna(0.0)
        out[f"{metric}_variance"] = out[metric] - out[f"{metric}_budget"]
        out[f"{metric}_variance_pct"] = out[f"{metric}_variance"] / out[f"{metric}_budget"].replace(0, np.nan)
    return out.fillna(0.0)


def _forecast_remaining(actual: pd.DataFrame, forecasts: pd.DataFrame, year: int, vintage: pd.Period) -> pd.DataFrame:
    base = forecasts[(forecasts.scenario=="Base") & (forecasts.vintage==str(vintage)) & (pd.PeriodIndex(forecasts.month,freq="M").year==year)].copy()
    if base.empty:
        fc = pd.DataFrame(columns=["entity","division","fc_revenue","fc_gross_profit","fc_opex","fc_ebit"])
    else:
        base["ebit_forecast"] = base.gross_profit_forecast - base.opex_forecast
        fc = base.groupby(["entity","division"],as_index=False).agg(
            fc_revenue=("revenue_forecast","sum"), fc_gross_profit=("gross_profit_forecast","sum"),
            fc_opex=("opex_forecast","sum"), fc_ebit=("ebit_forecast","sum"))

    # Factory/cost-center combinations are absent from the commercial forecast.
    # Forecast their remaining P&L using only the last three months observable at the vintage.
    remaining = max(12-vintage.month,0) if vintage.year==year else (12 if vintage.year<year else 0)
    hist = actual[pd.PeriodIndex(actual.month,freq="M") <= vintage].copy()
    hist["period"] = pd.PeriodIndex(hist.month,freq="M")
    recent = hist[hist.period >= vintage-2]
    if remaining and not recent.empty:
        fallback = recent.groupby(["entity","division"],as_index=False).agg(
            revenue=("revenue","mean"), gross_profit=("gross_profit","mean"), opex=("opex","mean"), ebit=("ebit","mean"))
        for m in ["revenue","gross_profit","opex","ebit"]:
            fallback[f"fc_{m}_fallback"] = fallback[m] * remaining
        fallback = fallback[["entity","division","fc_revenue_fallback","fc_gross_profit_fallback","fc_opex_fallback","fc_ebit_fallback"]]
    else:
        fallback = pd.DataFrame(columns=["entity","division","fc_revenue_fallback","fc_gross_profit_fallback","fc_opex_fallback","fc_ebit_fallback"])

    groups = pd.concat([fc[["entity","division"]], fallback[["entity","division"]]], ignore_index=True).drop_duplicates()
    out = groups.merge(fc,on=["entity","division"],how="left").merge(fallback,on=["entity","division"],how="left")
    for m in ["revenue","gross_profit","opex","ebit"]:
        out[f"fc_{m}"] = out[f"fc_{m}"].fillna(out[f"fc_{m}_fallback"]).fillna(0.0)
    return out[["entity","division","fc_revenue","fc_gross_profit","fc_opex","fc_ebit"]]


def fy_outlook(actual: pd.DataFrame, forecasts: pd.DataFrame, year: int, vintage: pd.Period) -> pd.DataFrame:
    act = actual[(pd.PeriodIndex(actual.month,freq="M").year==year) & (pd.PeriodIndex(actual.month,freq="M")<=vintage)]
    act = act.groupby(["entity","division"],as_index=False).agg(
        actual_revenue=("revenue","sum"), actual_gross_profit=("gross_profit","sum"),
        actual_opex=("opex","sum"), actual_ebit=("ebit","sum"))
    rem = _forecast_remaining(actual, forecasts, year, vintage)
    out = act.merge(rem,on=["entity","division"],how="outer").fillna(0.0)
    for m in ["revenue","gross_profit","opex","ebit"]:
        out[f"fy_{m}"] = out[f"actual_{m}"] + out[f"fc_{m}"]
    out["forecast_vintage"] = str(vintage)
    return out


def fy_plan_bridge(management: pd.DataFrame, budgets: pd.DataFrame, forecasts: pd.DataFrame, end_month: str) -> pd.DataFrame:
    if budgets.empty:
        return pd.DataFrame()
    end = pd.Period(end_month,freq="M")
    year = end.year
    budget = budgets[budgets.budget_year==year]
    if budget.empty:
        return pd.DataFrame()
    actual = actual_monthly(management)
    out = budget.groupby(["entity","division"],as_index=False).agg(
        fy_budget_revenue=("revenue_budget","sum"), fy_budget_gross_profit=("gross_profit_budget","sum"),
        fy_budget_opex=("opex_budget","sum"), fy_budget_ebit=("ebit_budget","sum"))
    ytd_b = budget[pd.PeriodIndex(budget.month,freq="M")<=end].groupby(["entity","division"],as_index=False).agg(
        ytd_budget_revenue=("revenue_budget","sum"), ytd_budget_gross_profit=("gross_profit_budget","sum"),
        ytd_budget_opex=("opex_budget","sum"), ytd_budget_ebit=("ebit_budget","sum"))
    ytd_a = actual[(pd.PeriodIndex(actual.month,freq="M").year==year)&(pd.PeriodIndex(actual.month,freq="M")<=end)].groupby(["entity","division"],as_index=False).agg(
        ytd_actual_revenue=("revenue","sum"), ytd_actual_gross_profit=("gross_profit","sum"),
        ytd_actual_opex=("opex","sum"), ytd_actual_ebit=("ebit","sum"))
    out = out.merge(ytd_b,on=["entity","division"],how="outer").merge(ytd_a,on=["entity","division"],how="outer").fillna(0.0)
    for label,vintage in {"latest":end,"fc_1":end-1,"fc_3":end-3,"fc_6":end-6}.items():
        f = fy_outlook(actual, forecasts, year, vintage)
        ren = {f"fy_{m}":f"{label}_fy_{m}" for m in ["revenue","gross_profit","opex","ebit"]}
        out = out.merge(f[["entity","division",*ren]].rename(columns=ren),on=["entity","division"],how="left")
    out = out.fillna(0.0)
    for m in ["revenue","gross_profit","opex","ebit"]:
        out[f"ytd_{m}_variance"] = out[f"ytd_actual_{m}"] - out[f"ytd_budget_{m}"]
        out[f"latest_fy_{m}_vs_budget"] = out[f"latest_fy_{m}"] - out[f"fy_budget_{m}"]
    out["budget_year"] = year
    out["close_month"] = end_month
    return out


def validate_budgets(management: pd.DataFrame, budgets: pd.DataFrame, config: dict) -> dict:
    if budgets.empty:
        return {"budget_future_source_months":0,"budget_incomplete_groups":0,"budget_duplicate_rows":0,"budget_frozen_max_gap":0.0,"passed":True}
    future = int((pd.PeriodIndex(budgets.max_source_month,freq="M") > pd.PeriodIndex(budgets.budget_vintage,freq="M")).sum())
    incomplete = int((budgets.groupby(["budget_year","entity","division"]).month.nunique()!=12).sum())
    duplicates = int(budgets.duplicated(["budget_year","month","entity","division"]).sum())
    latest_year = int(budgets.budget_year.max())
    vintage = pd.Period(budgets.loc[budgets.budget_year==latest_year,"budget_vintage"].iloc[0],freq="M")
    truncated = management[pd.PeriodIndex(management.month,freq="M")<=vintage]
    rebuilt = build_one_budget(truncated,config,latest_year)
    orig = budgets[budgets.budget_year==latest_year]
    cols=["revenue_budget","marginal_contribution_budget","gross_profit_budget","opex_budget","depreciation_budget","ebit_budget"]
    recon=orig[["month","entity","division",*cols]].merge(rebuilt[["month","entity","division",*cols]],on=["month","entity","division"],how="outer",suffixes=("_o","_r")).fillna(0.0)
    gap=max(float((recon[f"{c}_o"]-recon[f"{c}_r"]).abs().max()) for c in cols) if len(recon) else 0.0
    checks={"budget_future_source_months":future,"budget_incomplete_groups":incomplete,"budget_duplicate_rows":duplicates,"budget_frozen_max_gap":round(gap,2)}
    checks["passed"]=future==0 and incomplete==0 and duplicates==0 and gap<=.02
    return checks
