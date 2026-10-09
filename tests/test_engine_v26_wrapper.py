import json
from pathlib import Path

import pandas as pd
import pytest

from enterprise_finance import engine_v26
from enterprise_finance.engine import BuildResult


def test_v26_wrapper_publishes_reconciled_analytical_invoice_ecl(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for path in ["data/processed", "web/data", "config"]:
        Path(path).mkdir(parents=True)
    config = {"provisions": {"credit_loss_rates": {"current": 0.002}}}
    Path("config/company.yml").write_text("provisions:\n  credit_loss_rates:\n    current: 0.002\n", encoding="utf-8")
    pd.DataFrame([{
        "month": "2026-09", "entity": "DE01", "division": "Hardware", "customer": "C1",
        "customer_name": "Customer One", "customer_segment": "Core", "invoice_id": "SALE-1",
        "invoice_month": "2026-09", "invoice_amount": 100.0, "cash_applied_ltd": 0.0,
        "advance_applied_ltd": 0.0, "open_amount": 100.0, "payment_terms_days": 30,
        "invoice_age_days": 0, "overdue_days": 0, "aging_bucket": "current", "risk_score": 3.0,
    }]).to_csv("data/processed/ar_invoice_aging.csv", index=False)
    pd.DataFrame([{
        "month": "2026-09", "entity": "DE01", "division": "Hardware", "customer": "C1",
        "customer_name": "Customer One", "risk_score": 3.0, "current": 100.0,
        "total_ar": 100.0, "gross_ar": 100.0, "credit_loss_allowance": 0.205,
        "net_ar": 99.795, "allowance_pct": 0.00205,
    }]).to_csv("data/processed/credit_loss_allowance.csv", index=False)
    Path("web/data/ar_invoice_detail.json").write_text(json.dumps({
        "month": "2026-09", "invoice_count": 1, "invoices": [{"invoice_id": "SALE-1"}], "applications": [],
    }), encoding="utf-8")
    Path("data/processed/validation.json").write_text(json.dumps({"passed": True}), encoding="utf-8")
    Path("web/data/dashboard.json").write_text(json.dumps({"meta": {"version": "0.25.0"}, "validation": {"passed": True}}), encoding="utf-8")
    Path("web/data/manifest.json").write_text(json.dumps({"version": "0.25.0", "validation": {"passed": True}}), encoding="utf-8")
    monkeypatch.setattr(engine_v26, "build_v25", lambda *args, **kwargs: BuildResult("2026-09", 36, 24, 1, 2, 3, True))

    result = engine_v26.build("2026-09", allow_live_macro=False)

    invoice = pd.read_csv("data/processed/ar_invoice_aging.csv").iloc[0]
    detail = json.loads(Path("web/data/ar_invoice_detail.json").read_text(encoding="utf-8"))
    manifest = json.loads(Path("web/data/manifest.json").read_text(encoding="utf-8"))
    dashboard = json.loads(Path("web/data/dashboard.json").read_text(encoding="utf-8"))
    assert result.validation_passed
    assert invoice.credit_loss_allowance == pytest.approx(0.205)
    assert invoice.net_ar == pytest.approx(99.795)
    assert "not an invoice-specific GL posting" in detail["ecl_basis"]
    assert manifest["version"] == dashboard["meta"]["version"] == "0.26.0"
    assert manifest["ar_invoice_ecl_rows"] == dashboard["meta"]["ar_invoice_ecl_count"] == 1
    assert manifest["validation"]["ar_invoice_ecl_max_gap"] == 0.0
    assert manifest["validation"]["passed"]


def test_v26_wrapper_fails_closed_when_customer_ecl_does_not_reconcile(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for path in ["data/processed", "web/data", "config"]:
        Path(path).mkdir(parents=True)
    Path("config/company.yml").write_text("{}\n", encoding="utf-8")
    pd.DataFrame([{
        "month": "2026-09", "entity": "DE01", "division": "Hardware", "customer": "C1",
        "invoice_id": "SALE-1", "aging_bucket": "current", "open_amount": 100.0, "risk_score": 3.0,
    }]).to_csv("data/processed/ar_invoice_aging.csv", index=False)
    pd.DataFrame(columns=["month", "entity", "division", "customer", "current", "total_ar", "gross_ar", "credit_loss_allowance", "net_ar", "risk_score"]).to_csv("data/processed/credit_loss_allowance.csv", index=False)
    Path("web/data/ar_invoice_detail.json").write_text(json.dumps({"invoices": [], "applications": []}), encoding="utf-8")
    monkeypatch.setattr(engine_v26, "build_v25", lambda *args, **kwargs: BuildResult("2026-09", 1, 1, 1, 1, 1, True))

    import pytest
    with pytest.raises(RuntimeError, match="failed reconciliation"):
        engine_v26.build("2026-09", allow_live_macro=False)
