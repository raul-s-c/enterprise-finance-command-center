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
from .reporting import consolidation_bridge, group_balance_sheet, management_commentary, management_pnl, price_volume_mix, profitability, validate_all, working_capital


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


def _dashboard_payload(*, end_month: str, management: pd.DataFrame, group_bs: pd.DataFrame, cf: pd.DataFrame, wc: pd.DataFrame, latest_fc: pd.DataFrame, product_profit: pd.DataFrame, customer_profit: pd.DataFrame, pvm: pd.DataFrame, intercompany: pd.DataFrame, factory: pd.DataFrame, capex: pd.DataFrame, portfolio_events: pd.DataFrame, forecast_acc: pd.DataFrame, commentary: list[dict], checks: dict, sources: dict) -> dict:
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
    return {
        "meta": {"company": "Aureon Systems Group", "end_month": end_month, "currency": "EUR", "version": "0.2.0"},
        "actual": _records(monthly),
        "management_detail": _records(management),
        "division": _records(latest_division),
        "working_capital": _records(wc),
        "cash_flow": _records(cf_group),
        "cash_flow_detail": _records(cf),
        "balance_sheet": _records(group_bs),
        "forecast": _records(fc_group),
        "forecast_detail": _records(latest_fc),
        "forecast_accuracy": _records(acc_summary),
        "product_profitability": _records(product_profit.sort_values("operating_contribution").head(30)),
        "customer_profitability": _records(customer_profit.sort_values("operating_contribution").head(30)),
        "pvm": _records(pvm),
        "intercompany": _records(ic_month),
        "factory": _records(factory[factory.month >= str(pd.Period(end_month, freq="M") - 11)]),
        "capex": _records(capex),
        "portfolio_events": _records(portfolio_events.tail(30)),
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
    product_profit, customer_profit = profitability(simulation.operations, end_month)
    product_profit = product_profit.merge(simulation.products[["product", "name"]], on="product", how="left")
    customer_profit = customer_profit.merge(simulation.customers[["customer", "customer_name"]].drop_duplicates("customer"), on="customer", how="left")
    pvm = price_volume_mix(simulation.operations, end_month)
    bridge = consolidation_bridge(legal, management)

    forecasts = build_forecast_vintages(config, simulation.operations, months)
    latest_fc = latest_forecast(forecasts, end_month)
    accuracy = forecast_accuracy(forecasts, simulation.operations, end_month)
    commentary = management_commentary(management, wc, cf, latest_fc, end_month)

    checks = validate_all(accounting.journal, legal_bs, group_bs, cf, bridge)
    lookahead_errors = int((pd.PeriodIndex(forecasts.month, freq="M") <= pd.PeriodIndex(forecasts.vintage, freq="M")).sum()) if not forecasts.empty else 0
    checks["forecast_lookahead_errors"] = lookahead_errors
    checks["passed"] = bool(checks["passed"] and lookahead_errors == 0)
    if not checks["passed"]:
        raise RuntimeError(f"Financial controls failed: {checks}")

    out = Path("data/processed")
    out.mkdir(parents=True, exist_ok=True)
    _write_csv(chart_of_accounts(), out / "chart_of_accounts.csv")
    _write_csv(macro, out / "macro.csv")
    _write_csv(simulation.products, out / "products.csv")
    _write_csv(simulation.customers, out / "customers.csv")
    _write_csv(simulation.operations, out / "operational.csv")
    _write_csv(simulation.portfolio_events, out / "portfolio_events.csv")
    _write_csv(accounting.journal.head(5000), out / "journal_sample.csv")
    with gzip.open(out / "journal.csv.gz", "wt", encoding="utf-8", newline="") as f:
        accounting.journal.to_csv(f, index=False)
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
        end_month=end_month, management=management, group_bs=group_bs, cf=cf, wc=wc, latest_fc=latest_fc,
        product_profit=product_profit, customer_profit=customer_profit, pvm=pvm, intercompany=accounting.intercompany,
        factory=accounting.factory, capex=accounting.capex, portfolio_events=simulation.portfolio_events,
        forecast_acc=accuracy, commentary=commentary, checks=checks, sources=sources,
    )
    web = Path("web/data")
    web.mkdir(parents=True, exist_ok=True)
    with open(web / "dashboard.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"), allow_nan=False)
    manifest = {
        "end_month": end_month, "actual_months": actual_months, "forecast_months": forecast_months,
        "operational_rows": len(simulation.operations), "journal_rows": len(accounting.journal), "forecast_rows": len(forecasts),
        "portfolio_events": len(simulation.portfolio_events), "validation": checks,
    }
    with open(web / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return BuildResult(end_month, actual_months, forecast_months, len(simulation.operations), len(accounting.journal), len(forecasts), True)
