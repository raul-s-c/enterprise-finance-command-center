import pandas as pd

from enterprise_finance.transaction_fx import (
    build_transaction_documents,
    build_transaction_fx_snapshots,
    summarize_transaction_fx,
    validate_transaction_fx,
)


def _fixtures():
    config = {
        "entities": [
            {"code": "DE01", "currency": "EUR"},
            {"code": "US01", "currency": "USD"},
        ]
    }
    macro = pd.DataFrame([
        {"month": "2026-01", "EUR": 1.0, "USD": 0.90, "JPY": 0.006, "CNY": 0.13, "CZK": 0.04},
        {"month": "2026-02", "EUR": 1.0, "USD": 0.95, "JPY": 0.006, "CNY": 0.13, "CZK": 0.04},
        {"month": "2026-03", "EUR": 1.0, "USD": 0.85, "JPY": 0.006, "CNY": 0.13, "CZK": 0.04},
    ])
    journal = pd.DataFrame([
        {
            "month": "2026-01", "entity": "DE01", "division": "Hardware", "journal_id": "IC-DE-US",
            "journal_type": "intercompany_sale", "account": "1150_IC_AR", "debit": 900.0, "credit": 0.0,
            "counterparty": "US01",
        },
        {
            "month": "2026-01", "entity": "US01", "division": "Hardware", "journal_id": "IC-US-DE",
            "journal_type": "intercompany_purchase", "account": "2150_IC_AP", "debit": 0.0, "credit": 1000.0,
            "counterparty": "DE01",
        },
    ])
    return config, macro, journal


def test_transaction_documents_are_cross_currency_and_source_tied():
    config, macro, journal = _fixtures()
    documents = build_transaction_documents(journal, macro, config)
    assert len(documents) == 2
    assert not documents.functional_currency.eq(documents.transaction_currency).any()
    assert set(documents.source_account) == {"1150_IC_AR", "2150_IC_AP"}
    assert documents.document_id.is_unique


def test_eur_payable_in_usd_entity_has_functional_remeasurement():
    config, macro, journal = _fixtures()
    documents = build_transaction_documents(journal, macro, config)
    snapshots = build_transaction_fx_snapshots(documents, macro, "2026-03")
    payable = snapshots[
        snapshots.document_id.eq("FX-IC-US-DE-2150_IC_AP") & snapshots.snapshot_month.eq("2026-02")
    ].iloc[0]
    assert payable.carrying_reporting_eur == 1000.0
    assert payable.monthly_fx_gain_loss_functional != 0.0
    assert payable.monthly_fx_gain_loss_eur != 0.0


def test_transaction_fx_controls_reconcile_lifecycle_and_summary():
    config, macro, journal = _fixtures()
    documents = build_transaction_documents(journal, macro, config)
    snapshots = build_transaction_fx_snapshots(documents, macro, "2026-03")
    summary = summarize_transaction_fx(snapshots)
    checks = validate_transaction_fx(documents, snapshots, summary, macro)
    assert checks["passed"] is True
    assert checks["transaction_fx_carrying_value_max_gap"] <= 0.02
    assert checks["transaction_fx_lifecycle_pnl_max_gap"] <= 0.02
    assert checks["transaction_fx_summary_pnl_max_gap"] <= 0.02
