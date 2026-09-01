from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from . import engine as base_engine
from .accounting import validate_factory_absorption_accounting
from .factory_absorption import hardware_factory_accounting_schedule, management_pnl_with_factory_absorption
from .reporting import consolidation_bridge, management_commentary, working_capital


VERSION = "0.6.0"


def _read_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


def _write_csv(df: pd.DataFrame, path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def _group_management(management: pd.DataFrame) -> pd.DataFrame:
    return management.groupby("month", as_index=False).agg(
        revenue=("revenue", "sum"),
        marginal_contribution=("marginal_contribution", "sum"),
        gross_profit=("gross_profit", "sum"),
        opex=("opex", "sum"),
        depreciation=("depreciation", "sum"),
        ebit=("ebit", "sum"),
        net_income=("net_income", "sum"),
    )


def build(end_month: str, config_path: str = "config/company.yml", allow_live_macro: bool = True):
    """Run the proven base close and enrich it with v0.6 factory accounting.

    The base engine already creates the full ledger, statements, Working Capital,
    divisional schedules and forecast. Because v0.6 changes the accounting engine
    itself, the base close already contains absorption variance in legal books,
    AP, cash, tax and retained earnings. This function then replaces the
    management-only outputs that need factory-entity economics.
    """
    result = base_engine.build(end_month, config_path=config_path, allow_live_macro=allow_live_macro)
    config = base_engine.load_config(config_path)

    operations = _read_csv("data/runtime/operational.csv.gz")
    journal = _read_csv("data/runtime/journal.csv.gz")
    products = _read_csv("data/processed/products.csv")
    legal_bs = _read_csv("data/processed/legal_balance_sheet.csv")
    group_bs = _read_csv("data/processed/balance_sheet.csv")
    cf = _read_csv("data/processed/cash_flow.csv")
    factory = _read_csv("data/processed/factory.csv")
    ar_aging = _read_csv("data/processed/ar_aging.csv")
    inventory_aging = _read_csv("data/processed/inventory_aging.csv")
    latest_fc = _read_csv("data/processed/forecast.csv")

    management = management_pnl_with_factory_absorption(operations, journal, set(config["factories"]))
    wc = working_capital(group_bs, management)
    factory_economics, hardware_mix = hardware_factory_accounting_schedule(operations, products, factory, config)
    bridge = consolidation_bridge(_read_csv("data/processed/legal_pnl.csv"), management)
    commentary = management_commentary(management, wc, cf, latest_fc, end_month)

    with open("data/processed/validation.json", "r", encoding="utf-8") as f:
        checks = json.load(f)
    absorption_checks = validate_factory_absorption_accounting(factory, journal)
    checks.update({k: v for k, v in absorption_checks.items() if k != "passed"})
    checks["passed"] = bool(checks.get("passed", False) and absorption_checks["passed"])
    if not checks["passed"]:
        raise RuntimeError(f"Factory absorption controls failed: {checks}")

    _write_csv(management, "data/processed/management_pnl.csv")
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
    )
    _write_csv(pnl, "data/processed/pnl.csv")
    _write_csv(wc, "data/processed/working_capital.csv")
    _write_csv(factory_economics, "data/processed/hardware_factory_economics.csv")
    _write_csv(hardware_mix, "data/processed/hardware_production_mix.csv")
    _write_csv(bridge, "data/processed/consolidation_bridge.csv")
    with open("data/processed/validation.json", "w", encoding="utf-8") as f:
        json.dump(checks, f, indent=2)

    with open("web/data/dashboard.json", "r", encoding="utf-8") as f:
        dashboard = json.load(f)
    monthly = _group_management(management)
    latest_division = management[management.month.eq(end_month)].groupby("division", as_index=False).agg(
        revenue=("revenue", "sum"),
        marginal_contribution=("marginal_contribution", "sum"),
        gross_profit=("gross_profit", "sum"),
        ebit=("ebit", "sum"),
        factory_absorption_variance=("factory_absorption_variance", "sum"),
    )
    dashboard["meta"]["version"] = VERSION
    dashboard["actual"] = base_engine._records(monthly)
    dashboard["management_detail"] = base_engine._records(management)
    dashboard["division"] = base_engine._records(latest_division)
    dashboard["working_capital"] = base_engine._records(wc)
    dashboard["hardware_factory_economics"] = base_engine._records(
        factory_economics[factory_economics.month >= str(pd.Period(end_month, freq="M") - 11)]
    )
    dashboard["hardware_mix"] = base_engine._records(
        hardware_mix[hardware_mix.month.eq(end_month)].sort_values(["source_factory", "units"], ascending=[True, False])
    ) if not hardware_mix.empty else []
    dashboard["factory"] = base_engine._records(factory[factory.month >= str(pd.Period(end_month, freq="M") - 11)])
    dashboard["commentary"] = commentary
    dashboard["validation"] = checks
    with open("web/data/dashboard.json", "w", encoding="utf-8") as f:
        json.dump(dashboard, f, separators=(",", ":"), allow_nan=False)

    with open("web/data/manifest.json", "r", encoding="utf-8") as f:
        manifest = json.load(f)
    latest_factory = factory[factory.month.eq(end_month)]
    manifest["version"] = VERSION
    manifest["latest_factory_absorption_variance"] = round(float(latest_factory.absorption_variance.sum()), 2) if not latest_factory.empty else 0.0
    manifest["latest_factory_under_absorption"] = round(float(latest_factory.under_absorption.sum()), 2) if not latest_factory.empty else 0.0
    manifest["latest_factory_over_absorption"] = round(float(latest_factory.over_absorption.sum()), 2) if not latest_factory.empty else 0.0
    manifest["validation"] = checks
    with open("web/data/manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return result
