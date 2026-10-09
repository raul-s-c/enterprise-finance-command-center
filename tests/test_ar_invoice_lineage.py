import pandas as pd
import pytest

from enterprise_finance.ar_invoice_lineage import build_ar_invoice_lineage
from enterprise_finance.customer_receivables_v10 import build_ar_aging_with_contracts


def fixtures():
    rows = [
        ("2026-01", "SALE-A1", "sale", "A", "P1", 100.0, 0.0),
        ("2026-01", "SALE-A2", "sale", "A", "P2", 40.0, 0.0),
        ("2026-01", "SALE-B1", "sale", "B", "P1", 80.0, 0.0),
        ("2026-01", "COLL-JAN", "collection", "", "", 0.0, 50.0),
        ("2026-02", "SALE-A3", "sale", "A", "P1", 50.0, 0.0),
        ("2026-02", "ADV-APPLY-A", "contract_liability_application", "A", "P1", 0.0, 20.0),
        ("2026-02", "COLL-FEB", "collection", "", "", 0.0, 40.0),
    ]
    journal = pd.DataFrame([
        dict(month=month, entity="ES01", division="Hardware", account="1100_AR",
             journal_id=jid, journal_type=kind, customer=customer, product=product,
             debit=debit, credit=credit)
        for month, jid, kind, customer, product, debit, credit in rows
    ])
    customers = pd.DataFrame([
        dict(customer="A", customer_name="Alpha", segment="Strategic", customer_size=1.0),
        dict(customer="B", customer_name="Beta", segment="Growth", customer_size=1.0),
    ])
    return journal, customers, {"working_capital": {"payment_terms_days": {"Hardware": 30}}}


def test_invoice_open_items_and_applications_reconcile_customer_schedule():
    journal, customers, config = fixtures()
    customer_aging = build_ar_aging_with_contracts(journal, customers, config)
    before = journal.copy(deep=True)
    invoices, applications, checks = build_ar_invoice_lineage(
        journal, customers, config, "2026-02", customer_aging
    )

    assert checks["passed"]
    assert checks["ar_invoice_aging_max_gap"] <= 0.05
    assert checks["ar_invoice_application_max_gap"] <= 0.05
    assert abs(invoices.open_amount.sum() - 160.0) < 0.01
    assert set(invoices.invoice_id) == {"SALE-A2", "SALE-A3", "SALE-B1"}
    assert set(applications.source_journal_id) == {"COLL-JAN", "ADV-APPLY-A", "COLL-FEB"}
    assert applications.applied_amount.sum() == pytest.approx(110.0)
    assert applications.allocation_basis.str.contains("Modeled").all()
    assert invoices.evidence_basis.str.contains("not bank matched").all()

    actual_by_customer = invoices.groupby("customer").open_amount.sum().sort_index()
    expected_by_customer = customer_aging.loc[customer_aging.month.eq("2026-02")].set_index("customer").total_ar.sort_index()
    pd.testing.assert_series_equal(actual_by_customer, expected_by_customer, check_names=False)
    pd.testing.assert_frame_equal(journal, before)


def test_duplicate_invoice_identity_and_overapplication_fail_closed():
    journal, customers, config = fixtures()
    duplicate = pd.concat([journal, journal.iloc[[0]]], ignore_index=True)
    customer_aging = build_ar_aging_with_contracts(duplicate, customers, config)
    with pytest.raises(ValueError, match="unique"):
        build_ar_invoice_lineage(duplicate, customers, config, "2026-02", customer_aging)

    customer_aging = build_ar_aging_with_contracts(journal, customers, config)
    journal.loc[journal.journal_id.eq("COLL-FEB"), "credit"] = 500.0
    with pytest.raises(RuntimeError, match="exceeds modeled open invoices"):
        build_ar_invoice_lineage(journal, customers, config, "2026-02", customer_aging)


def test_missing_invoice_source_identity_is_not_reconstructed_from_customer_totals():
    journal, customers, config = fixtures()
    customer_aging = build_ar_aging_with_contracts(journal, customers, config)
    journal.loc[journal.journal_type.eq("sale") & journal.journal_id.eq("SALE-A1"), "journal_id"] = ""
    with pytest.raises(ValueError, match="unique"):
        build_ar_invoice_lineage(journal, customers, config, "2026-02", customer_aging)


def test_receivable_without_sales_or_with_missing_credit_source_fails_closed():
    journal, customers, config = fixtures()
    no_sales = journal.loc[journal.journal_type.ne("sale")].copy()
    empty_schedule = build_ar_aging_with_contracts(no_sales, customers, config)
    _, _, checks = build_ar_invoice_lineage(no_sales, customers, config, "2026-02", empty_schedule)
    assert not checks["passed"]

    customer_aging = build_ar_aging_with_contracts(journal, customers, config)
    journal.loc[journal.journal_type.eq("collection") & journal.month.eq("2026-02"), "journal_id"] = ""
    with pytest.raises(ValueError, match="source journal IDs"):
        build_ar_invoice_lineage(journal, customers, config, "2026-02", customer_aging)
