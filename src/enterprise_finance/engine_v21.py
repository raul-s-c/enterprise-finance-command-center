"""FX source integrity and close continuity, without historical GL adjustments."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .engine import load_config
from .engine_v19 import _dump_json
from .engine_v20 import build as build_v20
from .transaction_fx import build_intercompany_contracts, validate_transaction_fx

VERSION = "0.21.0"


def build(end_month: str, config_path: str = "config/company.yml", allow_live_macro: bool = True):
    result = build_v20(end_month, config_path=config_path, allow_live_macro=allow_live_macro)
    def read(name):
        return pd.read_csv(f"data/processed/{name}.csv", low_memory=False)
    journal = pd.read_csv("data/runtime/journal.csv.gz", low_memory=False)
    config, macro = load_config(config_path), read("macro")
    contracts = build_intercompany_contracts(journal, macro, config)
    checks = validate_transaction_fx(
        read("transaction_fx_documents"), read("transaction_fx_snapshots"), read("transaction_fx_summary"),
        macro, end_month=end_month, journal=journal, config=config, contracts=contracts,
    )
    if not checks["passed"]:
        raise RuntimeError(f"Transaction FX source integrity failed: {checks}")
    contracts.to_csv("data/processed/intercompany_fx_contracts.csv", index=False)
    for name in ["data/processed/validation.json", "web/data/dashboard.json", "web/data/manifest.json"]:
        payload = json.loads(Path(name).read_text(encoding="utf-8"))
        validation = payload if name.endswith("validation.json") else payload["validation"]
        prior_passed = validation["passed"]
        validation.update(checks)
        validation["passed"] = bool(prior_passed and checks["passed"])
        if name.endswith("dashboard.json"):
            payload["meta"]["version"] = VERSION
        elif name.endswith("manifest.json"):
            payload["version"] = VERSION
            payload["intercompany_fx_contract_rows"] = len(contracts)
        _dump_json(payload, name, allow_nan=False, indent=None if name.endswith("dashboard.json") else 2)
    return result
