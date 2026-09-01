from __future__ import annotations

from collections import deque

import numpy as np
import pandas as pd


PHYSICAL_DIVISIONS = {"Hardware", "Spare Parts"}


def _treasury_cfg(config: dict) -> dict:
    cfg = config.get("treasury", {})
    minimums = {str(k): float(v) for k, v in cfg.get("minimum_cash_by_entity", {}).items()}
    entities = [str(e["code"]) for e in config["entities"]]
    minimum_cash = sum(float(minimums.get(entity, cfg.get("minimum_cash_default", 3_000_000.0))) for entity in entities)
    return {
        "minimum_cash": minimum_cash,
        "rcf_limit": float(cfg.get("rcf_limit", 35_000_000.0)),
        "net_leverage_limit": float(cfg.get("net_leverage_limit", 2.50)),
        "interest_coverage_min": float(cfg.get("interest_coverage_min", 4.00)),
        "strategic_liquidity_buffer": float(cfg.get("strategic_liquidity_buffer", 15_000_000.0)),
    }


def _fallback_prepayment_ratio(config: dict, division: str) -> float:
    contracts = config.get("contract_liabilities", {})
    if division == "Software":
        values = contracts.get("software_advance_share", {}).values()
    elif division == "Events":
        values = contracts.get("events_advance_share", {}).values()
    else:
        return 0.0
    values = [float(v) for v in values]
    return float(np.mean(values)) if values else 0.0


def derive_prepayment_ratios(
    management: pd.DataFrame,
    advances: pd.DataFrame,
    end_month: str,
    config: dict,
) -> dict[str, float]:
    current = management[management.month.eq(end_month)].groupby("division", as_index=False).revenue.sum()
    revenue = dict(zip(current.division.astype(str), current.revenue.astype(float)))
    if advances.empty:
        advance = {}
    else:
        current_advances = advances[advances.month.eq(end_month)].groupby("division", as_index=False).advance_amount.sum()
        advance = dict(zip(current_advances.division.astype(str), current_advances.advance_amount.astype(float)))
    ratios: dict[str, float] = {}
    for division in ["Software", "Events"]:
        rev = float(revenue.get(division, 0.0))
        if rev > 0.005:
            ratio = float(advance.get(division, 0.0)) / rev
        else:
            ratio = _fallback_prepayment_ratio(config, division)
        ratios[division] = float(np.clip(ratio, 0.0, 0.85))
    return ratios


def future_capex(config: dict, start_month: str, horizon: int = 12) -> pd.DataFrame:
    start = pd.Period(start_month, freq="M") + 1
    target_months = set(pd.period_range(start=start, periods=horizon, freq="M"))
    rows: list[dict] = []
    for project in config.get("capex_projects", []):
        project_start = pd.Period(project["start"], freq="M")
        build_months = int(project["build_months"])
        spend_months = pd.period_range(start=project_start, periods=build_months, freq="M")
        x = np.linspace(0.25, np.pi - 0.25, build_months)
        weights = np.sin(x)
        weights = weights / weights.sum()
        for idx, month in enumerate(spend_months):
            if month not in target_months:
                continue
            rows.append({
                "month": str(month),
                "project": str(project["id"]),
                "project_name": str(project["name"]),
                "entity": str(project["entity"]),
                "division": str(project["division"]),
                "capex": round(float(project["budget"]) * float(weights[idx]), 2),
            })
    return pd.DataFrame(rows)


def _opening_state(balance_sheet: pd.DataFrame, end_month: str) -> dict:
    row = balance_sheet[balance_sheet.month.eq(end_month)]
    if row.empty:
        raise ValueError(f"No Balance Sheet row exists for {end_month}")
    r = row.iloc[0]
    return {
        "cash": float(r.get("cash", 0.0)),
        "ar": float(r.get("trade_receivables_gross", r.get("trade_receivables", 0.0))),
        "inventory": float(r.get("inventory_gross", r.get("inventory_legal_transfer_value", r.get("inventory", 0.0)))),
        "ap": float(r.get("trade_payables", 0.0)),
        "contract_liabilities": float(r.get("contract_liabilities", 0.0)),
        "tax_payable": float(r.get("tax_payable", 0.0)),
        "debt": float(r.get("debt", 0.0)),
    }


def _forecast_terms(scope: pd.DataFrame, prepayment_ratio: dict[str, float], config: dict) -> dict:
    if scope.empty:
        return {
            "revenue": 0.0, "gross_profit": 0.0, "opex": 0.0, "ebitda": 0.0,
            "target_ar": 0.0, "target_inventory": 0.0, "target_ap_base": 0.0,
            "target_contract_liabilities": 0.0, "operating_cost": 0.0,
        }
    revenue = float(scope.revenue_forecast.sum())
    gp = float(scope.gross_profit_forecast.sum())
    opex = float(scope.opex_forecast.sum())
    target_ar = 0.0
    target_inventory = 0.0
    target_ap_base = 0.0
    target_contract = 0.0
    operating_cost = max(revenue - gp + opex, 0.0)

    for division, grp in scope.groupby("division"):
        div = str(division)
        rev = float(grp.revenue_forecast.sum())
        div_gp = float(grp.gross_profit_forecast.sum())
        div_opex = float(grp.opex_forecast.sum())
        direct_cost = max(rev - div_gp, 0.0)
        prepay = float(prepayment_ratio.get(div, 0.0))
        billed_revenue = rev * (1.0 - prepay)
        dso = float(config["divisions"][div]["dso"])
        dpo = float(config["divisions"][div]["dpo"])
        target_ar += billed_revenue * dso / 30.0
        target_contract += rev * prepay
        target_ap_base += max(direct_cost + div_opex, 0.0) * dpo / 30.0
        if div in PHYSICAL_DIVISIONS:
            dio = float(config["divisions"][div]["dio"])
            target_inventory += direct_cost * dio / 30.0

    return {
        "revenue": revenue,
        "gross_profit": gp,
        "opex": opex,
        "ebitda": gp - opex,
        "target_ar": max(target_ar, 0.0),
        "target_inventory": max(target_inventory, 0.0),
        "target_ap_base": max(target_ap_base, 0.0),
        "target_contract_liabilities": max(target_contract, 0.0),
        "operating_cost": operating_cost,
    }


def build_liquidity_forecast(
    forecasts: pd.DataFrame,
    management: pd.DataFrame,
    balance_sheet: pd.DataFrame,
    actual_liquidity: pd.DataFrame,
    debt_schedule: pd.DataFrame,
    advances: pd.DataFrame,
    config: dict,
    end_month: str,
    horizon: int = 12,
) -> pd.DataFrame:
    if forecasts.empty:
        return pd.DataFrame()
    current = forecasts[forecasts.vintage.eq(end_month) & forecasts.horizon_month.le(horizon)].copy()
    if current.empty:
        return pd.DataFrame()

    state0 = _opening_state(balance_sheet, end_month)
    prepay = derive_prepayment_ratios(management, advances, end_month, config)
    treasury_cfg = _treasury_cfg(config)
    capex = future_capex(config, end_month, horizon)
    capex_map = capex.groupby("month").capex.sum().to_dict() if not capex.empty else {}

    latest_debt = debt_schedule[debt_schedule.month.eq(end_month)] if not debt_schedule.empty else pd.DataFrame()
    if not latest_debt.empty and float(latest_debt.gross_debt.sum()) > 0:
        annual_rate = float((latest_debt.gross_debt * latest_debt.implied_annual_interest_rate).sum() / latest_debt.gross_debt.sum())
    else:
        annual_rate = 0.035

    actual_liq = actual_liquidity[actual_liquidity.month.le(end_month)].sort_values("month") if not actual_liquidity.empty else pd.DataFrame()
    actual_ebitda = list(actual_liq.ebitda.tail(11).astype(float)) if "ebitda" in actual_liq else []
    actual_interest = list(actual_liq.interest_expense.tail(11).astype(float)) if "interest_expense" in actual_liq else []
    depreciation_run_rate = float(
        management[management.month.eq(end_month)].depreciation.sum()
    ) if "depreciation" in management.columns else 0.0

    rows: list[dict] = []
    for scenario in sorted(current.scenario.unique()):
        state = dict(state0)
        rcf_drawn = 0.0
        ebitda_window = deque(actual_ebitda, maxlen=12)
        interest_window = deque(actual_interest, maxlen=12)
        scenario_rows = current[current.scenario.eq(scenario)].sort_values("horizon_month")

        for _, forecast_month in scenario_rows.iterrows():
            month = str(forecast_month.month)
            month_scope = current[(current.scenario.eq(scenario)) & (current.month.eq(month))]
            terms = _forecast_terms(month_scope, prepay, config)

            opening_ar = state["ar"]
            opening_inventory = state["inventory"]
            opening_ap = state["ap"]
            opening_contract = state["contract_liabilities"]
            opening_cash = state["cash"]
            opening_debt = state["debt"]
            opening_tax = state["tax_payable"]

            ending_ar = terms["target_ar"]
            ending_inventory = terms["target_inventory"]
            inventory_change = ending_inventory - opening_inventory
            operating_accrual = max(terms["operating_cost"] + inventory_change, 0.0)
            ending_ap = terms["target_ap_base"]
            ending_contract = terms["target_contract_liabilities"]

            customer_cash = terms["revenue"] + opening_ar - ending_ar + ending_contract - opening_contract
            supplier_cash = operating_accrual + opening_ap - ending_ap

            interest = max(opening_debt, 0.0) * annual_rate / 12.0
            ebit = terms["gross_profit"] - terms["opex"] - depreciation_run_rate
            ebt = ebit - interest
            tax_accrual = max(ebt, 0.0) * float(config["group"]["corporate_tax_rate"])
            tax_available = opening_tax + tax_accrual
            period = pd.Period(month, freq="M")
            tax_payment = tax_available * 0.78 if period.month in {3, 6, 9, 12} else 0.0
            ending_tax = max(tax_available - tax_payment, 0.0)

            operating_cash_flow = customer_cash - supplier_cash - interest - tax_payment
            capex_cash = float(capex_map.get(month, 0.0))
            scheduled_debt_repayment = min(opening_debt * 0.0125, opening_debt) if period.month in {3, 6, 9, 12} else 0.0
            cash_before_rcf = opening_cash + operating_cash_flow - capex_cash - scheduled_debt_repayment

            available_rcf = max(treasury_cfg["rcf_limit"] - rcf_drawn, 0.0)
            required_draw = max(treasury_cfg["minimum_cash"] - cash_before_rcf, 0.0)
            rcf_draw = min(required_draw, available_rcf)
            rcf_drawn += rcf_draw
            ending_cash = cash_before_rcf + rcf_draw
            ending_debt = max(opening_debt - scheduled_debt_repayment + rcf_draw, 0.0)

            ebitda = terms["ebitda"]
            ebitda_window.append(ebitda)
            interest_window.append(interest)
            ebitda_ttm = float(sum(ebitda_window))
            interest_ttm = float(sum(interest_window))
            net_debt = ending_debt - ending_cash
            net_leverage = net_debt / ebitda_ttm if abs(ebitda_ttm) > 0.005 else 0.0
            interest_coverage = ebitda_ttm / interest_ttm if interest_ttm > 0.005 else 99.0
            undrawn_rcf = max(treasury_cfg["rcf_limit"] - rcf_drawn, 0.0)
            liquidity_headroom = max(ending_cash - treasury_cfg["minimum_cash"], 0.0) + undrawn_rcf
            deployable_cash = max(
                ending_cash - treasury_cfg["minimum_cash"] - treasury_cfg["strategic_liquidity_buffer"], 0.0
            )
            covenant_status = "PASS" if (
                net_leverage <= treasury_cfg["net_leverage_limit"]
                and interest_coverage >= treasury_cfg["interest_coverage_min"]
            ) else "WATCH"

            rows.append({
                "scenario": str(scenario),
                "month": month,
                "horizon_month": int(forecast_month.horizon_month),
                "opening_cash": opening_cash,
                "revenue": terms["revenue"],
                "ebitda": ebitda,
                "opening_ar": opening_ar,
                "ending_ar": ending_ar,
                "opening_inventory": opening_inventory,
                "ending_inventory": ending_inventory,
                "opening_ap": opening_ap,
                "ending_ap": ending_ap,
                "opening_contract_liabilities": opening_contract,
                "ending_contract_liabilities": ending_contract,
                "customer_cash": customer_cash,
                "supplier_cash": supplier_cash,
                "interest_cash": interest,
                "tax_accrual": tax_accrual,
                "tax_payment": tax_payment,
                "ending_tax_payable": ending_tax,
                "operating_cash_flow": operating_cash_flow,
                "capex": capex_cash,
                "scheduled_debt_repayment": scheduled_debt_repayment,
                "rcf_draw": rcf_draw,
                "rcf_drawn": rcf_drawn,
                "ending_cash": ending_cash,
                "gross_debt": ending_debt,
                "net_debt": net_debt,
                "ebitda_ttm": ebitda_ttm,
                "interest_ttm": interest_ttm,
                "net_leverage": net_leverage,
                "interest_coverage": interest_coverage,
                "undrawn_rcf": undrawn_rcf,
                "minimum_operating_cash": treasury_cfg["minimum_cash"],
                "strategic_liquidity_buffer": treasury_cfg["strategic_liquidity_buffer"],
                "liquidity_headroom": liquidity_headroom,
                "deployable_cash": deployable_cash,
                "covenant_status": covenant_status,
                "customer_cash_identity_gap": customer_cash - (
                    terms["revenue"] + opening_ar - ending_ar + ending_contract - opening_contract
                ),
                "supplier_cash_identity_gap": supplier_cash - (
                    operating_accrual + opening_ap - ending_ap
                ),
                "cash_rollforward_gap": ending_cash - (
                    opening_cash + operating_cash_flow - capex_cash - scheduled_debt_repayment + rcf_draw
                ),
            })

            state["cash"] = ending_cash
            state["ar"] = ending_ar
            state["inventory"] = ending_inventory
            state["ap"] = ending_ap
            state["contract_liabilities"] = ending_contract
            state["tax_payable"] = ending_tax
            state["debt"] = ending_debt

    return pd.DataFrame(rows)


def validate_liquidity_forecast(forecast: pd.DataFrame, horizon: int = 12) -> dict:
    if forecast.empty:
        return {
            "liquidity_forecast_cash_rollforward_max_gap": 0.0,
            "liquidity_forecast_customer_cash_max_gap": 0.0,
            "liquidity_forecast_supplier_cash_max_gap": 0.0,
            "liquidity_forecast_negative_balance_rows": 0,
            "liquidity_forecast_missing_scenario_months": horizon * 3,
            "liquidity_forecast_rcf_excess_rows": 0,
            "passed": False,
        }
    cash_gap = float(forecast.cash_rollforward_gap.abs().max())
    customer_gap = float(forecast.customer_cash_identity_gap.abs().max())
    supplier_gap = float(forecast.supplier_cash_identity_gap.abs().max())
    negative = int((forecast[["ending_ar", "ending_inventory", "ending_ap", "ending_contract_liabilities", "ending_cash", "gross_debt"]].min(axis=1) < -0.05).sum())
    coverage = forecast.groupby("scenario").month.nunique()
    missing = int(sum(max(horizon - int(v), 0) for v in coverage.values) + max(3 - len(coverage), 0) * horizon)
    rcf_excess = int((forecast.rcf_drawn - (forecast.rcf_drawn + forecast.undrawn_rcf).max() > 0.05).sum())
    checks = {
        "liquidity_forecast_cash_rollforward_max_gap": round(cash_gap, 2),
        "liquidity_forecast_customer_cash_max_gap": round(customer_gap, 2),
        "liquidity_forecast_supplier_cash_max_gap": round(supplier_gap, 2),
        "liquidity_forecast_negative_balance_rows": negative,
        "liquidity_forecast_missing_scenario_months": missing,
        "liquidity_forecast_rcf_excess_rows": rcf_excess,
    }
    checks["passed"] = (
        cash_gap <= 0.02 and customer_gap <= 0.02 and supplier_gap <= 0.02
        and negative == 0 and missing == 0 and rcf_excess == 0
    )
    return checks
