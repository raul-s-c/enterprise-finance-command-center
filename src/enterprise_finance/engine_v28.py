"""Cash movement source lineage over the v0.27 close."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .engine_v21 import _dump_json
from .engine_v27 import build as build_v27
from .cash_movement_lineage import build_cash_movement_lineage

VERSION = "0.28.2"
EVIDENCE_BASIS = (
    "Current-close cash-account journal rows are reconciled to the published cash-flow summary. "
    "Customer invoices and supplier accruals are analytical allocations of aggregate posted cash "
    "journals, not bank-matched remittances or invoice-level settlements. CAPEX SPEND ties to "
    "posted project journal IDs; GO_LIVE transfers are non-cash."
)


def _read_csv(path: str) -> pd.DataFrame:
    file = Path(path)
    if not file.exists():
        raise RuntimeError(f"Required cash movement lineage source is missing: {path}")
    return pd.read_csv(file, low_memory=False)


def build(end_month: str, config_path: str = "config/company.yml", allow_live_macro: bool = True):
    result = build_v27(end_month, config_path=config_path, allow_live_macro=allow_live_macro)
    journal = _read_csv("data/runtime/journal.csv.gz")
    ar_applications = _read_csv("data/processed/ar_invoice_applications.csv")
    ap_applications = _read_csv("data/processed/ap_item_applications.csv")
    capex_events = _read_csv("data/processed/fixed_asset_project_events.csv")

    dashboard_path = Path("web/data/dashboard.json")
    dashboard = json.loads(dashboard_path.read_text(encoding="utf-8"))
    expected_cash_flow = pd.DataFrame(dashboard.get("cash_flow_detail", []))
    lineage, checks = build_cash_movement_lineage(
        journal, ar_applications, ap_applications, capex_events, expected_cash_flow, end_month
    )
    if not checks["passed"]:
        raise RuntimeError(f"Cash movement source lineage failed reconciliation: {checks}")

    lineage_path = Path("data/processed/cash_movement_lineage.csv")
    lineage.to_csv(lineage_path, index=False)
    dashboard["cash_movement_lineage"] = lineage.to_dict("records") if not lineage.empty else []
    dashboard["cash_movement_evidence_basis"] = EVIDENCE_BASIS
    dashboard["meta"]["version"] = VERSION
    dashboard["meta"]["cash_movement_lineage_count"] = int(len(lineage))
    dashboard["meta"]["cash_movement_lineage_month"] = str(end_month)
    dashboard["meta"]["cash_movement_evidence_basis"] = EVIDENCE_BASIS
    dashboard["validation"].update({key: value for key, value in checks.items() if key != "passed"})
    dashboard["validation"]["passed"] = bool(dashboard["validation"].get("passed", False) and checks["passed"])
    _dump_json(dashboard, dashboard_path, allow_nan=False, separators=(",", ":"), indent=None)

    validation_path = Path("data/processed/validation.json")
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    validation.update({key: value for key, value in checks.items() if key != "passed"})
    validation["passed"] = bool(validation.get("passed", False) and checks["passed"])
    _dump_json(validation, validation_path, allow_nan=False)

    manifest_path = Path("web/data/manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["version"] = VERSION
    manifest["cash_movement_lineage_rows"] = int(len(lineage))
    manifest["cash_movement_detail_bytes"] = lineage_path.stat().st_size
    manifest["cash_movement_evidence_basis"] = EVIDENCE_BASIS
    manifest["validation"].update({key: value for key, value in checks.items() if key != "passed"})
    manifest["validation"]["passed"] = bool(manifest["validation"].get("passed", False) and checks["passed"])
    _dump_json(manifest, manifest_path, allow_nan=False)

    if not dashboard["validation"]["passed"] or not validation["passed"] or not manifest["validation"]["passed"]:
        raise RuntimeError("Close validation failed after adding cash movement source lineage")
    return result.__class__(
        result.end_month,
        result.actual_months,
        result.forecast_months,
        result.operational_rows,
        result.journal_rows,
        result.forecast_rows,
        True,
    )
