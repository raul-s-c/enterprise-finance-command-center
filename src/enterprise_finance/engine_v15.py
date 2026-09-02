from __future__ import annotations

import gzip
import json
from pathlib import Path

import pandas as pd

from . import engine as base_engine
from .engine_v14 import build as build_v14
from .fx_translation import (
    TRANSLATION_RESERVE,
    build_translation_schedule,
    constant_currency_analysis,
    enrich_journal_with_functional_currency,
    local_trial_balance,
    validate_fx_translation,
)


VERSION = "0.15.0"


def _read_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def _write_csv(frame: pd.DataFrame, path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def _write_gzip_csv(frame: pd.DataFrame, path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        frame.to_csv(handle, index=False)


def _chart_with_translation_reserve(chart: pd.DataFrame) -> pd.DataFrame:
    if TRANSLATION_RESERVE in set(chart.account.astype(str)):
        return chart.copy()
    extra = pd.DataFrame([{
        "account": TRANSLATION_RESERVE,
        "statement": "Balance Sheet",
        "line": "Foreign Currency Translation Reserve",
        "account_type": "Equity",
    }])
    return pd.concat([chart, extra], ignore_index=True)


def _fx_monthly_summary(translation: pd.DataFrame) -> pd.DataFrame:
    if translation.empty:
        return pd.DataFrame()
    return translation.groupby("month", as_index=False).agg(
        translated_assets=("translated_assets", "sum"),
        translated_liabilities=("translated_liabilities", "sum"),
        translated_equity_before_cta=("translated_equity_before_cta", "sum"),
        fx_translation_reserve=("fx_translation_reserve", "sum"),
        translated_equity=("translated_equity", "sum"),
    )


def build(end_month: str, config_path: str = "config/company.yml", allow_live_macro: bool = True):
    """Run v0.14 and add functional-currency books plus EUR translation analytics."""
    result = build_v14(end_month, config_path=config_path, allow_live_macro=allow_live_macro)
    config = base_engine.load_config(config_path)

    journal = _read_csv("data/runtime/journal.csv.gz")
    macro = _read_csv("data/processed/macro.csv")
    management = _read_csv("data/processed/management_pnl.csv")
    chart = _chart_with_translation_reserve(_read_csv("data/processed/chart_of_accounts.csv"))

    local_journal = enrich_journal_with_functional_currency(journal, macro, config)
    local_tb = local_trial_balance(local_journal)
    translation = build_translation_schedule(local_journal, macro, config, chart)
    cc = constant_currency_analysis(management, macro, config, end_month)
    fx_checks = validate_fx_translation(local_journal, translation)

    with open("data/processed/validation.json", "r", encoding="utf-8") as handle:
        checks = json.load(handle)
    checks.update({k: v for k, v in fx_checks.items() if k != "passed"})
    checks["functional_currency_journal_missing"] = int(local_journal.empty)
    checks["fx_translation_schedule_missing"] = int(translation.empty)
    checks["constant_currency_analysis_missing"] = int(cc.empty)
    checks["passed"] = bool(
        checks.get("passed", False)
        and fx_checks["passed"]
        and checks["functional_currency_journal_missing"] == 0
        and checks["fx_translation_schedule_missing"] == 0
        and checks["constant_currency_analysis_missing"] == 0
    )
    if not checks["passed"]:
        raise RuntimeError(f"Multi-currency controls failed: {checks}")

    _write_csv(chart, "data/processed/chart_of_accounts.csv")
    _write_csv(local_journal.head(5000), "data/processed/functional_currency_journal_sample.csv")
    _write_gzip_csv(local_journal, "data/runtime/functional_currency_journal.csv.gz")
    _write_csv(local_tb, "data/processed/local_trial_balance.csv")
    _write_csv(translation, "data/processed/fx_translation.csv")
    _write_csv(cc, "data/processed/constant_currency_analysis.csv")
    with open("data/processed/validation.json", "w", encoding="utf-8") as handle:
        json.dump(checks, handle, indent=2)

    fx_summary = _fx_monthly_summary(translation)
    with open("web/data/dashboard.json", "r", encoding="utf-8") as handle:
        dashboard = json.load(handle)
    dashboard["meta"]["version"] = VERSION
    dashboard["fx_translation"] = base_engine._records(translation)
    dashboard["fx_translation_summary"] = base_engine._records(fx_summary)
    dashboard["constant_currency"] = base_engine._records(cc)
    dashboard["validation"] = checks
    with open("web/data/dashboard.json", "w", encoding="utf-8") as handle:
        json.dump(dashboard, handle, separators=(",", ":"), allow_nan=False)

    latest_translation = translation[translation.month.eq(end_month)]
    foreign_cc = cc[~cc.functional_currency.eq("EUR")] if not cc.empty else pd.DataFrame()
    with open("web/data/manifest.json", "r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    manifest["version"] = VERSION
    manifest["functional_currency_journal_rows"] = int(len(local_journal))
    manifest["local_trial_balance_rows"] = int(len(local_tb))
    manifest["fx_translation_rows"] = int(len(translation))
    manifest["functional_currencies"] = sorted(local_journal.functional_currency.astype(str).unique().tolist())
    manifest["latest_fx_translation_reserve"] = round(float(latest_translation.fx_translation_reserve.sum()), 2) if not latest_translation.empty else 0.0
    manifest["latest_revenue_fx_effect"] = round(float(foreign_cc.revenue_fx_effect.sum()), 2) if not foreign_cc.empty else 0.0
    manifest["latest_ebit_fx_effect"] = round(float(foreign_cc.ebit_fx_effect.sum()), 2) if not foreign_cc.empty else 0.0
    manifest["validation"] = checks
    with open("web/data/manifest.json", "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)

    return result
