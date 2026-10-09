import json
from pathlib import Path

import pandas as pd
import pytest

from enterprise_finance import engine_v27
from enterprise_finance.engine import BuildResult


def _prepare_close(tmp_path, monkeypatch, journal_product="SKU-1", invoice_product="SKU-1"):
    monkeypatch.chdir(tmp_path)
    for path in ["data/runtime", "data/processed", "web/data"]:
        Path(path).mkdir(parents=True)
    pd.DataFrame([{"journal_type": "sale", "product": journal_product}]).to_csv(
        "data/runtime/journal.csv.gz", index=False, compression="gzip"
    )
    pd.DataFrame([{"product": "SKU-1"}]).to_csv("data/processed/products.csv", index=False)
    pd.DataFrame([{"invoice_id": "SALE-1", "product": invoice_product}]).to_csv(
        "data/processed/ar_invoice_aging.csv", index=False
    )
    Path("data/processed/validation.json").write_text(json.dumps({"passed": True}), encoding="utf-8")
    Path("web/data/dashboard.json").write_text(json.dumps({"meta": {"version": "0.26.0"}, "validation": {"passed": True}}), encoding="utf-8")
    Path("web/data/manifest.json").write_text(json.dumps({"version": "0.26.0", "validation": {"passed": True}}), encoding="utf-8")
    monkeypatch.setattr(engine_v27, "build_v26", lambda *args, **kwargs: BuildResult("2026-09", 36, 24, 1, 2, 3, True))


def test_v27_wrapper_publishes_sku_lineage_controls(tmp_path, monkeypatch):
    _prepare_close(tmp_path, monkeypatch)

    result = engine_v27.build("2026-09", allow_live_macro=False)

    validation = json.loads(Path("data/processed/validation.json").read_text(encoding="utf-8"))
    dashboard = json.loads(Path("web/data/dashboard.json").read_text(encoding="utf-8"))
    manifest = json.loads(Path("web/data/manifest.json").read_text(encoding="utf-8"))
    assert result.validation_passed
    assert validation["sale_journal_invalid_product_rows"] == 0
    assert validation["invoice_invalid_product_rows"] == 0
    assert validation["invoice_product_lineage_passed"]
    assert manifest["version"] == dashboard["meta"]["version"] == "0.27.0"
    assert manifest["invoice_product_lineage_rows"] == dashboard["meta"]["invoice_product_lineage_rows"] == 1


@pytest.mark.parametrize("journal_product,invoice_product", [
    ("<bound method Series.prod of month 2026-09>", "SKU-1"),
    ("SKU-1", "UNKNOWN-SKU"),
])
def test_v27_wrapper_fails_closed_on_invalid_product_lineage(tmp_path, monkeypatch, journal_product, invoice_product):
    _prepare_close(tmp_path, monkeypatch, journal_product, invoice_product)

    with pytest.raises(RuntimeError, match="product lineage failed catalog validation"):
        engine_v27.build("2026-09", allow_live_macro=False)
