from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from . import engine as base_engine
from .engine_v07 import build as build_v07
from .supplier_payables import (
    ap_aging_summary,
    build_ap_aging,
    supplier_concentration,
    supplier_master,
    validate_ap_aging,
)


VERSION = "0.8.0"


def _read_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


def _write_csv(df: pd.DataFrame, path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def build(end_month: str, config_path: str = "config/company.yml", allow_live_macro: bool = True):
    """Run v0.7 and add supplier-level AP aging and concentration analytics.

    The AP schedule is reconstructed from the legal `2100_AP` ledger. It does not
    alter accounting, supplier payments or cash flow. Publication is blocked if
    supplier-level open lots fail to reconcile to the legal payable balance.
    """
    result = build_v07(end_month, config_path=config_path, allow_live_macro=allow_live_macro)
    config = base_engine.load_config(config_path)
    journal = _read_csv("data/runtime/journal.csv.gz")

    ap_aging = build_ap_aging(journal, config)
    ap_summary = ap_aging_summary(ap_aging)
    concentration = supplier_concentration(ap_aging, end_month)
    suppliers = supplier_master(ap_aging)
    ap_checks = validate_ap_aging(journal, ap_aging)

    with open("data/processed/validation.json", "r", encoding="utf-8") as handle:
        checks = json.load(handle)
    checks.update({key: value for key, value in ap_checks.items() if key != "passed"})
    checks["passed"] = bool(checks.get("passed", False) and ap_checks["passed"])
    if not checks["passed"]:
        raise RuntimeError(f"AP aging controls failed: {checks}")

    _write_csv(ap_aging, "data/processed/ap_aging.csv")
    _write_csv(ap_summary, "data/processed/ap_aging_summary.csv")
    _write_csv(concentration, "data/processed/supplier_concentration.csv")
    _write_csv(suppliers, "data/processed/suppliers.csv")
    with open("data/processed/validation.json", "w", encoding="utf-8") as handle:
        json.dump(checks, handle, indent=2)

    with open("web/data/dashboard.json", "r", encoding="utf-8") as handle:
        dashboard = json.load(handle)
    latest_ap = ap_aging[ap_aging.month.eq(end_month)].copy()
    latest_ap = latest_ap.sort_values(["overdue_ap", "total_ap"], ascending=False).head(80) if not latest_ap.empty else latest_ap
    dashboard["meta"]["version"] = VERSION
    dashboard["ap_aging_summary"] = base_engine._records(ap_summary)
    dashboard["ap_supplier_aging"] = base_engine._records(latest_ap)
    dashboard["supplier_concentration"] = base_engine._records(concentration.head(100)) if not concentration.empty else []
    dashboard["supplier_master"] = base_engine._records(suppliers)
    dashboard["validation"] = checks
    with open("web/data/dashboard.json", "w", encoding="utf-8") as handle:
        json.dump(dashboard, handle, separators=(",", ":"), allow_nan=False)

    with open("web/data/manifest.json", "r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    latest_summary = ap_summary[ap_summary.month.eq(end_month)]
    values = latest_summary.iloc[0].to_dict() if not latest_summary.empty else {}
    manifest["version"] = VERSION
    manifest["ap_aging_rows"] = int(len(ap_aging))
    manifest["supplier_count"] = int(len(suppliers))
    manifest["latest_total_ap"] = round(float(values.get("total_ap", 0.0)), 2)
    manifest["latest_overdue_ap"] = round(float(values.get("overdue_ap", 0.0)), 2)
    manifest["latest_ap_overdue_pct"] = round(float(values.get("overdue_pct", 0.0)), 4)
    manifest["latest_supplier_top5_concentration"] = round(float(values.get("top5_spend_concentration", 0.0)), 4)
    manifest["latest_single_source_ap"] = round(float(values.get("single_source_ap", 0.0)), 2)
    manifest["validation"] = checks
    with open("web/data/manifest.json", "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)

    return result.__class__(
        result.end_month,
        result.actual_months,
        result.forecast_months,
        result.operational_rows,
        result.journal_rows,
        result.forecast_rows,
        True,
    )
