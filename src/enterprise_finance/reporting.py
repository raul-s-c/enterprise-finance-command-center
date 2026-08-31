from __future__ import annotations

import numpy as np
import pandas as pd

from .accounting import validate_journal


def management_pnl(operations: pd.DataFrame, journal: pd.DataFrame) -> pd.DataFrame:
    base = operations.groupby(["month", "entity", "division"], as_index=False).agg(
        revenue=("revenue", "sum"), variable_production_cost=("variable_production_cost", "sum"),
        variable_selling_cost=("variable_selling_cost", "sum"), fixed_production_cost=("fixed_production_cost", "sum"),
        marginal_contribution=("marginal_contribution", "sum"), gross_profit=("gross_profit", "sum"), opex=("opex", "sum"),
    )
    fin = journal[journal.account.isin(["6100_DEPRECIATION", "7000_INTEREST", "7100_TAX"]) & ~journal.journal_type.eq("closing")].copy()
    fin["amount"] = fin.debit - fin.credit
    fin = fin.groupby(["month", "entity", "account"], as_index=False).amount.sum()
    pivot = fin.pivot_table(index=["month", "entity"], columns="account", values="amount", aggfunc="sum", fill_value=0).reset_index()
    for c in ["6100_DEPRECIATION", "7000_INTEREST", "7100_TAX"]:
        if c not in pivot:
            pivot[c] = 0.0
    base["entity_revenue"] = base.groupby(["month", "entity"]).revenue.transform("sum")
    base["allocation_share"] = base.revenue / base.entity_revenue.replace(0, np.nan)
    base = base.merge(pivot, on=["month", "entity"], how="left")
    for c in ["6100_DEPRECIATION", "7000_INTEREST", "7100_TAX"]:
        base[c] = base[c].fillna(0.0) * base.allocation_share.fillna(0.0)
    base["depreciation"] = base["6100_DEPRECIATION"]
    base["ebit"] = base.gross_profit - base.opex - base.depreciation
    base["interest"] = base["7000_INTEREST"]
    base["ebt"] = base.ebit - base.interest
    base["tax"] = base["7100_TAX"]
    base["net_income"] = base.ebt - base.tax
    return base.drop(columns=["entity_revenue", "allocation_share", "6100_DEPRECIATION", "7000_INTEREST", "7100_TAX"])


def group_balance_sheet(legal_bs: pd.DataFrame, markup: float) -> pd.DataFrame:
    rows: list[dict] = []
    for month, grp in legal_bs.groupby("month"):
        cash = float(grp.cash.sum())
        ar = float(grp.trade_receivables.sum())
        inventory_legal = float(grp.inventory.sum())
        unrealized_markup = max(inventory_legal, 0.0) * markup / (1.0 + markup)
        inventory = inventory_legal - unrealized_markup
        ppe_gross = float(grp.ppe_gross.sum())
        cip = float(grp.cip.sum())
        accum_dep = float(grp.accumulated_depreciation.sum())
        ap = float(grp.trade_payables.sum())
        tax_payable = float(grp.tax_payable.sum())
        debt = float(grp.debt.sum())
        share_capital = float(grp.share_capital.sum())
        retained = float(grp.retained_earnings.sum()) - unrealized_markup
        assets = cash + ar + inventory + ppe_gross + cip + accum_dep
        liabilities = ap + tax_payable + debt
        equity = share_capital + retained
        rows.append({
            "month": month, "cash": cash, "trade_receivables": ar, "inventory": inventory,
            "inventory_legal_transfer_value": inventory_legal, "unrealized_ic_markup_reserve": unrealized_markup,
            "ppe_gross": ppe_gross, "cip": cip, "accumulated_depreciation": accum_dep,
            "trade_payables": ap, "tax_payable": tax_payable, "debt": debt, "share_capital": share_capital,
            "retained_earnings": retained, "assets": assets, "liabilities": liabilities, "equity": equity,
            "balance_check": assets - liabilities - equity,
        })
    return pd.DataFrame(rows)


def working_capital(group_bs: pd.DataFrame, management: pd.DataFrame) -> pd.DataFrame:
    monthly = management.groupby("month", as_index=False).agg(
        revenue=("revenue", "sum"), variable_production_cost=("variable_production_cost", "sum"),
        fixed_production_cost=("fixed_production_cost", "sum"), opex=("opex", "sum"),
    )
    out = group_bs[["month", "trade_receivables", "inventory", "trade_payables"]].merge(monthly, on="month", how="left")
    out["net_working_capital"] = out.trade_receivables + out.inventory - out.trade_payables
    out["dso"] = out.trade_receivables / out.revenue.replace(0, np.nan) * 30.0
    physical_cost = out.variable_production_cost + out.fixed_production_cost
    out["dio"] = out.inventory / physical_cost.replace(0, np.nan) * 30.0
    external_spend = physical_cost + out.opex
    out["dpo"] = out.trade_payables / external_spend.replace(0, np.nan) * 30.0
    return out.fillna(0.0)


def profitability(operations: pd.DataFrame, end_month: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    end = pd.Period(end_month, freq="M")
    scope = operations[(operations.month >= str(end - 11)) & (operations.month <= end_month)].copy()
    product = scope.groupby(["division", "product"], as_index=False).agg(
        revenue=("revenue", "sum"), marginal_contribution=("marginal_contribution", "sum"), gross_profit=("gross_profit", "sum"),
        opex=("opex", "sum"), quantity=("quantity", "sum"),
    )
    product["mc_pct"] = product.marginal_contribution / product.revenue.replace(0, np.nan)
    product["gross_margin_pct"] = product.gross_profit / product.revenue.replace(0, np.nan)
    product["operating_contribution"] = product.gross_profit - product.opex
    customer = scope.groupby(["entity", "division", "customer", "customer_segment"], as_index=False).agg(
        revenue=("revenue", "sum"), marginal_contribution=("marginal_contribution", "sum"), gross_profit=("gross_profit", "sum"), opex=("opex", "sum")
    )
    customer["mc_pct"] = customer.marginal_contribution / customer.revenue.replace(0, np.nan)
    customer["gross_margin_pct"] = customer.gross_profit / customer.revenue.replace(0, np.nan)
    customer["operating_contribution"] = customer.gross_profit - customer.opex
    return product.fillna(0.0), customer.fillna(0.0)


def price_volume_mix(operations: pd.DataFrame, end_month: str) -> pd.DataFrame:
    end = pd.Period(end_month, freq="M")
    prior = end - 12
    current = operations[operations.month.eq(str(end))].groupby(["division", "product"], as_index=False).agg(revenue=("revenue", "sum"), quantity=("quantity", "sum"))
    previous = operations[operations.month.eq(str(prior))].groupby(["division", "product"], as_index=False).agg(revenue_prior=("revenue", "sum"), quantity_prior=("quantity", "sum"))
    merged = current.merge(previous, on=["division", "product"], how="outer").fillna(0.0)
    merged["price"] = merged.revenue / merged.quantity.replace(0, np.nan)
    merged["price_prior"] = merged.revenue_prior / merged.quantity_prior.replace(0, np.nan)
    merged = merged.fillna(0.0)
    rows: list[dict] = []
    for division, grp in merged.groupby("division"):
        rev_change = float(grp.revenue.sum() - grp.revenue_prior.sum())
        q1, q0 = float(grp.quantity.sum()), float(grp.quantity_prior.sum())
        avg_p0 = float(grp.revenue_prior.sum() / q0) if q0 else 0.0
        price_effect = float((grp.quantity * (grp.price - grp.price_prior)).sum())
        volume_effect = (q1 - q0) * avg_p0
        mix_effect = rev_change - price_effect - volume_effect
        rows.append({"division": division, "current_month": str(end), "comparison_month": str(prior), "revenue_change": rev_change, "price_effect": price_effect, "volume_effect": volume_effect, "mix_effect": mix_effect, "check": rev_change - price_effect - volume_effect - mix_effect})
    return pd.DataFrame(rows)


def consolidation_bridge(legal: pd.DataFrame, management: pd.DataFrame) -> pd.DataFrame:
    legal_m = legal.groupby("month", as_index=False).agg(legal_revenue=("revenue", "sum"), legal_ebit=("ebit", "sum"), legal_net_income=("net_income", "sum"))
    mgmt_m = management.groupby("month", as_index=False).agg(group_revenue=("revenue", "sum"), group_ebit=("ebit", "sum"), group_net_income=("net_income", "sum"))
    out = legal_m.merge(mgmt_m, on="month", how="outer").fillna(0.0)
    out["revenue_elimination"] = out.group_revenue - out.legal_revenue
    out["ebit_consolidation_adjustment"] = out.group_ebit - out.legal_ebit
    out["net_income_consolidation_adjustment"] = out.group_net_income - out.legal_net_income
    out["revenue_check"] = out.legal_revenue + out.revenue_elimination - out.group_revenue
    out["ebit_check"] = out.legal_ebit + out.ebit_consolidation_adjustment - out.group_ebit
    return out


def management_commentary(management: pd.DataFrame, working_capital_df: pd.DataFrame, cash_flow_df: pd.DataFrame, latest_fc: pd.DataFrame, end_month: str) -> list[dict]:
    monthly = management.groupby("month", as_index=False).agg(revenue=("revenue", "sum"), gross_profit=("gross_profit", "sum"), ebit=("ebit", "sum"), net_income=("net_income", "sum"))
    latest = monthly[monthly.month.eq(end_month)].iloc[0]
    py_month = str(pd.Period(end_month, freq="M") - 12)
    py = monthly[monthly.month.eq(py_month)]
    comments: list[dict] = []
    if not py.empty:
        py = py.iloc[0]
        rev_delta = float(latest.revenue - py.revenue)
        ebit_delta = float(latest.ebit - py.ebit)
        comments.append({"priority": 1, "topic": "Performance", "headline": f"Revenue {'increased' if rev_delta >= 0 else 'decreased'} {abs(rev_delta / max(py.revenue, 1)):.1%} YoY", "detail": f"Revenue changed by EUR {rev_delta/1e6:.1f}m and EBIT by EUR {ebit_delta/1e6:.1f}m versus {py_month}."})
    div = management[management.month.eq(end_month)].groupby("division", as_index=False).agg(revenue=("revenue", "sum"), ebit=("ebit", "sum"))
    if not div.empty:
        top = div.sort_values("ebit", ascending=False).iloc[0]
        weak = div.sort_values("ebit").iloc[0]
        comments.append({"priority": 2, "topic": "Portfolio", "headline": f"{top.division} is the largest EBIT contributor", "detail": f"{top.division} generated EUR {top.ebit/1e6:.1f}m EBIT in the month; {weak.division} is the lowest contributor at EUR {weak.ebit/1e6:.1f}m."})
    wc = working_capital_df[working_capital_df.month.eq(end_month)]
    if not wc.empty:
        w = wc.iloc[0]
        comments.append({"priority": 3, "topic": "Working Capital", "headline": f"Net working capital is EUR {w.net_working_capital/1e6:.1f}m", "detail": f"DSO {w.dso:.0f} days, DIO {w.dio:.0f} days and DPO {w.dpo:.0f} days."})
    cf = cash_flow_df[cash_flow_df.month.eq(end_month)].groupby("month", as_index=False).agg(free_cash_flow=("free_cash_flow", "sum"))
    if not cf.empty:
        fcf = float(cf.iloc[0].free_cash_flow)
        comments.append({"priority": 4, "topic": "Cash", "headline": f"Free cash flow is EUR {fcf/1e6:.1f}m", "detail": "Cash generation is derived from customer collections, supplier payments, tax, interest and CAPEX rather than from a standalone cash assumption."})
    base_fc = latest_fc[latest_fc.scenario.eq("Base")]
    if not base_fc.empty:
        next12 = base_fc[base_fc.horizon_month.le(12)].groupby("month", as_index=False).revenue_forecast.sum()
        comments.append({"priority": 5, "topic": "Forecast", "headline": f"Base forecast covers {len(next12)} forward months", "detail": f"The current vintage is {end_month} and includes explicit Upside and Downside scenarios plus historical bias correction."})
    return comments


def validate_all(journal: pd.DataFrame, legal_bs: pd.DataFrame, group_bs: pd.DataFrame, cf: pd.DataFrame, bridge: pd.DataFrame) -> dict:
    checks = validate_journal(journal)
    checks["legal_balance_sheet_max_gap"] = round(float(legal_bs.balance_check.abs().max()), 2) if not legal_bs.empty else 0.0
    ic = legal_bs.groupby("month", as_index=False).agg(ic_ar=("ic_receivables", "sum"), ic_ap=("ic_payables", "sum"))
    checks["legal_ic_ar_ap_max_mismatch"] = round(float((ic.ic_ar - ic.ic_ap).abs().max()), 2) if not ic.empty else 0.0
    checks["consolidated_balance_sheet_max_gap"] = round(float(group_bs.balance_check.abs().max()), 2) if not group_bs.empty else 0.0
    group_cf = cf.groupby("month", as_index=False).net_cash_movement.sum().sort_values("month")
    cash = group_bs[["month", "cash"]].sort_values("month").copy()
    cash["cash_change"] = cash.cash.diff().fillna(cash.cash)
    recon = cash.merge(group_cf, on="month", how="left").fillna(0.0)
    checks["cash_flow_reconciliation_max_gap"] = round(float((recon.cash_change - recon.net_cash_movement).abs().max()), 2) if not recon.empty else 0.0
    checks["consolidation_revenue_max_gap"] = round(float(bridge.revenue_check.abs().max()), 2) if not bridge.empty else 0.0
    checks["consolidation_ebit_max_gap"] = round(float(bridge.ebit_check.abs().max()), 2) if not bridge.empty else 0.0
    tolerances = {
        "journal_balance_max_gap": 0.02, "trial_balance_gap": 0.02, "legal_balance_sheet_max_gap": 0.05,
        "legal_ic_ar_ap_max_mismatch": 0.05, "consolidated_balance_sheet_max_gap": 0.05,
        "cash_flow_reconciliation_max_gap": 0.05, "consolidation_revenue_max_gap": 0.05, "consolidation_ebit_max_gap": 0.05,
    }
    checks["passed"] = all(abs(float(checks[k])) <= v for k, v in tolerances.items())
    return checks
