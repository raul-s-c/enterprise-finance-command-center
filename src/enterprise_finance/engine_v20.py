from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from . import engine as base_engine
from .engine_v19 import _dump_json, build as build_v19
from .transaction_fx import (
    build_transaction_documents,
    build_transaction_fx_snapshots,
    summarize_transaction_fx,
    validate_transaction_fx,
)


VERSION = "0.20.0"


def _read(path: str) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def _write(frame: pd.DataFrame, path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def build(end_month: str, config_path: str = "config/company.yml", allow_live_macro: bool = True):
    """Add a foreign-currency transaction subledger to the v0.19 close."""
    result = build_v19(end_month, config_path=config_path, allow_live_macro=allow_live_macro)
    config = base_engine.load_config(config_path)
    journal = _read("data/runtime/journal.csv.gz")
    macro = _read("data/processed/macro.csv")

    documents = build_transaction_documents(journal, macro, config)
    snapshots = build_transaction_fx_snapshots(documents, macro, end_month)
    summary = summarize_transaction_fx(snapshots)
    fx_checks = validate_transaction_fx(documents, snapshots, summary, macro)

    with open("data/processed/validation.json", encoding="utf-8") as handle:
        checks = json.load(handle)
    checks.update({key: value for key, value in fx_checks.items() if key != "passed"})
    checks["passed"] = bool(checks.get("passed", False) and fx_checks["passed"])
    if not checks["passed"]:
        raise RuntimeError(f"Transaction FX subledger controls failed: {checks}")

    _write(documents, "data/processed/transaction_fx_documents.csv")
    _write(snapshots, "data/processed/transaction_fx_snapshots.csv")
    _write(summary, "data/processed/transaction_fx_summary.csv")
    _dump_json(checks, "data/processed/validation.json", indent=2)

    close = snapshots[snapshots.snapshot_month.eq(end_month)].copy()
    close["absolute_exposure"] = close.carrying_reporting_eur.abs()
    close = close.sort_values("absolute_exposure", ascending=False).drop(columns="absolute_exposure")
    with open("web/data/dashboard.json", encoding="utf-8") as handle:
        dashboard = json.load(handle)
    dashboard["meta"]["version"] = VERSION
    dashboard["transaction_fx_summary"] = base_engine._records(summary)
    dashboard["transaction_fx_close_documents"] = base_engine._records(close)
    dashboard["validation"] = checks
    _dump_json(dashboard, "web/data/dashboard.json", separators=(",", ":"), allow_nan=False)

    current = summary[summary.month.eq(end_month)]
    with open("web/data/manifest.json", encoding="utf-8") as handle:
        manifest = json.load(handle)
    manifest.update({
        "version": VERSION,
        "transaction_fx_document_rows": int(len(documents)),
        "transaction_fx_snapshot_rows": int(len(snapshots)),
        "transaction_fx_summary_rows": int(len(summary)),
        "transaction_fx_open_documents": int(current.open_documents.sum()),
        "transaction_fx_net_exposure_eur": round(float(current.net_exposure_eur.sum()), 2),
        "transaction_fx_unrealized_pnl_eur": round(float(current.unrealized_fx_gain_loss_eur.sum()), 2),
        "transaction_fx_realized_pnl_eur": round(float(current.realized_fx_gain_loss_eur.sum()), 2),
        "validation": checks,
    })
    _dump_json(manifest, "web/data/manifest.json", indent=2)
    return result
