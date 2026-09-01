from __future__ import annotations

from collections import deque
import pandas as pd

from .liquidity_forecast import PHYSICAL_DIVISIONS, _opening_state, _treasury_cfg, derive_prepayment_ratios, future_capex


def _money(value: float) -> float:
    return round(float(value), 2)


def _terms(scope: pd.DataFrame, prepay: dict[str, float], config: dict) -> dict:
    """Build one consolidated monthly driver block from cent-precise divisions.

    Revenue, Gross Profit, personnel cost, non-people OPEX, Working Capital targets
    and external supplier cost are all accumulated from the exact same divisional
    monetary blocks. This prevents a global-sum versus sum-of-rounded-divisions
    difference from leaking into the linked Balance Sheet through retained earnings.
    """
    revenue = gp = personnel = non_people = 0.0
    target_ar = target_inventory = target_ap = target_contract = external_cost = 0.0
    for division, grp in scope.groupby("division"):
        div = str(division)
        rev = _money(grp.revenue_forecast.sum())
        div_gp = _money(grp.gross_profit_forecast.sum())
        div_personnel = _money(grp.personnel_cost_forecast.sum()) if "personnel_cost_forecast" in grp.columns else 0.0
        raw_div_opex = _money(grp.opex_forecast.sum())
        div_non_people = _money(grp.non_people_opex_forecast.sum()) if "non_people_opex_forecast" in grp.columns else _money(max(raw_div_opex - div_personnel, 0.0))

        revenue = _money(revenue + rev)
        gp = _money(gp + div_gp)
        personnel = _money(personnel + div_personnel)
        non_people = _money(non_people + div_non_people)

        direct = _money(max(rev - div_gp, 0.0))
        ext = _money(direct + max(div_non_people, 0.0))
        external_cost = _money(external_cost + ext)
        ratio = float(prepay.get(div, 0.0))
        target_ar = _money(target_ar + rev * (1.0 - ratio) * float(config["divisions"][div]["dso"]) / 30.0)
        target_contract = _money(target_contract + rev * ratio)
        target_ap = _money(target_ap + ext * float(config["divisions"][div]["dpo"]) / 30.0)
        if div in PHYSICAL_DIVISIONS:
            target_inventory = _money(target_inventory + direct * float(config["divisions"][div]["dio"]) / 30.0)

    opex = _money(personnel + non_people)
    return {
        "revenue": revenue,
        "gross_profit": gp,
        "opex": opex,
        "personnel": personnel,
        "non_people": non_people,
        "ebitda": _money(gp - opex),
        "target_ar": _money(max(target_ar, 0.0)),
        "target_inventory": _money(max(target_inventory, 0.0)),
        "target_ap": _money(max(target_ap, 0.0)),
        "target_contract": _money(max(target_contract, 0.0)),
        "external_cost": _money(max(external_cost, 0.0)),
    }


def build_liquidity_forecast(forecasts, management, balance_sheet, actual_liquidity, debt_schedule, advances, config, end_month, horizon=12):
    current = forecasts[forecasts.vintage.eq(end_month) & forecasts.horizon_month.le(horizon)].copy()
    if current.empty:
        return pd.DataFrame()
    raw_state = _opening_state(balance_sheet, end_month)
    state0 = {key: _money(value) for key, value in raw_state.items()}
    prepay = derive_prepayment_ratios(management, advances, end_month, config)
    cfg = _treasury_cfg(config)
    rcf_limit = _money(cfg["rcf_limit"])
    minimum_cash = _money(cfg["minimum_cash"])
    strategic_buffer = _money(cfg["strategic_liquidity_buffer"])
    capex = future_capex(config, end_month, horizon)
    capex_map = {str(k): _money(v) for k, v in (capex.groupby("month").capex.sum().to_dict() if not capex.empty else {}).items()}
    latest_debt = debt_schedule[debt_schedule.month.eq(end_month)] if not debt_schedule.empty else pd.DataFrame()
    annual_rate = float((latest_debt.gross_debt * latest_debt.implied_annual_interest_rate).sum() / latest_debt.gross_debt.sum()) if not latest_debt.empty and float(latest_debt.gross_debt.sum()) > 0 else 0.035
    hist = actual_liquidity[actual_liquidity.month.le(end_month)].sort_values("month") if not actual_liquidity.empty else pd.DataFrame()
    actual_ebitda = list(hist.ebitda.tail(11).astype(float)) if "ebitda" in hist else []
    actual_interest = list(hist.interest_expense.tail(11).astype(float)) if "interest_expense" in hist else []
    dep = _money(management[management.month.eq(end_month)].depreciation.sum()) if "depreciation" in management.columns else 0.0
    rows = []

    for scenario in sorted(current.scenario.unique()):
        state = dict(state0)
        rcf_drawn = 0.0
        ebitda_window = deque(actual_ebitda, maxlen=12)
        interest_window = deque(actual_interest, maxlen=12)
        months = current[current.scenario.eq(scenario)][["month", "horizon_month"]].drop_duplicates().sort_values("horizon_month")
        for mr in months.itertuples(index=False):
            month = str(mr.month)
            scope = current[current.scenario.eq(scenario) & current.month.eq(month)]
            t = _terms(scope, prepay, config)

            opening_cash = _money(state["cash"])
            opening_ar = _money(state["ar"])
            opening_inv = _money(state["inventory"])
            opening_ap = _money(state["ap"])
            opening_contract = _money(state["contract_liabilities"])
            opening_tax = _money(state["tax_payable"])
            opening_debt = _money(state["debt"])

            ending_ar = _money(t["target_ar"])
            ending_inv = _money(t["target_inventory"])
            ending_ap = _money(t["target_ap"])
            ending_contract = _money(t["target_contract"])
            inventory_change = _money(ending_inv - opening_inv)
            external_accrual = _money(max(float(t["external_cost"]) + inventory_change, 0.0))
            customer_cash = _money(float(t["revenue"]) + opening_ar - ending_ar + ending_contract - opening_contract)
            supplier_cash = _money(external_accrual + opening_ap - ending_ap)
            payroll_cash = _money(t["personnel"])
            interest = _money(max(opening_debt, 0.0) * annual_rate / 12.0)
            ebit = _money(float(t["gross_profit"]) - float(t["opex"]) - dep)
            ebt = _money(ebit - interest)
            tax_accrual = _money(max(ebt, 0.0) * float(config["group"]["corporate_tax_rate"]))
            tax_available = _money(opening_tax + tax_accrual)
            period = pd.Period(month, freq="M")
            tax_payment = _money(tax_available * 0.78) if period.month in {3, 6, 9, 12} else 0.0
            ending_tax = _money(max(tax_available - tax_payment, 0.0))

            ocf = _money(customer_cash - supplier_cash - payroll_cash - interest - tax_payment)
            capex_cash = _money(capex_map.get(month, 0.0))
            repay = _money(min(opening_debt * 0.0125, opening_debt)) if period.month in {3, 6, 9, 12} else 0.0
            pre_rcf = _money(opening_cash + ocf - capex_cash - repay)
            available_rcf = _money(max(rcf_limit - rcf_drawn, 0.0))
            draw = _money(min(max(minimum_cash - pre_rcf, 0.0), available_rcf))
            rcf_drawn = _money(rcf_drawn + draw)
            ending_cash = _money(pre_rcf + draw)
            ending_debt = _money(max(opening_debt - repay + draw, 0.0))

            ebitda = _money(t["ebitda"])
            ebitda_window.append(ebitda)
            interest_window.append(interest)
            ebitda_ttm = _money(sum(ebitda_window))
            interest_ttm = _money(sum(interest_window))
            net_debt = _money(ending_debt - ending_cash)
            leverage = net_debt / ebitda_ttm if abs(ebitda_ttm) > 0.005 else 0.0
            coverage = ebitda_ttm / interest_ttm if interest_ttm > 0.005 else 99.0
            undrawn = _money(max(rcf_limit - rcf_drawn, 0.0))
            headroom = _money(max(ending_cash - minimum_cash, 0.0) + undrawn)
            deployable = _money(max(ending_cash - minimum_cash - strategic_buffer, 0.0))
            shortfall = _money(max(minimum_cash - ending_cash, 0.0))
            covenant = "PASS" if leverage <= float(cfg["net_leverage_limit"]) and coverage >= float(cfg["interest_coverage_min"]) else "WATCH"

            rows.append({
                "scenario": str(scenario), "month": month, "horizon_month": int(mr.horizon_month),
                "opening_cash": opening_cash, "revenue": _money(t["revenue"]), "ebitda": ebitda,
                "personnel_cost": payroll_cash, "non_people_opex": _money(t["non_people"]),
                "opening_ar": opening_ar, "ending_ar": ending_ar,
                "opening_inventory": opening_inv, "ending_inventory": ending_inv,
                "opening_ap": opening_ap, "ending_ap": ending_ap,
                "opening_contract_liabilities": opening_contract, "ending_contract_liabilities": ending_contract,
                "customer_cash": customer_cash, "supplier_cash": supplier_cash, "payroll_cash": payroll_cash,
                "interest_cash": interest, "tax_accrual": tax_accrual, "tax_payment": tax_payment,
                "ending_tax_payable": ending_tax, "operating_cash_flow": ocf, "capex": capex_cash,
                "scheduled_debt_repayment": repay, "rcf_draw": draw, "rcf_drawn": rcf_drawn,
                "rcf_limit": rcf_limit, "undrawn_rcf": undrawn, "ending_cash": ending_cash,
                "gross_debt": ending_debt, "net_debt": net_debt, "ebitda_ttm": ebitda_ttm,
                "interest_ttm": interest_ttm, "net_leverage": leverage, "interest_coverage": coverage,
                "minimum_operating_cash": minimum_cash, "strategic_liquidity_buffer": strategic_buffer,
                "liquidity_headroom": headroom, "liquidity_shortfall": shortfall,
                "deployable_cash": deployable, "covenant_status": covenant,
                "customer_cash_identity_gap": _money(customer_cash - (float(t["revenue"]) + opening_ar - ending_ar + ending_contract - opening_contract)),
                "supplier_cash_identity_gap": _money(supplier_cash - (external_accrual + opening_ap - ending_ap)),
                "payroll_cash_identity_gap": _money(payroll_cash - float(t["personnel"])),
                "cash_rollforward_gap": _money(ending_cash - (opening_cash + ocf - capex_cash - repay + draw)),
                "rcf_identity_gap": _money(rcf_limit - rcf_drawn - undrawn),
            })
            state.update({
                "cash": ending_cash, "ar": ending_ar, "inventory": ending_inv, "ap": ending_ap,
                "contract_liabilities": ending_contract, "tax_payable": ending_tax, "debt": ending_debt,
            })
    return pd.DataFrame(rows)


def validate_liquidity_forecast(forecast: pd.DataFrame, horizon=12):
    if forecast.empty:
        return {
            "liquidity_forecast_cash_rollforward_max_gap": 0.0,
            "liquidity_forecast_customer_cash_max_gap": 0.0,
            "liquidity_forecast_supplier_cash_max_gap": 0.0,
            "workforce_liquidity_payroll_cash_max_gap": 0.0,
            "liquidity_forecast_rcf_identity_max_gap": 0.0,
            "liquidity_forecast_negative_balance_rows": 0,
            "liquidity_forecast_missing_scenario_months": horizon * 3,
            "liquidity_forecast_rcf_excess_rows": 0,
            "liquidity_forecast_shortfall_rows": 0,
            "passed": False,
        }
    cash_gap = float(forecast.cash_rollforward_gap.abs().max())
    customer_gap = float(forecast.customer_cash_identity_gap.abs().max())
    supplier_gap = float(forecast.supplier_cash_identity_gap.abs().max())
    payroll_gap = float(forecast.payroll_cash_identity_gap.abs().max())
    rcf_gap = float(forecast.rcf_identity_gap.abs().max())
    negative = int((forecast[["ending_ar", "ending_inventory", "ending_ap", "ending_contract_liabilities", "ending_cash", "gross_debt"]].min(axis=1) < -0.05).sum())
    coverage = forecast.groupby("scenario").month.nunique()
    missing = int(sum(max(horizon - int(v), 0) for v in coverage.values) + max(3 - len(coverage), 0) * horizon)
    excess = int(((forecast.rcf_drawn < -0.05) | (forecast.rcf_drawn - forecast.rcf_limit > 0.05)).sum())
    shortfall = int((forecast.liquidity_shortfall > 0.05).sum())
    checks = {
        "liquidity_forecast_cash_rollforward_max_gap": round(cash_gap, 2),
        "liquidity_forecast_customer_cash_max_gap": round(customer_gap, 2),
        "liquidity_forecast_supplier_cash_max_gap": round(supplier_gap, 2),
        "workforce_liquidity_payroll_cash_max_gap": round(payroll_gap, 2),
        "liquidity_forecast_rcf_identity_max_gap": round(rcf_gap, 2),
        "liquidity_forecast_negative_balance_rows": negative,
        "liquidity_forecast_missing_scenario_months": missing,
        "liquidity_forecast_rcf_excess_rows": excess,
        "liquidity_forecast_shortfall_rows": shortfall,
    }
    checks["passed"] = (
        cash_gap <= 0.02 and customer_gap <= 0.02 and supplier_gap <= 0.02
        and payroll_gap <= 0.02 and rcf_gap <= 0.02 and negative == 0
        and missing == 0 and excess == 0 and shortfall == 0
    )
    return checks
