from __future__ import annotations

from collections import deque

import pandas as pd

from .liquidity_forecast import (
    _forecast_terms,
    _opening_state,
    _treasury_cfg,
    derive_prepayment_ratios,
    future_capex,
)


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
    """Project liquidity once per forecast month and scenario.

    Entity / Division forecast rows are used to calculate working-capital drivers,
    but the consolidated liquidity state advances exactly once for each month.
    """
    if forecasts.empty:
        return pd.DataFrame()
    current = forecasts[
        forecasts.vintage.eq(end_month) & forecasts.horizon_month.le(horizon)
    ].copy()
    if current.empty:
        return pd.DataFrame()

    state0 = _opening_state(balance_sheet, end_month)
    prepay = derive_prepayment_ratios(management, advances, end_month, config)
    treasury_cfg = _treasury_cfg(config)
    rcf_limit = float(treasury_cfg["rcf_limit"])
    capex = future_capex(config, end_month, horizon)
    capex_map = capex.groupby("month").capex.sum().to_dict() if not capex.empty else {}

    latest_debt = debt_schedule[debt_schedule.month.eq(end_month)] if not debt_schedule.empty else pd.DataFrame()
    if not latest_debt.empty and float(latest_debt.gross_debt.sum()) > 0.0:
        annual_rate = float(
            (latest_debt.gross_debt * latest_debt.implied_annual_interest_rate).sum()
            / latest_debt.gross_debt.sum()
        )
    else:
        annual_rate = 0.035

    actual_liq = (
        actual_liquidity[actual_liquidity.month.le(end_month)].sort_values("month")
        if not actual_liquidity.empty else pd.DataFrame()
    )
    actual_ebitda = list(actual_liq.ebitda.tail(11).astype(float)) if "ebitda" in actual_liq else []
    actual_interest = list(actual_liq.interest_expense.tail(11).astype(float)) if "interest_expense" in actual_liq else []
    depreciation_run_rate = (
        float(management[management.month.eq(end_month)].depreciation.sum())
        if "depreciation" in management.columns else 0.0
    )

    rows: list[dict] = []
    for scenario in sorted(current.scenario.unique()):
        state = dict(state0)
        rcf_drawn = 0.0
        ebitda_window = deque(actual_ebitda, maxlen=12)
        interest_window = deque(actual_interest, maxlen=12)
        months = (
            current[current.scenario.eq(scenario)][["month", "horizon_month"]]
            .drop_duplicates()
            .sort_values("horizon_month")
        )

        for month_row in months.itertuples(index=False):
            month = str(month_row.month)
            month_scope = current[
                current.scenario.eq(scenario) & current.month.eq(month)
            ]
            terms = _forecast_terms(month_scope, prepay, config)

            opening_cash = float(state["cash"])
            opening_ar = float(state["ar"])
            opening_inventory = float(state["inventory"])
            opening_ap = float(state["ap"])
            opening_contract = float(state["contract_liabilities"])
            opening_tax = float(state["tax_payable"])
            opening_debt = float(state["debt"])

            ending_ar = float(terms["target_ar"])
            ending_inventory = float(terms["target_inventory"])
            ending_ap = float(terms["target_ap_base"])
            ending_contract = float(terms["target_contract_liabilities"])

            inventory_change = ending_inventory - opening_inventory
            operating_accrual = max(float(terms["operating_cost"]) + inventory_change, 0.0)
            customer_cash = (
                float(terms["revenue"]) + opening_ar - ending_ar
                + ending_contract - opening_contract
            )
            supplier_cash = operating_accrual + opening_ap - ending_ap

            interest = max(opening_debt, 0.0) * annual_rate / 12.0
            ebit = float(terms["gross_profit"]) - float(terms["opex"]) - depreciation_run_rate
            ebt = ebit - interest
            tax_accrual = max(ebt, 0.0) * float(config["group"]["corporate_tax_rate"])
            tax_available = opening_tax + tax_accrual
            period = pd.Period(month, freq="M")
            tax_payment = tax_available * 0.78 if period.month in {3, 6, 9, 12} else 0.0
            ending_tax = max(tax_available - tax_payment, 0.0)

            operating_cash_flow = customer_cash - supplier_cash - interest - tax_payment
            capex_cash = float(capex_map.get(month, 0.0))
            scheduled_repayment = (
                min(opening_debt * 0.0125, opening_debt)
                if period.month in {3, 6, 9, 12} else 0.0
            )
            cash_before_rcf = opening_cash + operating_cash_flow - capex_cash - scheduled_repayment
            available_rcf = max(rcf_limit - rcf_drawn, 0.0)
            required_draw = max(float(treasury_cfg["minimum_cash"]) - cash_before_rcf, 0.0)
            rcf_draw = min(required_draw, available_rcf)
            rcf_drawn += rcf_draw
            ending_cash = cash_before_rcf + rcf_draw
            ending_debt = max(opening_debt - scheduled_repayment + rcf_draw, 0.0)

            ebitda = float(terms["ebitda"])
            ebitda_window.append(ebitda)
            interest_window.append(interest)
            ebitda_ttm = float(sum(ebitda_window))
            interest_ttm = float(sum(interest_window))
            net_debt = ending_debt - ending_cash
            net_leverage = net_debt / ebitda_ttm if abs(ebitda_ttm) > 0.005 else 0.0
            interest_coverage = ebitda_ttm / interest_ttm if interest_ttm > 0.005 else 99.0
            undrawn_rcf = max(rcf_limit - rcf_drawn, 0.0)
            liquidity_headroom = (
                max(ending_cash - float(treasury_cfg["minimum_cash"]), 0.0) + undrawn_rcf
            )
            deployable_cash = max(
                ending_cash
                - float(treasury_cfg["minimum_cash"])
                - float(treasury_cfg["strategic_liquidity_buffer"]),
                0.0,
            )
            covenant_status = "PASS" if (
                net_leverage <= float(treasury_cfg["net_leverage_limit"])
                and interest_coverage >= float(treasury_cfg["interest_coverage_min"])
            ) else "WATCH"
            liquidity_shortfall = max(float(treasury_cfg["minimum_cash"]) - ending_cash, 0.0)

            rows.append({
                "scenario": str(scenario),
                "month": month,
                "horizon_month": int(month_row.horizon_month),
                "opening_cash": opening_cash,
                "revenue": float(terms["revenue"]),
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
                "scheduled_debt_repayment": scheduled_repayment,
                "rcf_draw": rcf_draw,
                "rcf_drawn": rcf_drawn,
                "rcf_limit": rcf_limit,
                "undrawn_rcf": undrawn_rcf,
                "ending_cash": ending_cash,
                "gross_debt": ending_debt,
                "net_debt": net_debt,
                "ebitda_ttm": ebitda_ttm,
                "interest_ttm": interest_ttm,
                "net_leverage": net_leverage,
                "interest_coverage": interest_coverage,
                "minimum_operating_cash": float(treasury_cfg["minimum_cash"]),
                "strategic_liquidity_buffer": float(treasury_cfg["strategic_liquidity_buffer"]),
                "liquidity_headroom": liquidity_headroom,
                "liquidity_shortfall": liquidity_shortfall,
                "deployable_cash": deployable_cash,
                "covenant_status": covenant_status,
                "customer_cash_identity_gap": customer_cash - (
                    float(terms["revenue"]) + opening_ar - ending_ar
                    + ending_contract - opening_contract
                ),
                "supplier_cash_identity_gap": supplier_cash - (
                    operating_accrual + opening_ap - ending_ap
                ),
                "cash_rollforward_gap": ending_cash - (
                    opening_cash + operating_cash_flow - capex_cash
                    - scheduled_repayment + rcf_draw
                ),
                "rcf_identity_gap": rcf_limit - rcf_drawn - undrawn_rcf,
            })

            state.update({
                "cash": ending_cash,
                "ar": ending_ar,
                "inventory": ending_inventory,
                "ap": ending_ap,
                "contract_liabilities": ending_contract,
                "tax_payable": ending_tax,
                "debt": ending_debt,
            })

    return pd.DataFrame(rows)


def validate_liquidity_forecast(forecast: pd.DataFrame, horizon: int = 12) -> dict:
    if forecast.empty:
        return {
            "liquidity_forecast_cash_rollforward_max_gap": 0.0,
            "liquidity_forecast_customer_cash_max_gap": 0.0,
            "liquidity_forecast_supplier_cash_max_gap": 0.0,
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
    rcf_gap = float(forecast.rcf_identity_gap.abs().max())
    balance_cols = [
        "ending_ar", "ending_inventory", "ending_ap",
        "ending_contract_liabilities", "ending_cash", "gross_debt",
    ]
    negative = int((forecast[balance_cols].min(axis=1) < -0.05).sum())
    coverage = forecast.groupby("scenario").month.nunique()
    missing = int(
        sum(max(horizon - int(value), 0) for value in coverage.values)
        + max(3 - len(coverage), 0) * horizon
    )
    rcf_excess = int(
        ((forecast.rcf_drawn < -0.05) | (forecast.rcf_drawn - forecast.rcf_limit > 0.05)).sum()
    )
    shortfall = int((forecast.liquidity_shortfall > 0.05).sum())
    checks = {
        "liquidity_forecast_cash_rollforward_max_gap": round(cash_gap, 2),
        "liquidity_forecast_customer_cash_max_gap": round(customer_gap, 2),
        "liquidity_forecast_supplier_cash_max_gap": round(supplier_gap, 2),
        "liquidity_forecast_rcf_identity_max_gap": round(rcf_gap, 2),
        "liquidity_forecast_negative_balance_rows": negative,
        "liquidity_forecast_missing_scenario_months": missing,
        "liquidity_forecast_rcf_excess_rows": rcf_excess,
        "liquidity_forecast_shortfall_rows": shortfall,
    }
    checks["passed"] = (
        cash_gap <= 0.02 and customer_gap <= 0.02 and supplier_gap <= 0.02
        and rcf_gap <= 0.02 and negative == 0 and missing == 0
        and rcf_excess == 0 and shortfall == 0
    )
    return checks
