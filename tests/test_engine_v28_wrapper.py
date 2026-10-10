import gzip
import json
from pathlib import Path

import pandas as pd

from enterprise_finance import engine_v28
from enterprise_finance.engine import BuildResult


def _prepare_close(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for path in ["data/runtime", "data/processed", "web/data"]:
        Path(path).mkdir(parents=True)

    journal = pd.DataFrame([
        {"month":"2026-09","entity":"US01","division":"Hardware","journal_id":"COLL-1","account":"1000_CASH","debit":100,"credit":0,"cash_flow_category":"customer_collections","counterparty":"EXTERNAL","description":"Collections"},
        {"month":"2026-09","entity":"US01","division":"Hardware","journal_id":"PAY-1","account":"1000_CASH","debit":0,"credit":70,"cash_flow_category":"supplier_payments","counterparty":"EXTERNAL","description":"Supplier payments"},
        {"month":"2026-09","entity":"US01","division":"Hardware","journal_id":"CAPEX-1","account":"1000_CASH","debit":0,"credit":20,"cash_flow_category":"capex","counterparty":"EXTERNAL","description":"Project spend"},
    ])
    journal.to_csv("data/runtime/journal.csv.gz", index=False, compression="gzip")
    pd.DataFrame([
        {"application_month":"2026-09","entity":"US01","division":"Hardware","source_journal_id":"COLL-1","allocation_type":"cash_collection","applied_amount":100,"invoice_id":"INV-1","customer":"CUS-1"}
    ]).to_csv("data/processed/ar_invoice_applications.csv", index=False)
    pd.DataFrame([
        {"application_month":"2026-09","entity":"US01","posted_division":"Hardware","reduction_journal_id":"PAY-1","accrual_journal_id":"AP-1","applied_amount":70,"supplier":"SUP-1","supplier_name":"Supplier One"}
    ]).to_csv("data/processed/ap_item_applications.csv", index=False)
    pd.DataFrame([
        {"month":"2026-09","journal_id":"CAPEX-1","event":"SPEND","project":"PROJECT-1","project_name":"Factory automation","amount":20}
    ]).to_csv("data/processed/fixed_asset_project_events.csv", index=False)
    cash_flow = [{
        "month":"2026-09","entity":"US01","customer_collections":100,
        "supplier_payments":-70,"capex":-20,"interest":0,"tax":0,
        "debt_repayment":0,"intercompany_settlement":0,"opening":0,
        "operating_cash_flow":30,"investing_cash_flow":-20,
        "financing_cash_flow":0,"net_cash_movement":10,"free_cash_flow":10,
    }]
    Path("web/data/dashboard.json").write_text(json.dumps({
        "meta":{"version":"0.27.1","end_month":"2026-09"},
        "validation":{"passed":True},
        "cash_flow_detail":cash_flow,
    }), encoding="utf-8")
    Path("data/processed/validation.json").write_text(json.dumps({"passed":True}), encoding="utf-8")
    Path("web/data/manifest.json").write_text(json.dumps({"version":"0.27.1","validation":{"passed":True}}), encoding="utf-8")
    monkeypatch.setattr(engine_v28, "build_v27", lambda *args, **kwargs: BuildResult("2026-09", 36, 24, 1, 3, 2, True))


def test_v28_wrapper_publishes_cash_lineage_and_reconciliation(tmp_path, monkeypatch):
    _prepare_close(tmp_path, monkeypatch)

    result = engine_v28.build("2026-09", allow_live_macro=False)

    dashboard = json.loads(Path("web/data/dashboard.json").read_text(encoding="utf-8"))
    manifest = json.loads(Path("web/data/manifest.json").read_text(encoding="utf-8"))
    validation = json.loads(Path("data/processed/validation.json").read_text(encoding="utf-8"))
    lineage = pd.read_csv("data/processed/cash_movement_lineage.csv")
    assert result.validation_passed
    assert dashboard["meta"]["version"] == manifest["version"] == engine_v28.VERSION
    assert dashboard["validation"] == manifest["validation"] == validation
    assert dashboard["validation"]["passed"]
    assert dashboard["meta"]["cash_movement_lineage_count"] == manifest["cash_movement_lineage_rows"] == len(lineage) == 3
    assert manifest["cash_movement_detail_bytes"] > 0
    assert {row["source_record_type"] for row in dashboard["cash_movement_lineage"]} == {
        "Customer invoice allocation","Supplier accrual allocation","CAPEX project event"
    }
