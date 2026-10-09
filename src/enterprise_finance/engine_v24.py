"""Source-accrual-grain supplier payables evidence over the v0.23 close."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import yaml

from .ap_item_lineage import build_ap_item_lineage
from .engine_v21 import _dump_json
from .engine_v23 import build as build_v23

VERSION = "0.24.0"
ALLOCATION_BASIS = (
    "Modeled oldest-accrual allocation of posted aggregate AP reductions. "
    "Source IDs are accrual journal IDs, not supplier invoice numbers; reductions are not remittance matched."
)


def _read_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def build(end_month: str, config_path: str = "config/company.yml", allow_live_macro: bool = True):
    result = build_v23(end_month, config_path=config_path, allow_live_macro=allow_live_macro)
    journal = _read_csv("data/runtime/journal.csv.gz")
    supplier_aging = _read_csv("data/processed/ap_aging.csv")
    with Path(config_path).open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)

    items, applications, checks = build_ap_item_lineage(
        journal, config, end_month, supplier_aging
    )
    if not checks["passed"]:
        raise RuntimeError(f"Source-accrual AP lineage failed reconciliation: {checks}")

    item_path = Path("data/processed/ap_item_aging.csv")
    application_path = Path("data/processed/ap_item_applications.csv")
    item_path.parent.mkdir(parents=True, exist_ok=True)
    items.to_csv(item_path, index=False)
    applications.to_csv(application_path, index=False)

    current_ids = set(items.source_item_id.astype(str)) if not items.empty else set()
    current_applications = (
        applications.loc[applications.accrual_journal_id.astype(str).isin(current_ids)]
        if not applications.empty else applications
    )
    evidence = {
        "month": end_month,
        "currency": "EUR",
        "allocation_basis": ALLOCATION_BASIS,
        "item_count": int(len(items)),
        "application_count": int(len(current_applications)),
        "items": items.sort_values("open_amount", ascending=False, kind="stable").to_dict("records") if not items.empty else [],
        "applications": current_applications.to_dict("records") if not current_applications.empty else [],
    }
    _dump_json(evidence, "web/data/ap_item_detail.json", allow_nan=False, separators=(",", ":"), indent=None)

    for name in ["data/processed/validation.json", "web/data/dashboard.json", "web/data/manifest.json"]:
        path = Path(name)
        payload = json.loads(path.read_text(encoding="utf-8"))
        validation = payload if name.endswith("validation.json") else payload["validation"]
        prior_passed = bool(validation.get("passed", False))
        validation.update({key: value for key, value in checks.items() if key != "passed"})
        validation["passed"] = bool(prior_passed and checks["passed"])
        if name.endswith("dashboard.json"):
            payload["meta"]["version"] = VERSION
            payload["meta"]["ap_item_count"] = int(len(items))
            payload["meta"]["ap_item_application_count"] = int(len(current_applications))
        elif name.endswith("manifest.json"):
            payload["version"] = VERSION
            payload["ap_item_rows"] = int(len(items))
            payload["ap_item_application_rows"] = int(len(applications))
            payload["ap_item_detail_bytes"] = Path("web/data/ap_item_detail.json").stat().st_size
        _dump_json(
            payload,
            name,
            allow_nan=False,
            separators=(",", ":") if name.endswith("dashboard.json") else None,
            indent=None if name.endswith("dashboard.json") else 2,
        )

    if not validation["passed"]:
        raise RuntimeError("Published close validation failed after adding source-accrual AP lineage")
    return result.__class__(
        result.end_month,
        result.actual_months,
        result.forecast_months,
        result.operational_rows,
        len(journal),
        result.forecast_rows,
        True,
    )
