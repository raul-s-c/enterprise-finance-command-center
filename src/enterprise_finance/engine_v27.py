"""SKU-level integrity controls for invoice and sales-journal lineage over v0.26."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .engine_v21 import _dump_json
from .engine_v26 import build as build_v26

VERSION = "0.27.1"


def build(end_month: str, config_path: str = "config/company.yml", allow_live_macro: bool = True):
    result = build_v26(end_month, config_path=config_path, allow_live_macro=allow_live_macro)

    journal = pd.read_csv("data/runtime/journal.csv.gz", low_memory=False)
    products = pd.read_csv("data/processed/products.csv", low_memory=False)
    invoice_path = Path("data/processed/ar_invoice_aging.csv")
    invoices = pd.read_csv(invoice_path, low_memory=False) if invoice_path.exists() else pd.DataFrame()
    if "product" not in products or "journal_type" not in journal or "product" not in journal:
        raise RuntimeError("SKU lineage control is missing required product or journal fields")

    catalog = set(products["product"].dropna().astype(str))
    sales = journal.loc[journal["journal_type"].eq("sale")]
    invalid_journal = ~sales["product"].astype("string").isin(catalog)
    invalid_invoices = pd.Series(False, index=invoices.index)
    if not invoices.empty:
        if "product" not in invoices:
            raise RuntimeError("SKU lineage control cannot validate invoice products")
        invalid_invoices = ~invoices["product"].astype("string").isin(catalog)

    checks = {
        "sale_journal_invalid_product_rows": int(invalid_journal.sum()),
        "invoice_invalid_product_rows": int(invalid_invoices.sum()),
        "invoice_product_lineage_passed": bool(not invalid_journal.any() and not invalid_invoices.any()),
    }
    if not checks["invoice_product_lineage_passed"]:
        raise RuntimeError(f"Invoice product lineage failed catalog validation: {checks}")

    for name in ["data/processed/validation.json", "web/data/dashboard.json", "web/data/manifest.json"]:
        path = Path(name)
        payload = json.loads(path.read_text(encoding="utf-8"))
        validation = payload if name.endswith("validation.json") else payload["validation"]
        prior_passed = bool(validation.get("passed", False))
        validation.update(checks)
        validation["passed"] = bool(prior_passed and checks["invoice_product_lineage_passed"])
        if name.endswith("dashboard.json"):
            payload["meta"]["version"] = VERSION
            payload["meta"]["invoice_product_lineage_rows"] = int(len(invoices))
        elif name.endswith("manifest.json"):
            payload["version"] = VERSION
            payload["sale_journal_invalid_product_rows"] = checks["sale_journal_invalid_product_rows"]
            payload["invoice_product_lineage_rows"] = int(len(invoices))
        _dump_json(
            payload,
            path,
            allow_nan=False,
            separators=(",", ":") if name.endswith("dashboard.json") else None,
            indent=None if name.endswith("dashboard.json") else 2,
        )

    if not validation["passed"]:
        raise RuntimeError("Published close validation failed after SKU lineage controls")
    return result.__class__(
        result.end_month,
        result.actual_months,
        result.forecast_months,
        result.operational_rows,
        result.journal_rows,
        result.forecast_rows,
        True,
    )
