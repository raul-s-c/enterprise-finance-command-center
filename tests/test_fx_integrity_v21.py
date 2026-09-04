import pandas as pd
import pytest

from enterprise_finance.transaction_fx import (
    build_intercompany_contracts, build_transaction_documents, build_transaction_fx_snapshots,
    summarize_transaction_fx, validate_transaction_fx,
)


def fixture():
    config = {"entities": [{"code": "CN01", "currency": "CNY"}, {"code": "US01", "currency": "USD"}]}
    macro = pd.DataFrame([
        {"month": month, "EUR": 1., "USD": usd, "CNY": .13, "JPY": .006, "CZK": .04}
        for month, usd in [("2026-07", .9), ("2026-08", .95), ("2026-09", .85)]
    ])
    journal = pd.DataFrame([
        dict(month="2026-07", entity="CN01", counterparty="US01", division="Hardware", journal_id="SALE",
             journal_type="intercompany_sale", account="1150_IC_AR", debit=1000., credit=0.),
        dict(month="2026-07", entity="US01", counterparty="CN01", division="Hardware", journal_id="BUY",
             journal_type="intercompany_purchase", account="2150_IC_AP", debit=0., credit=1000.),
    ])
    contracts = build_intercompany_contracts(journal, macro, config)
    docs = build_transaction_documents(journal, macro, config)
    snaps = build_transaction_fx_snapshots(docs, macro, "2026-09")
    return config, macro, journal, contracts, docs, snaps, summarize_transaction_fx(snaps)


def validate(parts):
    config, macro, journal, contracts, docs, snaps, summary = parts
    return validate_transaction_fx(docs, snaps, summary, macro, end_month="2026-09",
                                   journal=journal, config=config, contracts=contracts)


def test_shared_intercompany_contract_and_source_reconciliation():
    parts = fixture()
    contract, doc = parts[3].iloc[0], parts[4].iloc[0]
    assert contract.transaction_currency == doc.transaction_currency == "CNY"
    assert doc.entity == "US01"
    assert contract.settlement_month == doc.settlement_month
    assert contract.contract_id == doc.contract_id
    assert contract.receivable_journal_id == "SALE"
    assert contract.payable_journal_id == doc.source_journal_id == "BUY"
    assert validate(parts)["passed"]


def test_coordinated_million_euro_summary_corruption_is_rejected():
    parts = fixture()
    parts[-1].loc[0, ["total_fx_gain_loss_eur", "realized_fx_gain_loss_eur"]] += 1_000_000
    checks = validate(parts)
    assert not checks["passed"]
    assert checks["transaction_fx_summary_source_max_gap"] == 1_000_000


@pytest.mark.parametrize("column", ["open_documents", "gross_receivable_eur", "gross_payable_eur", "net_exposure_eur"])
def test_summary_exposure_and_counts_reconcile_to_snapshots(column):
    parts = fixture()
    parts[-1].loc[0, column] += 10
    assert not validate(parts)["passed"]


@pytest.mark.parametrize("mutation", ["missing", "extra", "duplicate", "nan", "scope"])
def test_summary_coverage_and_finite_values(mutation):
    parts = list(fixture())
    summary = parts[-1]
    if mutation == "missing":
        parts[-1] = summary.iloc[1:].copy()
    elif mutation in {"extra", "duplicate"}:
        extra = summary.iloc[[0]].copy()
        if mutation == "extra":
            extra["entity"] = "ORPHAN"
        parts[-1] = pd.concat([summary, extra], ignore_index=True)
    elif mutation == "nan":
        summary.loc[0, "net_exposure_eur"] = float("nan")
    else:
        summary.loc[0, "entity"] = "ORPHAN"
    assert not validate(parts)["passed"]


@pytest.mark.parametrize("mutation", ["missing_snapshot", "orphan", "amount", "status", "source", "currency", "terms"])
def test_document_lifecycle_and_contract_mutations_are_rejected(mutation):
    parts = list(fixture())
    if mutation == "missing_snapshot":
        parts[5] = parts[5].iloc[1:].copy()
    elif mutation == "orphan":
        parts[5].loc[0, "document_id"] = "ORPHAN"
    elif mutation == "amount":
        parts[5].loc[0, "monthly_fx_gain_loss_eur"] += 10
    elif mutation == "status":
        parts[5].loc[0, "status"] = "Settled"
    elif mutation == "source":
        parts[4].loc[0, "original_reporting_eur"] += 100
    elif mutation == "currency":
        parts[3].loc[0, "transaction_currency"] = "USD"
    else:
        parts[3].loc[0, "settlement_month"] = "2026-12"
    assert not validate(parts)["passed"]


@pytest.mark.parametrize("mutation", ["missing_leg", "duplicate_leg", "amount"])
def test_intercompany_source_legs_must_match(mutation):
    config, macro, journal, *_ = fixture()
    if mutation == "missing_leg":
        journal = journal.iloc[:1]
    elif mutation == "duplicate_leg":
        journal = pd.concat([journal, journal.iloc[:1]])
    else:
        journal.loc[1, "credit"] += 1
    with pytest.raises(ValueError, match="Intercompany contract"):
        build_intercompany_contracts(journal, macro, config)
