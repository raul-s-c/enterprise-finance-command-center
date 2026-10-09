"""Invoice-level analytical ECL evidence over the v0.25 close."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import yaml

from .engine_v21 import _dump_json
from .engine_v25 import build as build_v25
from .invoice_credit_loss_lineage import build_invoice_credit_loss_lineage

VERSION = "0.26.0"


def build(end_month: str, config_path: str = "config/company.yml", allow_live_macro: bool = True):
    result = build_v25(end_month, config_path=config_path, allow_live_macro=allow_live_macro)
    invoice_path = Path("data/processed/ar_invoice_aging.csv")
    schedule_path = Path("data/processed/credit_loss_allowance.csv")
    invoices = pd.read_csv(invoice_path, low_memory=False) if invoice_path.exists() else pd.DataFrame()
    customer_schedule = pd.read_csv(schedule_path, low_memory=False) if schedule_path.exists() else pd.DataFrame()
    with Path(config_path).open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)

    ecl, checks = build_invoice_credit_loss_lineage(invoices, customer_schedule, config, end_month)
    if not checks["passed"]:
        raise RuntimeError(f"Invoice-level analytical ECL failed reconciliation: {checks}")
    if not invoices.empty:
        enriched = invoices.merge(
            ecl[["invoice_id", "risk_multiplier", "credit_loss_allowance", "net_ar", "allowance_pct", "evidence_basis"]],
            on="invoice_id", how="left", validate="one_to_one",
        )
        if enriched.credit_loss_allowance.isna().any():
            raise RuntimeError("Invoice-level ECL did not cover every open invoice")
        enriched.to_csv(invoice_path, index=False)
    else:
        enriched = invoices

    detail_path = Path("web/data/ar_invoice_detail.json")
    detail = json.loads(detail_path.read_text(encoding="utf-8"))
    detail["ecl_basis"] = ecl.evidence_basis.iloc[0] if not ecl.empty else (
        "Analytical allocation of the existing customer-level expected credit-loss policy; not an invoice-specific GL posting."
    )
    detail["ecl_invoice_count"] = int(len(ecl))
    detail["invoices"] = enriched.sort_values("open_amount", ascending=False, kind="stable").to_dict("records") if not enriched.empty else []
    _dump_json(detail, detail_path, allow_nan=False, separators=(",", ":"), indent=None)

    for name in ["data/processed/validation.json", "web/data/dashboard.json", "web/data/manifest.json"]:
        path = Path(name)
        payload = json.loads(path.read_text(encoding="utf-8"))
        validation = payload if name.endswith("validation.json") else payload["validation"]
        prior_passed = bool(validation.get("passed", False))
        validation.update({key: value for key, value in checks.items() if key != "passed"})
        validation["passed"] = bool(prior_passed and checks["passed"])
        if name.endswith("dashboard.json"):
            payload["meta"]["version"] = VERSION
            payload["meta"]["ar_invoice_ecl_count"] = int(len(ecl))
        elif name.endswith("manifest.json"):
            payload["version"] = VERSION
            payload["ar_invoice_ecl_rows"] = int(len(ecl))
            payload["ar_invoice_detail_bytes"] = detail_path.stat().st_size
        _dump_json(payload, path, allow_nan=False,
                   separators=(",", ":") if name.endswith("dashboard.json") else None,
                   indent=None if name.endswith("dashboard.json") else 2)

    if not validation["passed"]:
        raise RuntimeError("Published close validation failed after adding invoice-level analytical ECL")
    return result.__class__(
        result.end_month, result.actual_months, result.forecast_months,
        result.operational_rows, result.journal_rows, result.forecast_rows, True,
    )
