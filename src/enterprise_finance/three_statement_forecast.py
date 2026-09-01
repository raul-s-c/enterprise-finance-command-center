from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd


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
        spends = {str(month): round(float(project["budget"]) * float(weights[idx]), 2) for idx, month in enumerate(spend_months)}
        raw = sum(amount for month, amount in spends.items() if pd.Period(month, freq="M") <= end)
        raw_opening[str(project["id"])] = raw
        projects[str(project["id"])] = {
            "go_live": str(go_live),
            "budget": float(project["budget"]),
            "useful_life_months": int(project["useful_life_months"]),
            "spends": spends,
            "cip": 0.0,
        }
        for month, amount in spends.items():
            if pd.Period(month, freq="M") > end:
                future_spend[month] += amount

    raw_total = sum(raw_opening.values())
    scale = float(opening_cip) / raw_total if raw_total > 0.005 else 0.0
    for project_id, raw in raw_opening.items():
        projects[project_id]["cip"] = raw * scale
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

    The liquidity forecast supplies cash and Working Capital state. This layer adds
    forecast depreciation, asset-quality reserves, PPE/CIP, retained earnings and
    statement identities. No balancing plug is permitted.
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

    baseline_dep = float(management.loc[management.month.eq(end_month), "depreciation"].sum())
    tax_rate = float(config["group"]["corporate_tax_rate"])
    opening_ar_gross = float(opening.get("trade_receivables_gross", opening.get("trade_receivables", 0.0)))
    opening_ecl = float(opening.get("credit_loss_allowance", 0.0))
    opening_inv_gross = float(opening.get("inventory_gross", opening.get("inventory_legal_transfer_value", opening.get("inventory", 0.0))))
    opening_inv_prov = float(opening.get("inventory_provision", 0.0))
    opening_markup = float(opening.get("unrealized_ic_markup_reserve", 0.0))
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

        ppe_gross = float(opening.get("ppe_gross", 0.0))
        cip = float(opening.get("cip", 0.0))
        accum_dep = float(opening.get("accumulated_depreciation", 0.0))
        share_capital = float(opening.get("share_capital", 0.0))
        retained = float(opening.get("retained_earnings", 0.0))
        prior_ecl = opening_ecl
        prior_inv_prov = opening_inv_prov
        prior_markup = opening_markup
        projects, _ = _capex_project_schedules(config, end_month, cip)
        ecl_mult, inv_mult = _scenario_reserve_multiplier(str(scenario))

        for liq_row in liq.itertuples(index=False):
            month = str(liq_row.month)
            period = pd.Period(month, freq="M")
            month_fc = scenario_fc[scenario_fc.month.eq(month)]
            revenue = float(month_fc.revenue_forecast.sum())
            gross_profit_before_quality = float(month_fc.gross_profit_forecast.sum())
            opex = float(month_fc.opex_forecast.sum())

            depreciation = baseline_dep
            for project in projects.values():
                go_live = pd.Period(project["go_live"], freq="M")
                if period > go_live:
                    depreciation += float(project["budget"]) / float(project["useful_life_months"])

            for project in projects.values():
                spend = float(project["spends"].get(month, 0.0))
                if spend:
                    project["cip"] += spend
                    cip += spend
                if month == project["go_live"] and project["cip"] > 0.005:
                    transfer = float(project["cip"])
                    cip -= transfer
                    ppe_gross += transfer
                    project["cip"] = 0.0

            accum_dep -= depreciation

            ar_gross = float(liq_row.ending_ar)
            inv_gross = float(liq_row.ending_inventory)
            ecl = max(ar_gross * ecl_rate * ecl_mult, 0.0)
            inv_prov = max(inv_gross * inv_prov_rate * inv_mult, 0.0)
            markup_reserve = max(inv_gross * markup_rate, 0.0)
            credit_loss_expense = ecl - prior_ecl
            inventory_provision_expense = inv_prov - prior_inv_prov
            unrealized_profit_adjustment = markup_reserve - prior_markup

            gross_profit = gross_profit_before_quality - inventory_provision_expense - unrealized_profit_adjustment
            ebit = gross_profit - opex - credit_loss_expense - depreciation
            interest = float(liq_row.interest_cash)
            ebt = ebit - interest
            tax = float(liq_row.tax_accrual)
            net_income = ebt - tax
            retained += net_income

            trade_receivables = ar_gross - ecl
            inventory = inv_gross - inv_prov - markup_reserve
            cash = float(liq_row.ending_cash)
            trade_payables = float(liq_row.ending_ap)
            tax_payable = float(liq_row.ending_tax_payable)
            debt = float(liq_row.gross_debt)
            contract_liabilities = float(liq_row.ending_contract_liabilities)

            assets = cash + trade_receivables + inventory + ppe_gross + cip + accum_dep
            liabilities = trade_payables + tax_payable + debt + contract_liabilities
            equity = share_capital + retained
            balance_check = assets - liabilities - equity

            pnl_rows.append({
                "scenario": scenario, "month": month, "horizon_month": int(liq_row.horizon_month),
                "revenue": revenue, "gross_profit_before_asset_quality": gross_profit_before_quality,
                "inventory_provision_expense": inventory_provision_expense,
                "unrealized_ic_profit_adjustment": unrealized_profit_adjustment,
                "gross_profit": gross_profit, "opex": opex,
                "credit_loss_expense": credit_loss_expense, "depreciation": depreciation,
                "ebit": ebit, "interest": interest, "ebt": ebt, "tax": tax,
                "net_income": net_income,
                "ebit_identity_gap": ebit - (gross_profit - opex - credit_loss_expense - depreciation),
                "net_income_identity_gap": net_income - (ebit - interest - tax),
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
            financing_cash_flow = float(liq_row.rcf_draw) - float(liq_row.scheduled_debt_repayment)
            investing_cash_flow = -float(liq_row.capex)
            operating_cash_flow = float(liq_row.operating_cash_flow)
            net_cash_movement = operating_cash_flow + investing_cash_flow + financing_cash_flow
            cf_rows.append({
                "scenario": scenario, "month": month, "horizon_month": int(liq_row.horizon_month),
                "operating_cash_flow": operating_cash_flow,
                "investing_cash_flow": investing_cash_flow,
                "financing_cash_flow": financing_cash_flow,
                "free_cash_flow": operating_cash_flow + investing_cash_flow,
                "net_cash_movement": net_cash_movement,
                "opening_cash": float(liq_row.opening_cash), "ending_cash": cash,
                "cash_flow_identity_gap": cash - float(liq_row.opening_cash) - net_cash_movement,
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
        balance_gap <= 0.10 and cf_gap <= 0.02 and ebit_gap <= 0.02
        and ni_gap <= 0.02 and cash_link_gap <= 0.02 and missing == 0
    )
    return checks
