from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd

from . import engine as base_engine
from .engine_v18 import build as build_v18
from .financial_sensitivities import build_financial_sensitivities, validate_macro_and_sensitivities
from .macro import build_macro_lineage, source_manifest


VERSION = "0.19.0"


def _read(path: str) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def _write(frame: pd.DataFrame, path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def _dump_json(payload: object, path: str, **kwargs: object) -> None:
    """Retry transient Windows/OneDrive invalid-handle failures during close writes."""
    for attempt in range(5):
        try:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, **kwargs)
            return
        except OSError as exc:
            if exc.errno != 22 or attempt == 4:
                raise
            time.sleep(1)


def build(end_month: str, config_path: str = "config/company.yml", allow_live_macro: bool = True):
    """Add official macro lineage and controlled CFO sensitivities to v0.18."""
    result = build_v18(end_month, config_path=config_path, allow_live_macro=allow_live_macro)
    config = base_engine.load_config(config_path)
    macro = _read("data/processed/macro.csv")
    forecasts = _read("data/processed/forecast.csv")
    liquidity = _read("data/processed/liquidity_forecast.csv")
    debt = _read("data/processed/debt_schedule.csv")

    lineage = build_macro_lineage(macro, end_month)
    detail, summary = build_financial_sensitivities(forecasts, liquidity, debt, config, end_month)
    sensitivity_checks = validate_macro_and_sensitivities(macro, lineage, detail, summary)

    with open("data/processed/validation.json", encoding="utf-8") as handle:
        checks = json.load(handle)
    checks.update({key: value for key, value in sensitivity_checks.items() if key != "passed"})
    checks["passed"] = bool(checks.get("passed", False) and sensitivity_checks["passed"])
    if not checks["passed"]:
        raise RuntimeError(f"Macro lineage and sensitivity controls failed: {checks}")

    _write(lineage, "data/processed/macro_lineage.csv")
    _write(detail, "data/processed/financial_sensitivity_detail.csv")
    _write(summary, "data/processed/financial_sensitivity_summary.csv")
    _dump_json(source_manifest(macro), "data/processed/source_manifest.json", indent=2)
    _dump_json(checks, "data/processed/validation.json", indent=2)

    with open("web/data/dashboard.json", encoding="utf-8") as handle:
        dashboard = json.load(handle)
    dashboard["meta"]["version"] = VERSION
    dashboard["sources"] = source_manifest(macro)
    dashboard["macro_history"] = base_engine._records(macro)
    dashboard["macro_lineage"] = base_engine._records(lineage)
    dashboard["financial_sensitivity_detail"] = base_engine._records(detail)
    dashboard["financial_sensitivity_summary"] = base_engine._records(summary)
    dashboard["validation"] = checks
    _dump_json(dashboard, "web/data/dashboard.json", separators=(",", ":"), allow_nan=False)

    official_rows = int(lineage.status.eq("Official").sum())
    with open("web/data/manifest.json", encoding="utf-8") as handle:
        manifest = json.load(handle)
    manifest.update({
        "version": VERSION,
        "macro_lineage_rows": int(len(lineage)),
        "macro_official_observations": official_rows,
        "macro_fallback_observations": int(len(lineage) - official_rows),
        "financial_sensitivity_detail_rows": int(len(detail)),
        "financial_sensitivity_scenarios": int(summary.shock.nunique()),
        "validation": checks,
    })
    _dump_json(manifest, "web/data/manifest.json", indent=2)
    return result
