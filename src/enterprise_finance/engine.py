from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import gzip
import json

import pandas as pd
import yaml

from .accounting import build_accounting, balance_sheet, cash_flow, chart_of_accounts, legal_pnl
from .forecasting import build_forecast_vintages, forecast_accuracy, latest_forecast
from .macro import build_macro, source_manifest
from .model import simulate_operations
from .operating_schedules import (
    events_backlog_schedule,
    hardware_factory_schedule,
    software_subscription_schedule,
    spare_parts_schedule,
    validate_operating_schedules,
)
from .reporting import consolidation_bridge, group_balance_sheet, management_commentary, management_pnl, price_volume_mix, profitability, validate_all, working_capital
from .working_capital_detail import (
    ar_aging_summary,
    build_ar_aging,
    build_inventory_aging,
    inventory_aging_summary,
    validate_working_capital_schedules,
)


@dataclass(frozen=True)
class BuildResult:
    end_month: str
    actual_months: int
    forecast_months: int
    operational_rows: int
    journal_rows: int
    forecast_rows: int
    validation_passed: bool


def load_config(path: str | Path = "config/company.yml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def month_range(end_month: str, periods: int) -> pd.PeriodIndex:
    end = pd.Period(end_month, freq="M")
    return pd.period_range(end=end, periods=periods, freq="M")


def _records(df: pd.DataFrame) -> list[dict]:
    if df.empty:
        return []
    clean = df.copy()
    for col in clean.select_dtypes(include=["float"]).columns:
        clean[col] = clean[col].round(4)
    clean = clean.astype(object).where(pd.notna(clean), None)
    return clean.to_dict(orient="records")


def _write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def _write_gzip_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as f:
        df.to_csv(f, index=False)


def _hierarchy_summaries(product_profit: pd.DataFrame, products: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    family = product_profit.groupby(["division", "product_family"], as_index=False).agg(
        revenue=("revenue", "sum"),
        marginal_contribution=("marginal_contribution", "sum"),
        gross_profit=("gross_profit", "sum"),
        operating_contribution=("operating_contribution", "sum"),
        sku_count=("product", "nunique"),
    )
    family["gross_margin_pct"] = family.gross_profit / family.revenue.replace(0, pd.NA)
    family["mc_pct"] = family.marginal_contribution / family.revenue.replace(0, pd.NA)

    quality = product_profit.groupby(["division", "quality_tier"], as_index=False).agg(
        revenue=("revenue", "sum"),
        marginal_contribution=("marginal_contribution", "sum"),
        gross_profit=("gross_profit", "sum"),
        operating_contribution=("operating_contribution", "sum"),
        sku_count=("product", "nunique"),
    )
    quality["gross_margin_pct"] = quality.gross_profit / quality.revenue.replace(0, pd.NA)
    quality["mc_pct"] = quality.marginal_contribution / quality.revenue.replace(0, pd.NA)

    catalog = products.groupby(["division", "product_family", "product_subfamily", "quality_tier"], as_index=False).agg(
        sku_count=("product", "nunique"),
        initially_active_skus=("initial_active", "sum"),
    )
    return family.fillna(0.0), quality.fillna(0.0), catalog


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


def _group_software_summary(software_summary: pd.DataFrame) -> pd.DataFrame:
    if software_summary.empty:
        return pd.DataFrame()
    out = software_summary.groupby("month", as_index=False).agg(
        revenue=("revenue", "sum"),
        services_revenue=("services_revenue", "sum"),
        opening_mrr=("opening_mrr", "sum"),
        ending_mrr=("ending_mrr", "sum"),
        new_mrr=("new_mrr", "sum"),
        expansion_mrr=("expansion_mrr", "sum"),
        contraction_mrr=("contraction_mrr", "sum"),
        churn_mrr=("churn_mrr", "sum"),
        arr=("arr", "sum"),
        new_arr=("new_arr", "sum"),
        expansion_arr=("expansion_arr", "sum"),
        contraction_arr=("contraction_arr", "sum"),
        churn_arr=("churn_arr", "sum"),
    )
    out["recurring_revenue"] = out.ending_mrr
    out["recurring_mix"] = out.recurring_revenue / out.revenue.replace(0, pd.NA)
    out["nrr"] = (out.opening_mrr + out.expansion_mrr - out.contraction_mrr - out.churn_mrr) / out.opening_mrr.replace(0, pd.NA)
    out["grr"] = (out.opening_mrr - out.contraction_mrr - out.churn_mrr) / out.opening_mrr.replace(0, pd.NA)
    return out.fillna(0.0)


def _group_events_summary(events: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return pd.DataFrame()
    out = events.groupby("month", as_index=False).agg(
        opening_backlog=("opening_backlog", "sum"),
        bookings=("bookings", "sum"),
        recognized_revenue=("recognized_revenue", "sum"),
        ending_backlog=("ending_backlog", "sum"),
        project_units=("project_units", "sum"),
    )
    out["book_to_bill"] = out.bookings / out.recognized_revenue.replace(0, pd.NA)
    trailing = out.recognized_revenue.rolling(3, min_periods=1).mean()
    out["backlog_coverage_months"] = out.ending_backlog / trailing.replace(0, pd.NA)
    return out.fillna(0.0)


def _dashboard_payload(*, end_month: str, management: pd.DataFrame, group_bs: pd.DataFrame, cf: pd.DataFrame, wc: pd.DataFrame, ar_aging: pd.DataFrame, inventory_aging: pd.DataFrame, software_detail: pd.DataFrame, software_summary: pd.DataFrame, events_schedule: pd.DataFrame, factory_economics: pd.DataFrame, hardware_mix: pd.DataFrame, spare_parts_economics: pd.DataFrame, latest_fc: pd.DataFrame, product_profit: pd.DataFrame, customer_profit: pd.DataFrame, products: pd.DataFrame, pvm: pd.DataFrame, intercompany: pd.DataFrame, factory: pd.DataFrame, capex: pd.DataFrame, portfolio_events: pd.DataFrame, forecast_acc: pd.DataFrame, commentary: list[dict], checks: dict, sources: dict) -> dict:
    monthly = management.groupby("month", as_index=False).agg(
        revenue=("revenue", "sum"), marginal_contribution=("marginal_contribution", "sum"), gross_profit=("gross_profit", "sum"),
        opex=("opex", "sum"), depreciation=("depreciation", "sum"), ebit=("ebit", "sum"), net_income=("net_income", "sum"),
    )
    latest_division = management[management.month.eq(end_month)].groupby("division", as_index=False).agg(
        revenue=("revenue", "sum"), marginal_contribution=("marginal_contribution", "sum"), gross_profit=("gross_profit", "sum"), ebit=("ebit", "sum")
    )
    cf_group = cf.groupby("month", as_index=False).agg(
        operating_cash_flow=("operating_cash_flow", "sum"), investing_cash_flow=("investing_cash_flow", "sum"),
        financing_cash_flow=("financing_cash_flow", "sum"), free_cash_flow=("free_cash_flow", "sum"), net_cash_movement=("net_cash_movement", "sum"),
    )
    fc_group = latest_fc.groupby(["month", "horizon_month", "scenario"], as_index=False).agg(
        revenue_forecast=("revenue_forecast", "sum"), gross_profit_forecast=("gross_profit_forecast", "sum"),
        marginal_contribution_forecast=("marginal_contribution_forecast", "sum"), opex_forecast=("opex_forecast", "sum"),
    )
    fc_group["ebit_forecast"] = fc_group.gross_profit_forecast - fc_group.opex_forecast
    acc_summary = forecast_acc.groupby("horizon_month", as_index=False).agg(mape=("abs_pct_error", "mean"), bias=("bias_pct", "mean"), observations=("error", "size")) if not forecast_acc.empty else pd.DataFrame()
    ic_month = intercompany.groupby("month", as_index=False).agg(intercompany_sales=("invoice", "sum"), manufacturing_cost=("manufacturing_cost", "sum"), transfer_pricing_markup=("markup", "sum")) if not intercompany.empty else pd.DataFrame()
    family_profit, quality_profit, catalog_summary = _hierarchy_summaries(product_profit, products)
    ar_summary = ar_aging_summary(ar_aging)
    inv_summary = inventory_aging_summary(inventory_aging)
    latest_ar = ar_aging[ar_aging.month.eq(end_month)].sort_values(["overdue_ar", "total_ar"], ascending=False).head(50) if not ar_aging.empty else pd.DataFrame()
    latest_inventory = inventory_aging[inventory_aging.month.eq(end_month)].sort_values(["obsolescence_risk_value", "slow_moving_value", "inventory_value"], ascending=False).head(80) if not inventory_aging.empty else pd.DataFrame()
    inv_family = _inventory_family_summary(inventory_aging, end_month)
    sw_group = _group_software_summary(software_summary)
    evt_group = _group_events_summary(events_schedule)

    return {
        "meta": {
            "company": "Aureon Systems Group",
            "end_month": end_month,
            "currency": "EUR",
            "version": "0.5.0",
            "catalog_products": int(len(products)),
            "product_families": int(products[["division", "product_family"]].drop_duplicates().shape[0]),
        },
        "actual": _records(monthly),
        "management_detail": _records(management),
        "division": _records(latest_division),
        "working_capital": _records(wc),
        "ar_aging_summary": _records(ar_summary),
        "ar_customer_aging": _records(latest_ar),
        "inventory_aging_summary": _records(inv_summary),
        "inventory_sku_aging": _records(latest_inventory),
        "inventory_family_aging": _records(inv_family.sort_values(["division", "inventory_value"], ascending=[True, False])) if not inv_family.empty else [],
        "software_summary": _records(sw_group),
        "software_entity_summary": _records(software_summary[software_summary.month >= str(pd.Period(end_month, freq="M") - 11)]),
        "software_subscription_detail": _records(software_detail[software_detail.month.eq(end_month)].sort_values("arr", ascending=False).head(80)) if not software_detail.empty else [],
        "events_summary": _records(evt_group),
        "events_backlog_detail": _records(events_schedule[events_schedule.month.eq(end_month)].sort_values("ending_backlog", ascending=False)) if not events_schedule.empty else [],
        "hardware_factory_economics": _records(factory_economics[factory_economics.month >= str(pd.Period(end_month, freq="M") - 11)]),
        "hardware_mix": _records(hardware_mix[hardware_mix.month.eq(end_month)].sort_values(["source_factory", "units"], ascending=[True, False])) if not hardware_mix.empty else [],
        "spare_parts_economics": _records(spare_parts_economics[spare_parts_economics.month >= str(pd.Period(end_month, freq="M") - 23)]),
        "cash_flow": _records(cf_group),
        "cash_flow_detail": _records(cf),
        "balance_sheet": _records(group_bs),
        "forecast": _records(fc_group),
        "forecast_detail": _records(latest_fc),
        "forecast_accuracy": _records(acc_summary),
        "product_profitability": _records(product_profit.sort_values("operating_contribution")),
        "product_family_profitability": _records(family_profit.sort_values(["division", "revenue"], ascending=[True, False])),
        "quality_tier_profitability": _records(quality_profit.sort_values(["division", "quality_tier"])),
        "product_catalog": _records(catalog_summary),
        "customer_profitability": _records(customer_profit.sort_values("operating_contribution").head(40)),
        "pvm": _records(pvm),
        "intercompany": _records(ic_month),
        "factory": _records(factory[factory.month >= str(pd.Period(end_month, freq="M") - 11)]),
        "capex": _records(capex),
        "portfolio_events": _records(portfolio_events.tail(50)),
        "commentary": commentary,
        "validation": checks,
        "sources": sources,
    }


def build(end_month: str, config_path: str = "config/company.yml", allow_live_macro: bool = True) -> BuildResult:
    config = load_config(config_path)
    actual_months = int(config["group"]["actual_months"])
    forecast_months = int(config["group"]["forecast_months"])
    months = month_range(end_month, actual_months)
    macro = build_macro(months, int(config["group"]["seed"]), allow_live=allow_live_macro and bool(config["group"].get("live_macro", True)))
    simulation = simulate_operations(config, months, macro)
    accounting = build_accounting(config, months, macro, simulation.operations)

    legal = legal_pnl(accounting.journal)
    legal_bs = balance_sheet(accounting.journal)
    cf = cash_flow(accounting.journal)
    management = management_pnl(simulation.operations, accounting.journal)
    group_bs = group_balance_sheet(legal_bs, float(config["transfer_pricing"]["manufacturing_cost_plus"]))
    wc = working_capital(group_bs, management)

    ar_aging = build_ar_aging(accounting.journal, simulation.customers, config)
    inventory_aging = build_inventory_aging(accounting.journal, simulation.operations, simulation.products, config)

    software_detail, software_summary = software_subscription_schedule(simulation.operations, simulation.products)
    events_schedule = events_backlog_schedule(simulation.operations, simulation.products)
    factory_economics, hardware_mix = hardware_factory_schedule(simulation.operations, simulation.products, accounting.factory, config)
    spare_parts_economics = spare_parts_schedule(simulation.operations, inventory_aging)

    product_profit, customer_profit = profitability(simulation.operations, end_month)
    hierarchy_cols = ["product", "name", "product_family", "product_subfamily", "product_type", "quality_tier", "quality_score", "generation", "strategic_role"]
    product_profit = product_profit.merge(simulation.products[hierarchy_cols], on="product", how="left")
    customer_profit = customer_profit.merge(simulation.customers[["customer", "customer_name"]].drop_duplicates("customer"), on="customer", how="left")
    pvm = price_volume_mix(simulation.operations, end_month)
    bridge = consolidation_bridge(legal, management)

    forecasts = build_forecast_vintages(config, simulation.operations, months)
    latest_fc = latest_forecast(forecasts, end_month)
    accuracy = forecast_accuracy(forecasts, simulation.operations, end_month)
    commentary = management_commentary(management, wc, cf, latest_fc, end_month)

    checks = validate_all(accounting.journal, legal_bs, group_bs, cf, bridge)
    schedule_checks = validate_working_capital_schedules(accounting.journal, ar_aging, inventory_aging)
    operating_checks = validate_operating_schedules(
        simulation.operations, software_detail, software_summary, events_schedule, factory_economics, spare_parts_economics
    )
    checks.update({k: v for k, v in schedule_checks.items() if k != "passed"})
    checks.update({k: v for k, v in operating_checks.items() if k != "passed"})
    lookahead_errors = int((pd.PeriodIndex(forecasts.month, freq="M") <= pd.PeriodIndex(forecasts.vintage, freq="M")).sum()) if not forecasts.empty else 0
    checks["forecast_lookahead_errors"] = lookahead_errors
    checks["catalog_product_count"] = int(len(simulation.products))
    checks["catalog_family_count"] = int(simulation.products[["division", "product_family"]].drop_duplicates().shape[0])
    checks["sold_product_count"] = int(simulation.operations["product"].nunique())
    checks["passed"] = bool(
        checks["passed"] and schedule_checks["passed"] and operating_checks["passed"]
        and lookahead_errors == 0 and checks["catalog_product_count"] >= 200 and checks["sold_product_count"] >= 150
    )
    if not checks["passed"]:
        raise RuntimeError(f"Financial controls failed: {checks}")

    out = Path("data/processed")
    runtime = Path("data/runtime")
    out.mkdir(parents=True, exist_ok=True)
    runtime.mkdir(parents=True, exist_ok=True)

    _write_csv(chart_of_accounts(), out / "chart_of_accounts.csv")
    _write_csv(macro, out / "macro.csv")
    _write_csv(simulation.products, out / "products.csv")
    _write_csv(simulation.customers, out / "customers.csv")
    _write_csv(simulation.operations.head(5000), out / "operational_sample.csv")
    _write_gzip_csv(simulation.operations, runtime / "operational.csv.gz")
    _write_csv(simulation.portfolio_events, out / "portfolio_events.csv")
    _write_csv(accounting.journal.head(5000), out / "journal_sample.csv")
    _write_gzip_csv(accounting.journal, runtime / "journal.csv.gz")
    _write_csv(legal, out / "legal_pnl.csv")
    _write_csv(management, out / "management_pnl.csv")

    pnl = management.groupby("month", as_index=False).agg(
        revenue=("revenue", "sum"), marginal_contribution=("marginal_contribution", "sum"), gross_profit=("gross_profit", "sum"),
        opex=("opex", "sum"), depreciation=("depreciation", "sum"), ebit=("ebit", "sum"), interest=("interest", "sum"),
        tax=("tax", "sum"), net_income=("net_income", "sum"),
    )
    _write_csv(pnl, out / "pnl.csv")
    _write_csv(legal_bs, out / "legal_balance_sheet.csv")
    _write_csv(group_bs, out / "balance_sheet.csv")
    _write_csv(cf, out / "cash_flow.csv")
    _write_csv(wc, out / "working_capital.csv")
    _write_csv(ar_aging, out / "ar_aging.csv")
    _write_csv(inventory_aging, out / "inventory_aging.csv")
    _write_csv(software_summary, out / "software_subscription_summary.csv")
    _write_csv(events_schedule, out / "events_backlog.csv")
    _write_csv(factory_economics, out / "hardware_factory_economics.csv")
    _write_csv(hardware_mix, out / "hardware_production_mix.csv")
    _write_csv(spare_parts_economics, out / "spare_parts_economics.csv")
    _write_csv(accounting.intercompany, out / "intercompany.csv")
    _write_csv(accounting.factory, out / "factory.csv")
    _write_csv(accounting.capex, out / "capex.csv")
    _write_csv(product_profit, out / "product_profitability.csv")
    _write_csv(customer_profit, out / "customer_profitability.csv")
    _write_csv(pvm, out / "price_volume_mix.csv")
    _write_csv(bridge, out / "consolidation_bridge.csv")
    _write_csv(forecasts, out / "forecast_vintages.csv")
    _write_csv(latest_fc, out / "forecast.csv")
    _write_csv(accuracy, out / "forecast_accuracy.csv")

    sources = source_manifest(macro)
    with open(out / "validation.json", "w", encoding="utf-8") as f:
        json.dump(checks, f, indent=2)
    with open(out / "source_manifest.json", "w", encoding="utf-8") as f:
        json.dump(sources, f, indent=2)

    payload = _dashboard_payload(
        end_month=end_month, management=management, group_bs=group_bs, cf=cf, wc=wc,
        ar_aging=ar_aging, inventory_aging=inventory_aging,
        software_detail=software_detail, software_summary=software_summary, events_schedule=events_schedule,
        factory_economics=factory_economics, hardware_mix=hardware_mix, spare_parts_economics=spare_parts_economics,
        latest_fc=latest_fc, product_profit=product_profit, customer_profit=customer_profit, products=simulation.products, pvm=pvm,
        intercompany=accounting.intercompany, factory=accounting.factory, capex=accounting.capex,
        portfolio_events=simulation.portfolio_events, forecast_acc=accuracy, commentary=commentary, checks=checks, sources=sources,
    )
    web = Path("web/data")
    web.mkdir(parents=True, exist_ok=True)
    with open(web / "dashboard.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"), allow_nan=False)

    latest_ar = ar_aging[ar_aging.month.eq(end_month)] if not ar_aging.empty else pd.DataFrame()
    latest_inv = inventory_aging[inventory_aging.month.eq(end_month)] if not inventory_aging.empty else pd.DataFrame()
    latest_sw = _group_software_summary(software_summary)
    latest_sw = latest_sw[latest_sw.month.eq(end_month)] if not latest_sw.empty else pd.DataFrame()
    latest_evt = _group_events_summary(events_schedule)
    latest_evt = latest_evt[latest_evt.month.eq(end_month)] if not latest_evt.empty else pd.DataFrame()
    latest_sp = spare_parts_economics[spare_parts_economics.month.eq(end_month)] if not spare_parts_economics.empty else pd.DataFrame()
    manifest = {
        "end_month": end_month,
        "actual_months": actual_months,
        "forecast_months": forecast_months,
        "catalog_products": len(simulation.products),
        "sold_products": int(simulation.operations["product"].nunique()),
        "product_families": int(simulation.products[["division", "product_family"]].drop_duplicates().shape[0]),
        "operational_rows": len(simulation.operations),
        "journal_rows": len(accounting.journal),
        "forecast_rows": len(forecasts),
        "portfolio_events": len(simulation.portfolio_events),
        "ar_aging_rows": len(ar_aging),
        "inventory_aging_rows": len(inventory_aging),
        "software_schedule_rows": len(software_detail),
        "events_backlog_rows": len(events_schedule),
        "hardware_factory_rows": len(factory_economics),
        "spare_parts_schedule_rows": len(spare_parts_economics),
        "latest_overdue_ar": round(float(latest_ar.overdue_ar.sum()), 2) if not latest_ar.empty else 0.0,
        "latest_slow_moving_inventory": round(float(latest_inv.slow_moving_value.sum()), 2) if not latest_inv.empty else 0.0,
        "latest_software_arr": round(float(latest_sw.arr.sum()), 2) if not latest_sw.empty else 0.0,
        "latest_events_backlog": round(float(latest_evt.ending_backlog.sum()), 2) if not latest_evt.empty else 0.0,
        "latest_spare_parts_installed_base": round(float(latest_sp.ending_installed_base.sum()), 2) if not latest_sp.empty else 0.0,
        "detail_retention": "full transaction and journal detail is generated reproducibly in data/runtime and not committed to git",
        "validation": checks,
    }
    with open(web / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return BuildResult(end_month, actual_months, forecast_months, len(simulation.operations), len(accounting.journal), len(forecasts), True)
