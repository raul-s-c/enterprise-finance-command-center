import json
from pathlib import Path

import pandas as pd
import yaml

from enterprise_finance.engine import BuildResult
from enterprise_finance import engine_v24
from enterprise_finance.supplier_payables import build_ap_aging


def test_release_wrapper_publishes_reconciled_ap_source_items(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("data/processed").mkdir(parents=True)
    Path("data/runtime").mkdir(parents=True)
    Path("web/data").mkdir(parents=True)
    config = {"divisions": {"Hardware": {"dpo": 45}}}
    Path("config").mkdir()
    Path("config/company.yml").write_text(yaml.safe_dump(config), encoding="utf-8")

    journal = pd.DataFrame([
        dict(month="2026-09", entity="US01", division="Hardware", account="2100_AP",
             journal_id="ACCRUAL-2026-09-001", journal_type="factory_cost", debit=0.0,
             credit=125.0, product="HW-1", customer="C1"),
        dict(month="2026-09", entity="US01", division="Hardware", account="2100_AP",
             journal_id="PAY-2026-09-001", journal_type="supplier_payment", debit=25.0,
             credit=0.0, product="", customer=""),
    ])
    journal.to_csv("data/runtime/journal.csv.gz", index=False, compression="gzip")
    build_ap_aging(journal, config).to_csv("data/processed/ap_aging.csv", index=False)
    Path("data/processed/validation.json").write_text(json.dumps({"passed": True}), encoding="utf-8")
    Path("web/data/dashboard.json").write_text(json.dumps({"meta": {"version": "0.23.0", "end_month": "2026-09"}, "validation": {"passed": True}}), encoding="utf-8")
    Path("web/data/manifest.json").write_text(json.dumps({"version": "0.23.0", "validation": {"passed": True}}), encoding="utf-8")
    monkeypatch.setattr(engine_v24, "build_v23", lambda *args, **kwargs: BuildResult("2026-09", 24, 24, 1, 2, 3, True))

    result = engine_v24.build("2026-09", allow_live_macro=False)

    assert result.validation_passed
    dashboard = json.loads(Path("web/data/dashboard.json").read_text(encoding="utf-8"))
    manifest = json.loads(Path("web/data/manifest.json").read_text(encoding="utf-8"))
    evidence = json.loads(Path("web/data/ap_item_detail.json").read_text(encoding="utf-8"))
    assert dashboard["meta"]["version"] == manifest["version"] == "0.24.0"
    assert dashboard["meta"]["ap_item_count"] == manifest["ap_item_rows"] == evidence["item_count"] == 1
    assert evidence["items"][0]["source_item_id"] == "ACCRUAL-2026-09-001"
    assert evidence["items"][0]["open_amount"] == 100.0
    assert manifest["validation"]["ap_item_aging_max_gap"] == 0.0
    assert Path("data/processed/ap_item_aging.csv").exists()
    assert Path("data/processed/ap_item_applications.csv").exists()
