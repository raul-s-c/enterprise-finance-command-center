from __future__ import annotations

import pandas as pd


SHOCKS = {
    "Price +1%": ("price", 0.01, "+1.0%"),
    "Volume +1%": ("volume", 0.01, "+1.0%"),
    "Industrial production -1%": ("industrial", -0.01, "-1.0%"),
    "Inflation +100 bps": ("inflation", 0.01, "+100 bps"),
    "Wage inflation +100 bps": ("wages", 0.01, "+100 bps"),
    "Energy index +10%": ("energy", 0.10, "+10.0%"),
    "Policy rate +100 bps": ("policy_rate", 0.01, "+100 bps"),
    "EUR strengthening +5%": ("fx", 1.0 / 1.05 - 1.0, "+5.0% EUR"),
}

PASS_THROUGH = {"Software": 0.55, "Hardware": 0.35, "Events": 0.30, "Spare Parts": 0.40}
INDUSTRIAL_ELASTICITY = {"Software": 0.25, "Hardware": 1.00, "Events": 0.65, "Spare Parts": 0.55}
ENERGY_ELASTICITY = {"Software": 0.01, "Hardware": 0.25, "Events": 0.03, "Spare Parts": 0.08}
CASH_CONVERSION = {"Software": 0.88, "Hardware": 0.82, "Events": 0.90, "Spare Parts": 0.84, "Corporate": 1.00}


def _money(value: float) -> float:
    return round(float(value), 2)


def _scope_row(scope: pd.Series, shock_name: str, driver: str, shock: float, display: str, tax_rate: float) -> dict:
    entity, division = str(scope.entity), str(scope.division)
    revenue = float(scope.revenue_forecast)
    gross_profit = float(scope.gross_profit_forecast)
    contribution = float(scope.marginal_contribution_forecast)
    personnel = float(scope.personnel_cost_forecast)
    non_people = float(scope.non_people_opex_forecast)
    direct_cost = max(revenue - gross_profit, 0.0)
    gp_impact = opex_benefit = revenue_impact = interest_expense_impact = 0.0
    methodology = ""

    if driver == "price":
        revenue_impact = revenue * shock
        gp_impact = revenue_impact
        methodology = "Revenue shock with unchanged unit costs."
    elif driver in {"volume", "industrial"}:
        demand_shock = shock if driver == "volume" else shock * INDUSTRIAL_ELASTICITY[division]
        revenue_impact = revenue * demand_shock
        gp_impact = revenue_impact * (gross_profit / revenue if revenue else 0.0)
        ebit_impact = revenue_impact * (contribution / revenue if revenue else 0.0)
        opex_benefit = ebit_impact - gp_impact
        methodology = "Demand elasticity applied to Revenue and marginal contribution."
    elif driver == "inflation":
        revenue_impact = revenue * shock * PASS_THROUGH[division]
        gp_impact = revenue_impact - direct_cost * shock
        opex_benefit = -non_people * shock
        methodology = "Division price pass-through less direct-cost and non-people OPEX inflation."
    elif driver == "wages":
        opex_benefit = -personnel * shock
        methodology = "Fully loaded personnel cost exposed to the annual wage shock."
    elif driver == "energy":
        gp_impact = -direct_cost * shock * ENERGY_ELASTICITY[division]
        methodology = "Direct cost exposed through division energy elasticity."
    elif driver == "fx":
        if entity not in {"DE01", "ES01"}:
            revenue_impact = revenue * shock
            gp_impact = gross_profit * shock
            opex_benefit = -float(scope.opex_forecast) * shock
        methodology = "Translation-only shock for non-EUR entities; no transaction-cash claim."

    ebit_impact = gp_impact + opex_benefit
    if driver == "policy_rate":
        return {}
    cash_impact = 0.0 if driver == "fx" else ebit_impact * (1.0 - tax_rate) * CASH_CONVERSION[division]
    return {
        "shock": shock_name, "driver": driver, "shock_display": display,
        "entity": entity, "division": division,
        "base_revenue": _money(revenue), "base_gross_profit": _money(gross_profit),
        "base_opex": _money(float(scope.opex_forecast)),
        "revenue_impact": _money(revenue_impact), "gross_profit_impact": _money(gp_impact),
        "opex_benefit": _money(opex_benefit), "ebit_impact": _money(ebit_impact),
        "interest_expense_impact": _money(interest_expense_impact),
        "net_income_impact": _money((ebit_impact - interest_expense_impact) * (1.0 - tax_rate)),
        "ending_cash_impact": _money(cash_impact), "net_debt_impact": _money(-cash_impact),
        "methodology": methodology,
    }


def build_financial_sensitivities(
    forecasts: pd.DataFrame, liquidity: pd.DataFrame, debt: pd.DataFrame, config: dict, end_month: str
) -> tuple[pd.DataFrame, pd.DataFrame]:
    current = forecasts[
        forecasts.vintage.eq(end_month) & forecasts.scenario.eq("Base") & forecasts.horizon_month.le(12)
    ].copy()
    if current.empty:
        return pd.DataFrame(), pd.DataFrame()
    required = ["personnel_cost_forecast", "non_people_opex_forecast"]
    for column in required:
        if column not in current:
            current[column] = 0.0
    scopes = current.groupby(["entity", "division"], as_index=False).agg(
        revenue_forecast=("revenue_forecast", "sum"),
        gross_profit_forecast=("gross_profit_forecast", "sum"),
        marginal_contribution_forecast=("marginal_contribution_forecast", "sum"),
        opex_forecast=("opex_forecast", "sum"),
        personnel_cost_forecast=("personnel_cost_forecast", "sum"),
        non_people_opex_forecast=("non_people_opex_forecast", "sum"),
    )
    tax_rate = float(config["group"]["corporate_tax_rate"])
    rows: list[dict] = []
    for shock_name, (driver, shock, display) in SHOCKS.items():
        if driver == "policy_rate":
            continue
        for _, scope in scopes.iterrows():
            rows.append(_scope_row(scope, shock_name, driver, shock, display, tax_rate))

    latest_debt = debt[debt.month.eq(end_month)].copy() if not debt.empty else pd.DataFrame()
    for entity, gross_debt in latest_debt.groupby("entity").gross_debt.sum().items():
        expense = float(gross_debt) * SHOCKS["Policy rate +100 bps"][1]
        cash = -expense * (1.0 - tax_rate)
        rows.append({
            "shock": "Policy rate +100 bps", "driver": "policy_rate", "shock_display": "+100 bps",
            "entity": str(entity), "division": "Corporate", "base_revenue": 0.0,
            "base_gross_profit": 0.0, "base_opex": 0.0, "revenue_impact": 0.0,
            "gross_profit_impact": 0.0, "opex_benefit": 0.0, "ebit_impact": 0.0,
            "interest_expense_impact": _money(expense),
            "net_income_impact": _money(-expense * (1.0 - tax_rate)),
            "ending_cash_impact": _money(cash), "net_debt_impact": _money(-cash),
            "methodology": "Closing gross debt exposed to a 100 bps annual interest-rate increase.",
        })
    detail = pd.DataFrame(rows)

    monetary = [
        "base_revenue", "base_gross_profit", "base_opex", "revenue_impact", "gross_profit_impact",
        "opex_benefit", "ebit_impact", "interest_expense_impact", "net_income_impact",
        "ending_cash_impact", "net_debt_impact",
    ]
    summary = detail.groupby(["shock", "driver", "shock_display"], as_index=False)[monetary].sum()
    summary[monetary] = summary[monetary].round(2)
    base_liq = liquidity[
        liquidity.scenario.eq("Base") & liquidity.horizon_month.eq(liquidity.horizon_month.max())
    ]
    if base_liq.empty:
        base_net_debt = base_net_leverage = base_interest_coverage = base_ebitda = base_interest = 0.0
    else:
        row = base_liq.iloc[-1]
        base_net_debt = float(row.net_debt)
        base_net_leverage = float(row.net_leverage)
        base_interest_coverage = float(row.interest_coverage)
        base_ebitda = float(row.ebitda_ttm)
        base_interest = float(row.interest_ttm)
    summary["net_leverage_delta"] = summary.apply(
        lambda r: round(
            (base_net_debt + float(r.net_debt_impact))
            / max(base_ebitda + float(r.ebit_impact), 1.0)
            - base_net_leverage,
            4,
        ),
        axis=1,
    )
    summary["interest_coverage_delta"] = summary.apply(
        lambda r: round(
            (base_ebitda + float(r.ebit_impact)) / max(base_interest + float(r.interest_expense_impact), 1.0)
            - base_interest_coverage, 4
        ), axis=1
    )
    summary["base_net_leverage"] = round(base_net_leverage, 4)
    summary["base_interest_coverage"] = round(base_interest_coverage, 4)
    summary["portfolio_additive"] = False
    summary["interpretation"] = "Standalone controlled sensitivity; do not sum across shocks."
    return detail, summary


def validate_macro_and_sensitivities(
    macro: pd.DataFrame, lineage: pd.DataFrame, detail: pd.DataFrame, summary: pd.DataFrame
) -> dict:
    expected_lineage = len(macro) * 8
    monetary = [
        "base_revenue", "base_gross_profit", "base_opex", "revenue_impact", "gross_profit_impact",
        "opex_benefit", "ebit_impact", "interest_expense_impact", "net_income_impact",
        "ending_cash_impact", "net_debt_impact",
    ]
    grouped = detail.groupby("shock", as_index=False)[monetary].sum() if not detail.empty else pd.DataFrame()
    reconciled = summary.merge(grouped, on="shock", suffixes=("_summary", "_detail")) if not summary.empty else pd.DataFrame()
    reconciliation_gap = 0.0
    if not reconciled.empty:
        reconciliation_gap = max(
            float((reconciled[f"{column}_summary"] - reconciled[f"{column}_detail"]).abs().max())
            for column in monetary
        )
    ebit_gap = float((detail.ebit_impact - detail.gross_profit_impact - detail.opex_benefit).abs().max()) if not detail.empty else 1.0
    net_debt_gap = float((detail.net_debt_impact + detail.ending_cash_impact).abs().max()) if not detail.empty else 1.0
    directions = {
        "Price +1%": 1, "Volume +1%": 1, "Industrial production -1%": -1,
        "Inflation +100 bps": -1, "Wage inflation +100 bps": -1,
        "Energy index +10%": -1, "Policy rate +100 bps": 0, "EUR strengthening +5%": -1,
    }
    summary_ebit = summary.set_index("shock").ebit_impact.to_dict() if not summary.empty else {}
    direction_errors = sum(
        int(sign > 0 and summary_ebit.get(shock, 0.0) <= 0)
        + int(sign < 0 and summary_ebit.get(shock, 0.0) >= 0)
        for shock, sign in directions.items() if sign
    )
    if not summary.empty:
        policy_net_income = float(
            summary.loc[summary.shock.eq("Policy rate +100 bps"), "net_income_impact"].sum()
        )
        direction_errors += int(policy_net_income >= 0)
    checks = {
        "macro_lineage_missing_rows": max(expected_lineage - len(lineage), 0),
        "macro_lineage_duplicate_rows": int(lineage.duplicated(["close_month", "observation_month", "driver"]).sum()) if not lineage.empty else expected_lineage,
        "macro_lineage_invalid_status_rows": int((~lineage.status.isin(["Official", "Fallback"])).sum()) if not lineage.empty else expected_lineage,
        "sensitivity_missing_shocks": int(len(SHOCKS) - summary.shock.nunique()) if not summary.empty else len(SHOCKS),
        "sensitivity_duplicate_detail_rows": int(detail.duplicated(["shock", "entity", "division"]).sum()) if not detail.empty else 1,
        "sensitivity_ebit_identity_max_gap": round(ebit_gap, 2),
        "sensitivity_net_debt_identity_max_gap": round(net_debt_gap, 2),
        "sensitivity_detail_summary_max_gap": round(reconciliation_gap, 2),
        "sensitivity_direction_errors": int(direction_errors),
        "sensitivity_additive_summary_rows": int(summary.portfolio_additive.astype(bool).sum()) if not summary.empty else 1,
    }
    count_checks = [
        "macro_lineage_missing_rows", "macro_lineage_duplicate_rows", "macro_lineage_invalid_status_rows",
        "sensitivity_missing_shocks", "sensitivity_duplicate_detail_rows", "sensitivity_direction_errors",
        "sensitivity_additive_summary_rows",
    ]
    checks["passed"] = bool(
        all(int(checks[key]) == 0 for key in count_checks)
        and checks["sensitivity_ebit_identity_max_gap"] <= 0.02
        and checks["sensitivity_net_debt_identity_max_gap"] <= 0.02
        and checks["sensitivity_detail_summary_max_gap"] <= 0.02
    )
    return checks
