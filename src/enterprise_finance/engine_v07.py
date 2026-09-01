from __future__ import annotations

import gzip
import json
from pathlib import Path

import pandas as pd

from . import engine as base_engine
from .accounting import cash_flow, validate_factory_absorption_accounting
from .engine_v06 import build as build_v06
from .factory_absorption import hardware_factory_accounting_schedule
from .operating_schedules import (
    events_backlog_schedule,
    software_subscription_schedule,
    spare_parts_schedule,
    validate_operating_schedules,
)
from .provisions import (
    append_provision_journals,
    build_credit_loss_schedule,
    build_inventory_provision_schedule,
    chart_of_accounts_with_provisions,
    group_balance_sheet_with_provisions,
    legal_balance_sheet_with_provisions,
    legal_pnl_with_provisions,
    management_pnl_with_provisions,
    provision_monthly_summary,
    validate_provisions,
)
from .reporting import consolidation_bridge, management_commentary, validate_all, working_capital
from .working_capital_detail import validate_working_capital_schedules


VERSION = "0.7.0"


def _read_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


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


def _enrich_working_capital(wc: pd.DataFrame, group_bs: pd.DataFrame) -> pd.DataFrame:
    asset_quality = group_bs[[
        "month", "trade_receivables_gross", "credit_loss_allowance", "trade_receivables",
        "inventory_gross", "inventory_provision", "inventory",
    ]].copy()
    asset_quality = asset_quality.rename(columns={
        "trade_receivables": "net_trade_receivables",
        "inventory": "net_inventory",
    })
    out = wc.drop(columns=[c for c in ["trade_receivables", "inventory"] if c in wc.columns]).merge(asset_quality, on="month", how="left")
    out["trade_receivables"] = out.net_trade_receivables
    out["inventory"] = out.net_inventory
    out["gross_net_working_capital"] = out.trade_receivables_gross + out.inventory_gross - out.trade_payables
    out["provision_adjusted_net_working_capital"] = out.net_working_capital
    return out


def _working_capital_with_asset_quality(group_bs: pd.DataFrame, management: pd.DataFrame) -> pd.DataFrame:
    # ECL is a non-cash accounting charge, not supplier spend. Excluding it from
    # the DPO denominator keeps supplier-payment efficiency economically clean.
    wc_management = management.copy()
    if "credit_loss_expense" in wc_management.columns:
        wc_management["opex"] = wc_management.opex - wc_management.credit_loss_expense
    return _enrich_working_capital(working_capital(group_bs, wc_management), group_bs)


def build(end_month: str, config_path: str = "config/company.yml", allow_live_macro: bool = True):
    """Run v0.6 and then post book provisions from reconciled aging schedules.

    Provision movements are supplemental book adjustments. They are intentionally
    treated as non-deductible in the current synthetic tax model, so no invented
    jurisdiction-specific tax benefit is created.
    """
    result = build_v06(end_month, config_path=config_path, allow_live_macro=allow_live_macro)
    config = base_engine.load_config(config_path)

    operations = _read_csv("data/runtime/operational.csv.gz")
    journal_pre_provision = _read_csv("data/runtime/journal.csv.gz")
    products = _read_csv("data/processed/products.csv")
    ar_aging = _read_csv("data/processed/ar_aging.csv")
    inventory_aging = _read_csv("data/processed/inventory_aging.csv")
    factory = _read_csv("data/processed/factory.csv")
    latest_fc = _read_csv("data/processed/forecast.csv")
    forecasts = _read_csv("data/processed/forecast_vintages.csv")

    credit_loss = build_credit_loss_schedule(ar_aging, config)
    inventory_provision = build_inventory_provision_schedule(inventory_aging, config)
    journal, provision_journal = append_provision_journals(journal_pre_provision, credit_loss, inventory_provision)

    legal = legal_pnl_with_provisions(journal)
    legal_bs = legal_balance_sheet_with_provisions(journal)
    group_bs = group_balance_sheet_with_provisions(legal_bs, float(config["transfer_pricing"]["manufacturing_cost_plus"]))
    cf = cash_flow(journal)
    management = management_pnl_with_provisions(operations, journal, set(config["factories"]))
    # Provision rows explain Gross Profit directly; they are not standard physical cost for DIO.
    management["fixed_production_cost"] = management.fixed_production_cost - management.inventory_provision_expense
    wc = _working_capital_with_asset_quality(group_bs, management)

    software_detail, software_summary = software_subscription_schedule(operations, products)
    events_schedule = events_backlog_schedule(operations, products)
    factory_economics, hardware_mix = hardware_factory_accounting_schedule(operations, products, factory, config)
    spare_parts_economics = spare_parts_schedule(operations, inventory_aging)
    bridge = consolidation_bridge(legal, management)
    commentary = management_commentary(management, wc, cf, latest_fc, end_month)
    provision_summary = provision_monthly_summary(credit_loss, inventory_provision, journal)

    checks = validate_all(journal, legal_bs, group_bs, cf, bridge)
    wc_checks = validate_working_capital_schedules(journal, ar_aging, inventory_aging)
    operating_checks = validate_operating_schedules(
        operations, software_detail, software_summary, events_schedule, factory_economics, spare_parts_economics
    )
    absorption_checks = validate_factory_absorption_accounting(factory, journal)
    provision_checks = validate_provisions(journal, credit_loss, inventory_provision)
    for source in [wc_checks, operating_checks, absorption_checks, provision_checks]:
        checks.update({key: value for key, value in source.items() if key != "passed"})

    if forecasts.empty:
        lookahead_errors = 0
    else:
        lookahead_errors = int((pd.PeriodIndex(forecasts.month, freq="M") <= pd.PeriodIndex(forecasts.vintage, freq="M")).sum())
    checks["forecast_lookahead_errors"] = lookahead_errors
    checks["catalog_product_count"] = int(len(products))
    checks["catalog_family_count"] = int(products[["division", "product_family"]].drop_duplicates().shape[0])
    checks["sold_product_count"] = int(operations.product.nunique())
    checks["passed"] = bool(
        checks["passed"]
        and wc_checks["passed"]
        and operating_checks["passed"]
        and absorption_checks["passed"]
        and provision_checks["passed"]
        and lookahead_errors == 0
        and checks["catalog_product_count"] >= 200
        and checks["sold_product_count"] >= 150
    )
    if not checks["passed"]:
        raise RuntimeError(f"Provision close controls failed: {checks}")

    _write_gzip_csv(journal, "data/runtime/journal.csv.gz")
    if provision_journal.empty:
        _write_csv(provision_journal, "data/processed/provision_journal.csv")
        journal_sample = journal.head(5000)
    else:
        _write_csv(provision_journal, "data/processed/provision_journal.csv")
        journal_sample = pd.concat([journal.head(4800), provision_journal.head(200)], ignore_index=True)
    _write_csv(journal_sample, "data/processed/journal_sample.csv")
    _write_csv(chart_of_accounts_with_provisions(), "data/processed/chart_of_accounts.csv")
    _write_csv(legal, "data/processed/legal_pnl.csv")
    _write_csv(legal_bs, "data/processed/legal_balance_sheet.csv")
    _write_csv(group_bs, "data/processed/balance_sheet.csv")
    _write_csv(cf, "data/processed/cash_flow.csv")
    _write_csv(management, "data/processed/management_pnl.csv")
    _write_csv(wc, "data/processed/working_capital.csv")
    _write_csv(credit_loss, "data/processed/credit_loss_allowance.csv")
    _write_csv(inventory_provision, "data/processed/inventory_provision.csv")
    _write_csv(provision_summary, "data/processed/provision_summary.csv")
    _write_csv(bridge, "data/processed/consolidation_bridge.csv")

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
    latest_ecl = credit_loss[credit_loss.month.eq(end_month)].sort_values("credit_loss_allowance", ascending=False).head(60)
    latest_inv = inventory_provision[inventory_provision.month.eq(end_month)].sort_values("inventory_provision", ascending=False).head(80)

    dashboard["meta"]["version"] = VERSION
    dashboard["actual"] = base_engine._records(monthly)
    dashboard["management_detail"] = base_engine._records(management)
    dashboard["division"] = base_engine._records(latest_division)
    dashboard["working_capital"] = base_engine._records(wc)
    dashboard["balance_sheet"] = base_engine._records(group_bs)
    dashboard["cash_flow_detail"] = base_engine._records(cf)
    dashboard["provision_summary"] = base_engine._records(provision_summary)
    dashboard["credit_loss_detail"] = base_engine._records(latest_ecl)
    dashboard["inventory_provision_detail"] = base_engine._records(latest_inv)
    dashboard["commentary"] = commentary
    dashboard["validation"] = checks
    with open("web/data/dashboard.json", "w", encoding="utf-8") as handle:
        json.dump(dashboard, handle, separators=(",", ":"), allow_nan=False)

    with open("web/data/manifest.json", "r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    latest_provision = provision_summary[provision_summary.month.eq(end_month)]
    if latest_provision.empty:
        values = {}
    else:
        values = latest_provision.iloc[0].to_dict()
    manifest["version"] = VERSION
    manifest["journal_rows"] = int(len(journal))
    manifest["provision_journal_rows"] = int(len(provision_journal))
    manifest["latest_credit_loss_allowance"] = round(float(values.get("credit_loss_allowance", 0.0)), 2)
    manifest["latest_inventory_provision"] = round(float(values.get("inventory_provision", 0.0)), 2)
    manifest["latest_net_trade_receivables"] = round(float(values.get("net_ar", 0.0)), 2)
    manifest["latest_net_inventory"] = round(float(values.get("net_inventory", 0.0)), 2)
    manifest["latest_credit_loss_expense"] = round(float(values.get("credit_loss_expense", 0.0)), 2)
    manifest["latest_inventory_provision_expense"] = round(float(values.get("inventory_provision_expense", 0.0)), 2)
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
