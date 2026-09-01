from __future__ import annotations

import gzip
import json
from pathlib import Path

import pandas as pd

from . import engine as base_engine
from .engine_v10_final import build as build_v10
from .reporting import validate_all
from .treasury import (
    append_cash_pool_journals,
    cash_flow_with_treasury,
    chart_of_accounts_with_treasury,
    debt_schedule,
    group_balance_sheet_with_treasury,
    legal_balance_sheet_with_treasury,
    treasury_entity_schedule,
    validate_treasury,
)


VERSION = "0.11.0"


def _read_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def _write_csv(df: pd.DataFrame, path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def _write_gzip_csv(df: pd.DataFrame, path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        df.to_csv(handle, index=False)


def _group_cash_flow(cf: pd.DataFrame) -> pd.DataFrame:
    return cf.groupby("month", as_index=False).agg(
        operating_cash_flow=("operating_cash_flow", "sum"),
        investing_cash_flow=("investing_cash_flow", "sum"),
        financing_cash_flow=("financing_cash_flow", "sum"),
        free_cash_flow=("free_cash_flow", "sum"),
        net_cash_movement=("net_cash_movement", "sum"),
        intercompany_treasury=("intercompany_treasury", "sum"),
    )


def build(end_month: str, config_path: str = "config/company.yml", allow_live_macro: bool = True):
    """Run the v0.10 close and add legal-entity Treasury / liquidity management."""
    result = build_v10(end_month, config_path=config_path, allow_live_macro=allow_live_macro)
    config = base_engine.load_config(config_path)

    base_journal = _read_csv("data/runtime/journal.csv.gz")
    management = _read_csv("data/processed/management_pnl.csv")
    legal_pnl = _read_csv("data/processed/legal_pnl.csv")
    bridge = _read_csv("data/processed/consolidation_bridge.csv")

    journal, pool_schedule = append_cash_pool_journals(base_journal, config)
    legal_bs = legal_balance_sheet_with_treasury(journal)
    group_bs = group_balance_sheet_with_treasury(
        legal_bs, float(config["transfer_pricing"]["manufacturing_cost_plus"])
    )
    cf = cash_flow_with_treasury(journal)
    debt, maturity, liquidity = debt_schedule(journal, management, config)
    entity_treasury = treasury_entity_schedule(journal, debt, config)

    overall = validate_all(journal, legal_bs, group_bs, cf, bridge)
    treasury_checks = validate_treasury(base_journal, journal, legal_bs, group_bs, debt)

    latest_entity = entity_treasury[entity_treasury.month.eq(end_month)].copy()
    non_hq = latest_entity[~latest_entity.entity.eq(str(config.get("treasury", {}).get("hq_entity", "DE01")))]
    below_minimum = int((non_hq.cash < non_hq.minimum_cash - 0.05).sum()) if not non_hq.empty else 0
    negative_cash = int((latest_entity.cash < -0.05).sum()) if not latest_entity.empty else 0

    with open("data/processed/validation.json", "r", encoding="utf-8") as handle:
        checks = json.load(handle)
    checks.update({key: value for key, value in overall.items() if key != "passed"})
    checks.update({key: value for key, value in treasury_checks.items() if key != "passed"})
    checks["treasury_subsidiaries_below_minimum_cash"] = below_minimum
    checks["treasury_negative_cash_entities"] = negative_cash
    checks["passed"] = bool(
        checks.get("passed", False)
        and overall["passed"]
        and treasury_checks["passed"]
        and below_minimum == 0
        and negative_cash == 0
    )
    if not checks["passed"]:
        raise RuntimeError(f"Treasury close controls failed: {checks}")

    _write_gzip_csv(journal, "data/runtime/journal.csv.gz")
    sample = pd.concat([
        journal.head(4300),
        journal[journal.journal_type.eq("treasury_cash_pool")].head(700),
    ], ignore_index=True).drop_duplicates()
    _write_csv(sample, "data/processed/journal_sample.csv")
    _write_csv(chart_of_accounts_with_treasury(), "data/processed/chart_of_accounts.csv")
    _write_csv(legal_bs, "data/processed/legal_balance_sheet.csv")
    _write_csv(group_bs, "data/processed/balance_sheet.csv")
    _write_csv(cf, "data/processed/cash_flow.csv")
    _write_csv(pool_schedule, "data/processed/treasury_cash_pool.csv")
    _write_csv(debt, "data/processed/debt_schedule.csv")
    _write_csv(maturity, "data/processed/debt_maturity_ladder.csv")
    _write_csv(liquidity, "data/processed/liquidity_covenants.csv")
    _write_csv(entity_treasury, "data/processed/treasury_entity_cash.csv")
    with open("data/processed/validation.json", "w", encoding="utf-8") as handle:
        json.dump(checks, handle, indent=2)

    with open("web/data/dashboard.json", "r", encoding="utf-8") as handle:
        dashboard = json.load(handle)
    recent_start = str(pd.Period(end_month, freq="M") - 23)
    latest_pool = pool_schedule[pool_schedule.month.eq(end_month)] if not pool_schedule.empty else pd.DataFrame()
    latest_liquidity = liquidity[liquidity.month.eq(end_month)] if not liquidity.empty else pd.DataFrame()

    dashboard["meta"]["version"] = VERSION
    dashboard["balance_sheet"] = base_engine._records(group_bs)
    dashboard["cash_flow"] = base_engine._records(_group_cash_flow(cf))
    dashboard["cash_flow_detail"] = base_engine._records(cf)
    dashboard["treasury_liquidity"] = base_engine._records(liquidity[liquidity.month.ge(recent_start)])
    dashboard["treasury_entity_cash"] = base_engine._records(latest_entity)
    dashboard["treasury_cash_pool"] = base_engine._records(latest_pool)
    dashboard["debt_schedule"] = base_engine._records(debt[debt.month.eq(end_month)])
    dashboard["debt_maturity_ladder"] = base_engine._records(maturity)
    dashboard["validation"] = checks
    with open("web/data/dashboard.json", "w", encoding="utf-8") as handle:
        json.dump(dashboard, handle, separators=(",", ":"), allow_nan=False)

    with open("web/data/manifest.json", "r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    liq = latest_liquidity.iloc[0].to_dict() if not latest_liquidity.empty else {}
    total_pool = float(latest_pool.amount.sum()) if not latest_pool.empty else 0.0
    sweeps = float(latest_pool.loc[latest_pool.transfer_type.eq("surplus_sweep"), "amount"].sum()) if not latest_pool.empty else 0.0
    funding = float(latest_pool.loc[latest_pool.transfer_type.eq("liquidity_funding"), "amount"].sum()) if not latest_pool.empty else 0.0

    manifest["version"] = VERSION
    manifest["journal_rows"] = int(len(journal))
    manifest["latest_group_cash"] = round(float(liq.get("cash", 0.0)), 2)
    manifest["latest_gross_debt"] = round(float(liq.get("gross_debt", 0.0)), 2)
    manifest["latest_net_debt"] = round(float(liq.get("net_debt", 0.0)), 2)
    manifest["latest_liquidity_headroom"] = round(float(liq.get("liquidity_headroom", 0.0)), 2)
    manifest["latest_net_leverage"] = round(float(liq.get("net_leverage", 0.0)), 4)
    manifest["latest_interest_coverage"] = round(float(liq.get("interest_coverage", 0.0)), 4)
    manifest["latest_covenant_status"] = str(liq.get("covenant_status", ""))
    manifest["latest_cash_pool_transfers"] = round(total_pool, 2)
    manifest["latest_cash_pool_sweeps"] = round(sweeps, 2)
    manifest["latest_cash_pool_funding"] = round(funding, 2)
    manifest["treasury_pool_rows"] = int(len(pool_schedule))
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
