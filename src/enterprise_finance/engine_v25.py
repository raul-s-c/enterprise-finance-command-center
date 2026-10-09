"""Project-grain fixed-asset lifecycle evidence over the v0.24 close."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import yaml

from .engine_v21 import _dump_json
from .engine_v24 import build as build_v24
from .fixed_asset_lineage import build_fixed_asset_lineage

VERSION = "0.25.0"
EVIDENCE_BASIS = (
    "Project spend and CIP-to-PPE transfer tie to posted journal IDs. Project depreciation is reconstructed "
    "from approved budget and useful life because depreciation posts in one aggregate entity journal; "
    "opening PPE remains an entity-level pool."
)


def build(end_month: str, config_path: str = "config/company.yml", allow_live_macro: bool = True):
    result = build_v24(end_month, config_path=config_path, allow_live_macro=allow_live_macro)
    journal = pd.read_csv("data/runtime/journal.csv.gz", low_memory=False)
    capex_events = pd.read_csv("data/processed/capex.csv", low_memory=False)
    with Path(config_path).open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)

    register, events, checks = build_fixed_asset_lineage(journal, capex_events, config, end_month)
    if not checks["passed"]:
        raise RuntimeError(f"Fixed-asset project lineage failed reconciliation: {checks}")

    register.to_csv("data/processed/fixed_asset_project_register.csv", index=False)
    events.to_csv("data/processed/fixed_asset_project_events.csv", index=False)
    detail = {
        "month": end_month,
        "currency": "EUR",
        "evidence_basis": EVIDENCE_BASIS,
        "project_count": int(len(register)),
        "event_count": int(len(events)),
        "projects": register.sort_values(["status", "project_name"], kind="stable").to_dict("records") if not register.empty else [],
        "events": events.to_dict("records") if not events.empty else [],
    }
    _dump_json(detail, "web/data/fixed_asset_detail.json", allow_nan=False, separators=(",", ":"), indent=None)

    for name in ["data/processed/validation.json", "web/data/dashboard.json", "web/data/manifest.json"]:
        path = Path(name)
        payload = json.loads(path.read_text(encoding="utf-8"))
        validation = payload if name.endswith("validation.json") else payload["validation"]
        prior_passed = bool(validation.get("passed", False))
        validation.update({key: value for key, value in checks.items() if key != "passed"})
        validation["passed"] = bool(prior_passed and checks["passed"])
        if name.endswith("dashboard.json"):
            payload["meta"]["version"] = VERSION
            payload["meta"]["fixed_asset_project_count"] = int(len(register))
            payload["meta"]["fixed_asset_event_count"] = int(len(events))
        elif name.endswith("manifest.json"):
            payload["version"] = VERSION
            payload["fixed_asset_project_rows"] = int(len(register))
            payload["fixed_asset_event_rows"] = int(len(events))
            payload["fixed_asset_detail_bytes"] = Path("web/data/fixed_asset_detail.json").stat().st_size
        _dump_json(
            payload,
            name,
            allow_nan=False,
            separators=(",", ":") if name.endswith("dashboard.json") else None,
            indent=None if name.endswith("dashboard.json") else 2,
        )

    if not validation["passed"]:
        raise RuntimeError("Published close validation failed after adding fixed-asset project lineage")
    return result.__class__(
        result.end_month,
        result.actual_months,
        result.forecast_months,
        result.operational_rows,
        len(journal),
        result.forecast_rows,
        True,
    )
