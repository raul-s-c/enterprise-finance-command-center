import json
from pathlib import Path

import pandas as pd
import yaml

from enterprise_finance.engine import BuildResult
from enterprise_finance import engine_v23
from enterprise_finance.customer_receivables_v10 import build_ar_aging_with_contracts


def test_release_wrapper_publishes_invoice_detail_and_reconciliation(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("data/processed").mkdir(parents=True)
    Path("data/runtime").mkdir(parents=True)
    Path("web/data").mkdir(parents=True)
    config = {"working_capital": {"payment_terms_days": {"Hardware": 30}}}
    Path("config").mkdir()
    Path("config/company.yml").write_text(yaml.safe_dump(config), encoding="utf-8")

    journal = pd.DataFrame([dict(
        month="2026-09", entity="US01", division="Hardware", account="1100_AR",
        journal_id="SALE-2026-09-00001-US01", journal_type="sale", debit=125.0,
        credit=0.0, customer="C1", product="HW-1",
    )])
    customers = pd.DataFrame([dict(customer="C1", customer_name="Acme", segment="Core", customer_size=1.0)])
    journal.to_csv("data/runtime/journal.csv.gz", index=False, compression="gzip")
    customers.to_csv("data/processed/customers.csv", index=False)
    build_ar_aging_with_contracts(journal, customers, config).to_csv("data/processed/ar_aging.csv", index=False)
    Path("data/processed/validation.json").write_text(json.dumps({"passed": True}), encoding="utf-8")
    Path("web/data/dashboard.json").write_text(json.dumps({"meta": {"version": "0.22.1", "end_month": "2026-09"}, "validation": {"passed": True}}), encoding="utf-8")
    Path("web/data/manifest.json").write_text(json.dumps({"version": "0.22.1", "validation": {"passed": True}}), encoding="utf-8")
    monkeypatch.setattr(engine_v23, "build_v22", lambda *args, **kwargs: BuildResult("2026-09", 24, 24, 1, 2, 3, True))

    result = engine_v23.build("2026-09", allow_live_macro=False)

    assert result.validation_passed
    dashboard = json.loads(Path("web/data/dashboard.json").read_text(encoding="utf-8"))
    manifest = json.loads(Path("web/data/manifest.json").read_text(encoding="utf-8"))
    evidence = json.loads(Path("web/data/ar_invoice_detail.json").read_text(encoding="utf-8"))
    assert dashboard["meta"]["version"] == manifest["version"] == "0.23.0"
    assert dashboard["meta"]["ar_invoice_count"] == manifest["ar_invoice_rows"] == 1
    assert manifest["validation"]["ar_invoice_aging_max_gap"] == 0.0
    assert evidence["invoices"][0]["invoice_id"] == "SALE-2026-09-00001-US01"
    assert evidence["invoices"][0]["open_amount"] == 125.0
    assert Path("data/processed/ar_invoice_aging.csv").exists()
    assert Path("data/processed/ar_invoice_applications.csv").exists()
