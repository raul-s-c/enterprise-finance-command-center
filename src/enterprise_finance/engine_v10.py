from __future__ import annotations

import gzip
import json
from pathlib import Path

import pandas as pd

from . import engine as base_engine
from .accounting import cash_flow, validate_factory_absorption_accounting
from .budgeting_v09 import build_annual_budgets, budget_performance, validate_budgets
from .contract_liabilities import (
    apply_contract_liability_accounting,
    chart_of_accounts_with_contracts,
    contract_liability_summary,
    group_balance_sheet_with_contracts,
    legal_balance_sheet_with_contracts,
    strip_provision_journals,
    validate_contract_liabilities,
)
from .customer_receivables_v10 import build_ar_aging_with_contracts, validate_contract_ar
from .engine_v07 import _working_capital_with_asset_quality
from .engine_v09 import build as build_v09
from .planning_v09 import fy_plan_bridge
from .provisions import (
    append_provision_journals,
    build_credit_loss_schedule,
    build_inventory_provision_schedule,
    legal_pnl_with_provisions,
    management_pnl_with_provisions,
    provision_monthly_summary,
    validate_provisions,
)
from .reporting import consolidation_bridge, management_commentary, validate_all
from .supplier_payables import ap_aging_summary, build_ap_aging, supplier_concentration, supplier_master, validate_ap_aging
from .working_capital_detail import ar_aging_summary, inventory_aging_summary, validate_working_capital_schedules


VERSION = "0.10.0"


def _read_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def _write_csv(df: pd.DataFrame, path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def _write_gzip_csv(df: pd.DataFrame, path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        df.to_csv(handle, index=False)


def _group_management(management: pd.DataFrame) -> pd.DataFrame:
    return management.groupby("month", as_index=False).agg(
        revenue=("revenue", "sum"),
        marginal_contribution=("marginal_contribution", "sum"),
        gross_profit=("gross_profit", "sum"),
        opex=("opex", "sum"),
        depreciation=("depreciation", "sum"),
        ebit=("ebit", "sum"),
        net_income=("net_income", "sum"),
        factory_absorption_variance=("factory_absorption_variance", "sum"),
        inventory_provision_expense=("inventory_provision_expense", "sum"),
        credit_loss_expense=("credit_loss_expense", "sum"),
    )


def _group_cash_flow(cf: pd.DataFrame) -> pd.DataFrame:
    return cf.groupby("month", as_index=False).agg(
        operating_cash_flow=("operating_cash_flow", "sum"),
        investing_cash_flow=("investing_cash_flow", "sum"),
        financing_cash_flow=("financing_cash_flow", "sum"),
        free_cash_flow=("free_cash_flow", "sum"),
        net_cash_movement=("net_cash_movement", "sum"),
    )


def _inventory_family_summary(inventory_aging: pd.DataFrame, end_month: str) -> pd.DataFrame:
    if inventory_aging.empty:
        return pd.DataFrame()
    latest = inventory_aging[inventory_aging.month.eq(end_month)]
    if latest.empty:
        return pd.DataFrame()
    out = latest.groupby(["division", "product_family"], as_index=False).agg(
        inventory_value=("inventory_value", "sum"),
        slow_moving_value=("slow_moving_value", "sum"),
        obsolescence_risk_value=("obsolescence_risk_value", "sum"),
        sku_count=("product", "nunique"),
    )
    out["slow_moving_pct"] = out.slow_moving_value / out.inventory_value.replace(0, pd.NA)
    out["obsolescence_risk_pct"] = out.obsolescence_risk_value / out.inventory_value.replace(0, pd.NA)
    return out.fillna(0.0)


def _working_capital_with_contracts(group_bs: pd.DataFrame, management: pd.DataFrame) -> pd.DataFrame:
    wc = _working_capital_with_asset_quality(group_bs, management)
    if "contract_liabilities" not in group_bs.columns:
        wc["contract_liabilities"] = 0.0
    else:
        wc = wc.merge(group_bs[["month", "contract_liabilities"]], on="month", how="left")
        wc["contract_liabilities"] = wc.contract_liabilities.fillna(0.0)
    wc["trade_net_working_capital"] = wc.net_working_capital
    wc["operating_net_working_capital"] = wc.trade_net_working_capital - wc.contract_liabilities
    wc["gross_operating_net_working_capital"] = wc.gross_net_working_capital - wc.contract_liabilities
    return wc


def build(end_month: str, config_path: str = "config/company.yml", allow_live_macro: bool = True):
    """Run v0.9 and rebuild the close with customer advances / contract liabilities."""
    result = build_v09(end_month, config_path=config_path, allow_live_macro=allow_live_macro)
    config = base_engine.load_config(config_path)

    operations = _read_csv("data/runtime/operational.csv.gz")
    journal_v09 = _read_csv("data/runtime/journal.csv.gz")
    customers = _read_csv("data/processed/customers.csv")
    products = _read_csv("data/processed/products.csv")
    inventory_aging = _read_csv("data/processed/inventory_aging.csv")
    factory = _read_csv("data/processed/factory.csv")
    forecasts = _read_csv("data/processed/forecast_vintages.csv")
    latest_fc = _read_csv("data/processed/forecast.csv")

    # Remove the v0.7 provision overlay, transform customer settlement, then rebuild provisions.
    journal_pre_provision = strip_provision_journals(journal_v09)
    contract_pre_provision, commitments, contract_schedule = apply_contract_liability_accounting(
        journal_pre_provision, operations, config
    )
    ar_aging = build_ar_aging_with_contracts(contract_pre_provision, customers, config)
    credit_loss = build_credit_loss_schedule(ar_aging, config)
    inventory_provision = build_inventory_provision_schedule(inventory_aging, config)
    journal, provision_journal = append_provision_journals(
        contract_pre_provision, credit_loss, inventory_provision
    )

    legal = legal_pnl_with_provisions(journal)
    legal_bs = legal_balance_sheet_with_contracts(journal)
    group_bs = group_balance_sheet_with_contracts(
        legal_bs, float(config["transfer_pricing"]["manufacturing_cost_plus"])
    )
    cf = cash_flow(journal)
    management = management_pnl_with_provisions(operations, journal, set(config["factories"]))
    # Inventory provision is a valuation adjustment, not physical usage for DIO.
    management["fixed_production_cost"] = management.fixed_production_cost - management.inventory_provision_expense
    wc = _working_capital_with_contracts(group_bs, management)
    bridge = consolidation_bridge(legal, management)

    contract_summary = contract_liability_summary(contract_schedule, commitments)
    provision_summary = provision_monthly_summary(credit_loss, inventory_provision, journal)
    ap_aging = build_ap_aging(journal, config)
    ap_summary = ap_aging_summary(ap_aging)
    concentration = supplier_concentration(ap_aging, end_month)
    suppliers = supplier_master(ap_aging)

    budgets = build_annual_budgets(management, config, end_month)
    performance = budget_performance(management, budgets, end_month)
    fy_bridge = fy_plan_bridge(management, budgets, forecasts, end_month)

    commentary = management_commentary(management, wc, cf, latest_fc, end_month)

    checks = validate_all(journal, legal_bs, group_bs, cf, bridge)
    wc_checks = validate_working_capital_schedules(journal, ar_aging, inventory_aging)
    contract_ar_checks = validate_contract_ar(journal, ar_aging)
    contract_checks = validate_contract_liabilities(journal, contract_schedule)
    provision_checks = validate_provisions(journal, credit_loss, inventory_provision)
    ap_checks = validate_ap_aging(journal, ap_aging)
    absorption_checks = validate_factory_absorption_accounting(factory, journal)
    budget_checks = validate_budgets(management, budgets, config)

    for source in [wc_checks, contract_ar_checks, contract_checks, provision_checks, ap_checks, absorption_checks, budget_checks]:
        checks.update({key: value for key, value in source.items() if key != "passed"})

    current_year = pd.Period(end_month, freq="M").year
    current_budget = budgets[budgets.budget_year.eq(current_year)] if not budgets.empty else pd.DataFrame()
    checks["current_year_budget_missing"] = int(current_budget.empty)
    checks["fy_plan_bridge_missing"] = int(fy_bridge.empty)
    latest_contract = contract_schedule[contract_schedule.month.eq(end_month)] if not contract_schedule.empty else pd.DataFrame()
    stale_contract_rows = int((latest_contract.months_to_service < -3).sum()) if not latest_contract.empty else 0
    checks["stale_contract_liability_rows"] = stale_contract_rows
    checks["passed"] = bool(
        checks.get("passed", False)
        and wc_checks["passed"]
        and contract_ar_checks["passed"]
        and contract_checks["passed"]
        and provision_checks["passed"]
        and ap_checks["passed"]
        and absorption_checks["passed"]
        and budget_checks["passed"]
        and checks["current_year_budget_missing"] == 0
        and checks["fy_plan_bridge_missing"] == 0
        and stale_contract_rows == 0
    )
    if not checks["passed"]:
        raise RuntimeError(f"Contract-liability close controls failed: {checks}")

    # Persist rebuilt finance outputs.
    _write_gzip_csv(journal, "data/runtime/journal.csv.gz")
    journal_sample = pd.concat([
        journal.head(4500),
        journal[journal.journal_type.isin(["customer_advance", "contract_liability_application"])].head(250),
        provision_journal.head(250),
    ], ignore_index=True).drop_duplicates()
    _write_csv(journal_sample, "data/processed/journal_sample.csv")
    _write_csv(chart_of_accounts_with_contracts(), "data/processed/chart_of_accounts.csv")
    _write_csv(legal, "data/processed/legal_pnl.csv")
    _write_csv(legal_bs, "data/processed/legal_balance_sheet.csv")
    _write_csv(group_bs, "data/processed/balance_sheet.csv")
    _write_csv(cf, "data/processed/cash_flow.csv")
    _write_csv(management, "data/processed/management_pnl.csv")
    _write_csv(wc, "data/processed/working_capital.csv")
    _write_csv(ar_aging, "data/processed/ar_aging.csv")
    _write_csv(credit_loss, "data/processed/credit_loss_allowance.csv")
    _write_csv(inventory_provision, "data/processed/inventory_provision.csv")
    _write_csv(provision_journal, "data/processed/provision_journal.csv")
    _write_csv(provision_summary, "data/processed/provision_summary.csv")
    _write_csv(contract_schedule, "data/processed/contract_liabilities.csv")
    _write_csv(commitments, "data/processed/customer_advances.csv")
    _write_csv(contract_summary, "data/processed/contract_liability_summary.csv")
    _write_csv(ap_aging, "data/processed/ap_aging.csv")
    _write_csv(ap_summary, "data/processed/ap_aging_summary.csv")
    _write_csv(concentration, "data/processed/supplier_concentration.csv")
    _write_csv(suppliers, "data/processed/suppliers.csv")
    _write_csv(bridge, "data/processed/consolidation_bridge.csv")
    _write_csv(budgets, "data/processed/annual_budget.csv")
    _write_csv(performance, "data/processed/budget_performance.csv")
    _write_csv(fy_bridge, "data/processed/fy_plan_bridge.csv")

    pnl = management.groupby("month", as_index=False).agg(
        revenue=("revenue", "sum"),
        marginal_contribution=("marginal_contribution", "sum"),
        gross_profit=("gross_profit", "sum"),
        opex=("opex", "sum"),
        depreciation=("depreciation", "sum"),
        ebit=("ebit", "sum"),
        interest=("interest", "sum"),
        tax=("tax", "sum"),
        net_income=("net_income", "sum"),
        factory_absorption_variance=("factory_absorption_variance", "sum"),
        inventory_provision_expense=("inventory_provision_expense", "sum"),
        credit_loss_expense=("credit_loss_expense", "sum"),
    )
    _write_csv(pnl, "data/processed/pnl.csv")
    with open("data/processed/validation.json", "w", encoding="utf-8") as handle:
        json.dump(checks, handle, indent=2)

    # Update only the views affected by customer settlement / asset quality / planning.
    with open("web/data/dashboard.json", "r", encoding="utf-8") as handle:
        dashboard = json.load(handle)
    monthly = _group_management(management)
    latest_division = management[management.month.eq(end_month)].groupby("division", as_index=False).agg(
        revenue=("revenue", "sum"),
        marginal_contribution=("marginal_contribution", "sum"),
        gross_profit=("gross_profit", "sum"),
        ebit=("ebit", "sum"),
        factory_absorption_variance=("factory_absorption_variance", "sum"),
        inventory_provision_expense=("inventory_provision_expense", "sum"),
        credit_loss_expense=("credit_loss_expense", "sum"),
    )
    ar_summary = ar_aging_summary(ar_aging)
    inv_summary = inventory_aging_summary(inventory_aging)
    latest_ar = ar_aging[ar_aging.month.eq(end_month)].sort_values(["overdue_ar", "total_ar"], ascending=False).head(60) if not ar_aging.empty else pd.DataFrame()
    latest_ecl = credit_loss[credit_loss.month.eq(end_month)].sort_values("credit_loss_allowance", ascending=False).head(60) if not credit_loss.empty else pd.DataFrame()
    latest_inv = inventory_provision[inventory_provision.month.eq(end_month)].sort_values("inventory_provision", ascending=False).head(80) if not inventory_provision.empty else pd.DataFrame()
    latest_ap = ap_aging[ap_aging.month.eq(end_month)].sort_values(["overdue_ap", "total_ap"], ascending=False).head(80) if not ap_aging.empty else pd.DataFrame()
    inv_family = _inventory_family_summary(inventory_aging, end_month)
    perf_scope = performance[performance.budget_year.eq(current_year)] if not performance.empty else performance

    dashboard["meta"]["version"] = VERSION
    dashboard["actual"] = base_engine._records(monthly)
    dashboard["management_detail"] = base_engine._records(management)
    dashboard["division"] = base_engine._records(latest_division)
    dashboard["working_capital"] = base_engine._records(wc)
    dashboard["ar_aging_summary"] = base_engine._records(ar_summary)
    dashboard["ar_customer_aging"] = base_engine._records(latest_ar)
    dashboard["credit_loss_detail"] = base_engine._records(latest_ecl)
    dashboard["inventory_aging_summary"] = base_engine._records(inv_summary)
    dashboard["inventory_provision_detail"] = base_engine._records(latest_inv)
    dashboard["inventory_family_aging"] = base_engine._records(inv_family)
    dashboard["balance_sheet"] = base_engine._records(group_bs)
    dashboard["cash_flow"] = base_engine._records(_group_cash_flow(cf))
    dashboard["cash_flow_detail"] = base_engine._records(cf)
    dashboard["provision_summary"] = base_engine._records(provision_summary)
    dashboard["contract_liability_summary"] = base_engine._records(contract_summary)
    dashboard["contract_liability_detail"] = base_engine._records(
        latest_contract.sort_values("contract_liability", ascending=False).head(100)
    ) if not latest_contract.empty else []
    dashboard["customer_advances"] = base_engine._records(
        commitments[commitments.month.eq(end_month)].sort_values("advance_amount", ascending=False).head(100)
    ) if not commitments.empty else []
    dashboard["ap_aging_summary"] = base_engine._records(ap_summary)
    dashboard["ap_supplier_aging"] = base_engine._records(latest_ap)
    dashboard["supplier_concentration"] = base_engine._records(concentration.head(100)) if not concentration.empty else []
    dashboard["annual_budget"] = base_engine._records(current_budget)
    dashboard["budget_performance"] = base_engine._records(perf_scope)
    dashboard["fy_plan_bridge"] = base_engine._records(fy_bridge)
    dashboard["commentary"] = commentary
    dashboard["validation"] = checks
    with open("web/data/dashboard.json", "w", encoding="utf-8") as handle:
        json.dump(dashboard, handle, separators=(",", ":"), allow_nan=False)

    with open("web/data/manifest.json", "r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    contract_values = contract_summary[contract_summary.month.eq(end_month)]
    contract_values = contract_values.iloc[0].to_dict() if not contract_values.empty else {}
    latest_bs = group_bs[group_bs.month.eq(end_month)]
    latest_bs_values = latest_bs.iloc[0].to_dict() if not latest_bs.empty else {}
    latest_ecl_total = float(credit_loss.loc[credit_loss.month.eq(end_month), "credit_loss_allowance"].sum()) if not credit_loss.empty else 0.0
    agg = fy_bridge.select_dtypes(include="number").sum(numeric_only=True) if not fy_bridge.empty else pd.Series(dtype=float)

    manifest["version"] = VERSION
    manifest["journal_rows"] = int(len(journal))
    manifest["ar_aging_rows"] = int(len(ar_aging))
    manifest["latest_overdue_ar"] = round(float(latest_ar.overdue_ar.sum()), 2) if not latest_ar.empty else 0.0
    manifest["latest_credit_loss_allowance"] = round(latest_ecl_total, 2)
    manifest["latest_contract_liabilities"] = round(float(contract_values.get("contract_liabilities", 0.0)), 2)
    manifest["latest_software_contract_liabilities"] = round(float(contract_values.get("software_contract_liabilities", 0.0)), 2)
    manifest["latest_events_contract_liabilities"] = round(float(contract_values.get("events_contract_liabilities", 0.0)), 2)
    manifest["latest_customer_advances"] = round(float(contract_values.get("customer_advances", 0.0)), 2)
    manifest["latest_cash"] = round(float(latest_bs_values.get("cash", 0.0)), 2)
    manifest["latest_net_trade_receivables"] = round(float(latest_bs_values.get("trade_receivables", 0.0)), 2)
    manifest["latest_operating_nwc"] = round(float(wc.loc[wc.month.eq(end_month), "operating_net_working_capital"].sum()), 2) if not wc.empty else 0.0
    manifest["fy_budget_revenue"] = round(float(agg.get("fy_budget_revenue", 0.0)), 2)
    manifest["fy_budget_ebit"] = round(float(agg.get("fy_budget_ebit", 0.0)), 2)
    manifest["latest_fy_revenue"] = round(float(agg.get("latest_fy_revenue", 0.0)), 2)
    manifest["latest_fy_ebit"] = round(float(agg.get("latest_fy_ebit", 0.0)), 2)
    manifest["validation"] = checks
    with open("web/data/manifest.json", "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)

    return result.__class__(
        result.end_month,
        result.actual_months,
        result.forecast_months,
        result.operational_rows,
        len(journal),
        result.forecast_rows,
        True,
    )
