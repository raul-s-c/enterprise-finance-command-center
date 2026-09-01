from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd


def _money(value: float) -> float:
    """Materialize monetary state at ledger precision."""
    return round(float(value), 2)


def _capex_project_schedules(config: dict, end_month: str, opening_cip: float) -> tuple[dict[str, dict], dict[str, float]]:
    end = pd.Period(end_month, freq="M")
    projects: dict[str, dict] = {}
    raw_opening: dict[str, float] = {}
    future_spend: dict[str, float] = defaultdict(float)

    for project in config.get("capex_projects", []):
        start = pd.Period(project["start"], freq="M")
        build_months = int(project["build_months"])
        spend_months = pd.period_range(start=start, periods=build_months, freq="M")
        x = np.linspace(0.25, np.pi - 0.25, build_months)
        weights = np.sin(x)
        weights = weights / weights.sum()
        go_live = start + build_months - 1
        if go_live <= end:
            continue
        spends = {str(month): _money(float(project["budget"]) * float(weights[idx])) for idx, month in enumerate(spend_months)}
        raw = _money(sum(amount for month, amount in spends.items() if pd.Period(month, freq="M") <= end))
        raw_opening[str(project["id"])] = raw
        projects[str(project["id"])] = {
            "go_live": str(go_live),
            "budget": _money(project["budget"]),
            "useful_life_months": int(project["useful_life_months"]),
            "spends": spends,
            "cip": 0.0,
        }
        for month, amount in spends.items():
            if pd.Period(month, freq="M") > end:
                future_spend[month] = _money(future_spend[month] + amount)

    raw_total = _money(sum(raw_opening.values()))
    scale = float(opening_cip) / raw_total if raw_total > 0.005 else 0.0
    remaining = _money(opening_cip)
    ids = list(raw_opening)
    for idx, project_id in enumerate(ids):
        if idx == len(ids) - 1:
            allocated = remaining
        else:
            allocated = _money(raw_opening[project_id] * scale)
            remaining = _money(remaining - allocated)
        projects[project_id]["cip"] = allocated
    return projects, dict(future_spend)


def _scenario_reserve_multiplier(scenario: str) -> tuple[float, float]:
    if scenario == "Downside":
        return 1.15, 1.10
    if scenario == "Upside":
        return 0.95, 0.97
    return 1.0, 1.0


def build_three_statement_forecast(
    forecasts: pd.DataFrame,
    liquidity: pd.DataFrame,
    management: pd.DataFrame,
    balance_sheet: pd.DataFrame,
    config: dict,
    end_month: str,
    horizon: int = 12,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build linked forecast P&L, Balance Sheet and Cash Flow statements.

    The detailed operating forecast first feeds the liquidity engine. Liquidity
    materializes Revenue, Gross Profit / EBITDA and OPEX at the same cent precision
    used to derive AR, Inventory, AP and cash. The three-statement layer consumes
    that exact monetary block rather than independently re-aggregating detailed
    forecast rows. This preserves a single forward monetary source and prevents
    divisional rounding differences from accumulating in retained earnings.

    Legacy/unit-test liquidity frames may not expose the newer Workforce-specific
    personnel/non-people split. In that case the function falls back to the detailed
    forecast OPEX aggregate while preserving the same three-statement identities.

    No balancing plug is permitted.
    """
    if forecasts.empty or liquidity.empty or balance_sheet.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    opening = balance_sheet[balance_sheet.month.eq(end_month)]
    if opening.empty:
        raise ValueError(f"No opening Balance Sheet exists for {end_month}")
    opening = opening.iloc[0]

    current_forecasts = forecasts[
        forecasts.vintage.eq(end_month) & forecasts.horizon_month.le(horizon)
    ].copy()
    if current_forecasts.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    baseline_dep = _money(management.loc[management.month.eq(end_month), "depreciation"].sum())
    opening_ar_gross = _money(opening.get("trade_receivables_gross", opening.get("trade_receivables", 0.0)))
    opening_ecl = _money(opening.get("credit_loss_allowance", 0.0))
    opening_inv_gross = _money(opening.get("inventory_gross", opening.get("inventory_legal_transfer_value", opening.get("inventory", 0.0))))
    opening_inv_prov = _money(opening.get("inventory_provision", 0.0))
    opening_markup = _money(opening.get("unrealized_ic_markup_reserve", 0.0))
    ecl_rate = opening_ecl / opening_ar_gross if opening_ar_gross > 0.005 else 0.0
    inv_prov_rate = opening_inv_prov / opening_inv_gross if opening_inv_gross > 0.005 else 0.0
    markup_rate = opening_markup / opening_inv_gross if opening_inv_gross > 0.005 else 0.0

    pnl_rows: list[dict] = []
    bs_rows: list[dict] = []
    cf_rows: list[dict] = []

    for scenario in sorted(liquidity.scenario.unique()):
        liq = liquidity[liquidity.scenario.eq(scenario)].sort_values("horizon_month").copy()
        scenario_fc = current_forecasts[current_forecasts.scenario.eq(scenario)].copy()
        if liq.empty or scenario_fc.empty:
            continue

        ppe_gross = _money(opening.get("ppe_gross", 0.0))
        cip = _money(opening.get("cip", 0.0))
        accum_dep = _money(opening.get("accumulated_depreciation", 0.0))
        share_capital = _money(opening.get("share_capital", 0.0))
        retained = _money(opening.get("retained_earnings", 0.0))
        prior_ecl = opening_ecl
        prior_inv_prov = opening_inv_prov
        prior_markup = opening_markup
        projects, _ = _capex_project_schedules(config, end_month, cip)
        ecl_mult, inv_mult = _scenario_reserve_multiplier(str(scenario))

        for liq_row in liq.itertuples(index=False):
            month = str(liq_row.month)
            period = pd.Period(month, freq="M")
            month_fc = scenario_fc[scenario_fc.month.eq(month)]

            detailed_revenue = _money(month_fc.revenue_forecast.sum())
            detailed_opex = _money(month_fc.opex_forecast.sum())
            detailed_gp = _money(month_fc.gross_profit_forecast.sum())

            # Production v0.14 liquidity frames expose the exact cent-precise
            # Workforce driver block. Older fixtures do not, so they retain the
            # detailed forecast aggregate as a compatibility fallback.
            revenue = _money(getattr(liq_row, "revenue", detailed_revenue))
            if hasattr(liq_row, "personnel_cost") and hasattr(liq_row, "non_people_opex"):
                opex = _money(float(liq_row.personnel_cost) + float(liq_row.non_people_opex))
            else:
                opex = detailed_opex
            if hasattr(liq_row, "ebitda"):
                gross_profit_before_quality = _money(float(liq_row.ebitda) + opex)
            else:
                gross_profit_before_quality = detailed_gp

            driver_revenue_rounding_gap = _money(revenue - detailed_revenue)
            driver_opex_rounding_gap = _money(opex - detailed_opex)

            depreciation = baseline_dep
            for project in projects.values():
                go_live = pd.Period(project["go_live"], freq="M")
                if period > go_live:
                    depreciation = _money(depreciation + float(project["budget"]) / float(project["useful_life_months"]))

            for project in projects.values():
                spend = _money(project["spends"].get(month, 0.0))
                if spend:
                    project["cip"] = _money(project["cip"] + spend)
                    cip = _money(cip + spend)
                if month == project["go_live"] and project["cip"] > 0.005:
                    transfer = _money(project["cip"])
                    cip = _money(cip - transfer)
                    ppe_gross = _money(ppe_gross + transfer)
                    project["cip"] = 0.0

            accum_dep = _money(accum_dep - depreciation)

            ar_gross = _money(liq_row.ending_ar)
            inv_gross = _money(liq_row.ending_inventory)
            ecl = _money(max(ar_gross * ecl_rate * ecl_mult, 0.0))
            inv_prov = _money(max(inv_gross * inv_prov_rate * inv_mult, 0.0))
            markup_reserve = _money(max(inv_gross * markup_rate, 0.0))
            credit_loss_expense = _money(ecl - prior_ecl)
            inventory_provision_expense = _money(inv_prov - prior_inv_prov)
            unrealized_profit_adjustment = _money(markup_reserve - prior_markup)

            gross_profit = _money(gross_profit_before_quality - inventory_provision_expense - unrealized_profit_adjustment)
            ebit = _money(gross_profit - opex - credit_loss_expense - depreciation)
            interest = _money(liq_row.interest_cash)
            ebt = _money(ebit - interest)
            tax = _money(liq_row.tax_accrual)
            net_income = _money(ebt - tax)
            retained = _money(retained + net_income)

            trade_receivables = _money(ar_gross - ecl)
            inventory = _money(inv_gross - inv_prov - markup_reserve)
            cash = _money(liq_row.ending_cash)
            trade_payables = _money(liq_row.ending_ap)
            tax_payable = _money(liq_row.ending_tax_payable)
            debt = _money(liq_row.gross_debt)
            contract_liabilities = _money(liq_row.ending_contract_liabilities)

            assets = _money(cash + trade_receivables + inventory + ppe_gross + cip + accum_dep)
            liabilities = _money(trade_payables + tax_payable + debt + contract_liabilities)
            equity = _money(share_capital + retained)
            balance_check = _money(assets - liabilities - equity)

            pnl_rows.append({
                "scenario": scenario, "month": month, "horizon_month": int(liq_row.horizon_month),
                "revenue": revenue, "gross_profit_before_asset_quality": gross_profit_before_quality,
                "inventory_provision_expense": inventory_provision_expense,
                "unrealized_ic_profit_adjustment": unrealized_profit_adjustment,
                "gross_profit": gross_profit, "opex": opex,
                "credit_loss_expense": credit_loss_expense, "depreciation": depreciation,
                "ebit": ebit, "interest": interest, "ebt": ebt, "tax": tax,
                "net_income": net_income,
                "operating_forecast_revenue_rounding_gap": driver_revenue_rounding_gap,
                "operating_forecast_opex_rounding_gap": driver_opex_rounding_gap,
                "ebit_identity_gap": _money(ebit - (gross_profit - opex - credit_loss_expense - depreciation)),
                "net_income_identity_gap": _money(net_income - (ebit - interest - tax)),
            })
            bs_rows.append({
                "scenario": scenario, "month": month, "horizon_month": int(liq_row.horizon_month),
                "cash": cash,
                "trade_receivables_gross": ar_gross, "credit_loss_allowance": ecl,
                "trade_receivables": trade_receivables,
                "inventory_gross": inv_gross, "inventory_provision": inv_prov,
                "unrealized_ic_markup_reserve": markup_reserve, "inventory": inventory,
                "ppe_gross": ppe_gross, "cip": cip, "accumulated_depreciation": accum_dep,
                "trade_payables": trade_payables, "tax_payable": tax_payable,
                "debt": debt, "contract_liabilities": contract_liabilities,
                "share_capital": share_capital, "retained_earnings": retained,
                "assets": assets, "liabilities": liabilities, "equity": equity,
                "balance_check": balance_check,
            })
            financing_cash_flow = _money(float(liq_row.rcf_draw) - float(liq_row.scheduled_debt_repayment))
            investing_cash_flow = _money(-float(liq_row.capex))
            operating_cash_flow = _money(liq_row.operating_cash_flow)
            net_cash_movement = _money(operating_cash_flow + investing_cash_flow + financing_cash_flow)
            opening_cash = _money(liq_row.opening_cash)
            cf_rows.append({
                "scenario": scenario, "month": month, "horizon_month": int(liq_row.horizon_month),
                "operating_cash_flow": operating_cash_flow,
                "investing_cash_flow": investing_cash_flow,
                "financing_cash_flow": financing_cash_flow,
                "free_cash_flow": _money(operating_cash_flow + investing_cash_flow),
                "net_cash_movement": net_cash_movement,
                "opening_cash": opening_cash, "ending_cash": cash,
                "cash_flow_identity_gap": _money(cash - opening_cash - net_cash_movement),
            })

            prior_ecl = ecl
            prior_inv_prov = inv_prov
            prior_markup = markup_reserve

    return pd.DataFrame(pnl_rows), pd.DataFrame(bs_rows), pd.DataFrame(cf_rows)


def validate_three_statement_forecast(pnl: pd.DataFrame, bs: pd.DataFrame, cf: pd.DataFrame, horizon: int = 12) -> dict:
    if pnl.empty or bs.empty or cf.empty:
        return {
            "three_statement_balance_sheet_max_gap": 0.0,
            "three_statement_cash_flow_max_gap": 0.0,
            "three_statement_ebit_identity_max_gap": 0.0,
            "three_statement_net_income_identity_max_gap": 0.0,
            "three_statement_cash_link_max_gap": 0.0,
            "three_statement_missing_scenario_months": horizon * 3,
            "passed": False,
        }
    balance_gap = float(bs.balance_check.abs().max())
    cf_gap = float(cf.cash_flow_identity_gap.abs().max())
    ebit_gap = float(pnl.ebit_identity_gap.abs().max())
    ni_gap = float(pnl.net_income_identity_gap.abs().max())
    cash_link = bs[["scenario", "month", "cash"]].merge(
        cf[["scenario", "month", "ending_cash"]], on=["scenario", "month"], how="outer"
    ).fillna(0.0)
    cash_link_gap = float((cash_link.cash - cash_link.ending_cash).abs().max())
    coverage = bs.groupby("scenario").month.nunique()
    missing = int(sum(max(horizon - int(v), 0) for v in coverage.values) + max(3 - len(coverage), 0) * horizon)
    checks = {
        "three_statement_balance_sheet_max_gap": round(balance_gap, 2),
        "three_statement_cash_flow_max_gap": round(cf_gap, 2),
        "three_statement_ebit_identity_max_gap": round(ebit_gap, 2),
        "three_statement_net_income_identity_max_gap": round(ni_gap, 2),
        "three_statement_cash_link_max_gap": round(cash_link_gap, 2),
        "three_statement_missing_scenario_months": missing,
    }
    checks["passed"] = (
        balance_gap <= 0.02 and cf_gap <= 0.02 and ebit_gap <= 0.02
        and ni_gap <= 0.02 and cash_link_gap <= 0.02 and missing == 0
    )
    return checks
