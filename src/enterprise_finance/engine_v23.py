"""Invoice-grain receivables evidence over the v0.22.1 published close."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import yaml

from .ar_invoice_lineage import build_ar_invoice_lineage
from .engine_v21 import _dump_json
from .engine_v22 import build as build_v22

VERSION = "0.23.0"
ALLOCATION_BASIS = (
    "Modeled risk-aware oldest-receivable allocation of posted aggregate AR credits. "
    "Invoice IDs reference source sale journals; collection applications are not bank matched."
)


def _read_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def build(end_month: str, config_path: str = "config/company.yml", allow_live_macro: bool = True):
    result = build_v22(end_month, config_path=config_path, allow_live_macro=allow_live_macro)
    journal = _read_csv("data/runtime/journal.csv.gz")
    customers = _read_csv("data/processed/customers.csv")
    customer_aging = _read_csv("data/processed/ar_aging.csv")
    with Path(config_path).open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)

    invoices, applications, checks = build_ar_invoice_lineage(
        journal, customers, config, end_month, customer_aging
    )
    if not checks["passed"]:
        raise RuntimeError(f"Invoice-grain AR lineage failed reconciliation: {checks}")

    invoice_path = Path("data/processed/ar_invoice_aging.csv")
    application_path = Path("data/processed/ar_invoice_applications.csv")
    invoice_path.parent.mkdir(parents=True, exist_ok=True)
    invoices.to_csv(invoice_path, index=False)
    applications.to_csv(application_path, index=False)

    current_ids = set(invoices.invoice_id.astype(str)) if not invoices.empty else set()
    current_applications = applications.loc[applications.invoice_id.astype(str).isin(current_ids)] if not applications.empty else applications
    evidence = {
        "month": end_month,
        "currency": "EUR",
        "allocation_basis": ALLOCATION_BASIS,
        "invoice_count": int(len(invoices)),
        "application_count": int(len(current_applications)),
        "invoices": invoices.sort_values("open_amount", ascending=False, kind="stable").to_dict("records") if not invoices.empty else [],
        "applications": current_applications.to_dict("records") if not current_applications.empty else [],
    }
    _dump_json(evidence, "web/data/ar_invoice_detail.json", allow_nan=False, separators=(",", ":"), indent=None)

    for name in ["data/processed/validation.json", "web/data/dashboard.json", "web/data/manifest.json"]:
        path = Path(name)
        payload = json.loads(path.read_text(encoding="utf-8"))
        validation = payload if name.endswith("validation.json") else payload["validation"]
        prior_passed = bool(validation.get("passed", False))
        validation.update({key: value for key, value in checks.items() if key != "passed"})
        validation["passed"] = bool(prior_passed and checks["passed"])
        if name.endswith("dashboard.json"):
            payload["meta"]["version"] = VERSION
            payload["meta"]["ar_invoice_count"] = int(len(invoices))
            payload["meta"]["ar_invoice_application_count"] = int(len(current_applications))
        elif name.endswith("manifest.json"):
            payload["version"] = VERSION
            payload["ar_invoice_rows"] = int(len(invoices))
            payload["ar_invoice_application_rows"] = int(len(applications))
            payload["ar_invoice_detail_bytes"] = Path("web/data/ar_invoice_detail.json").stat().st_size
        _dump_json(
            payload,
            name,
            allow_nan=False,
            separators=(",", ":") if name.endswith("dashboard.json") else None,
            indent=None if name.endswith("dashboard.json") else 2,
        )

    if not validation["passed"]:
        raise RuntimeError("Published close validation failed after adding AR invoice lineage")
    return result.__class__(
        result.end_month,
        result.actual_months,
        result.forecast_months,
        result.operational_rows,
        len(journal),
        result.forecast_rows,
        True,
    )
