import pandas as pd
import numpy as np
import pytest

from enterprise_finance.ar_invoice_lineage import build_ar_invoice_lineage
from enterprise_finance.customer_receivables_v10 import build_ar_aging_with_contracts
from enterprise_finance.invoice_credit_loss_lineage import EVIDENCE_BASIS, build_invoice_credit_loss_lineage
from enterprise_finance.provisions import build_credit_loss_schedule


def fixture_data():
    entries = [
        ("2026-01", "SALE-A1", "sale", "A", "P1", 100.0, 0.0),
        ("2026-01", "SALE-A2", "sale", "A", "P2", 40.0, 0.0),
        ("2026-01", "SALE-B1", "sale", "B", "P1", 80.0, 0.0),
        ("2026-01", "COLL-JAN", "collection", "", "", 0.0, 50.0),
        ("2026-02", "SALE-A3", "sale", "A", "P1", 50.0, 0.0),
        ("2026-02", "ADV-APPLY-A", "contract_liability_application", "A", "P1", 0.0, 20.0),
        ("2026-02", "COLL-FEB", "collection", "", "", 0.0, 40.0),
    ]
    journal = pd.DataFrame([
        dict(month=m, entity="ES01", division="Hardware", account="1100_AR", journal_id=jid,
             journal_type=kind, customer=customer, product=product, debit=debit, credit=credit)
        for m, jid, kind, customer, product, debit, credit in entries
    ])
    customers = pd.DataFrame([
        dict(customer="A", customer_name="Alpha", segment="Strategic", customer_size=1.0),
        dict(customer="B", customer_name="Beta", segment="Growth", customer_size=1.0),
    ])
    config = {"working_capital": {"payment_terms_days": {"Hardware": 30}}}
    aging = build_ar_aging_with_contracts(journal, customers, config)
    invoices, _, ar_checks = build_ar_invoice_lineage(journal, customers, config, "2026-02", aging)
    assert ar_checks["passed"]
    customer_ecl = build_credit_loss_schedule(aging, config)
    return invoices, customer_ecl, config


def test_invoice_ecl_reconciles_to_existing_customer_schedule():
    invoices, customer_ecl, config = fixture_data()
    before = invoices.copy(deep=True)
    detail, checks = build_invoice_credit_loss_lineage(invoices, customer_ecl, config, "2026-02")

    assert checks["passed"]
    assert checks["ar_invoice_ecl_max_gap"] <= 0.05
    assert checks["ar_invoice_ecl_unmatched_customers"] == 0
    assert detail.open_amount.sum() == pytest.approx(160.0)
    assert detail.credit_loss_allowance.sum() == pytest.approx(
        customer_ecl.loc[customer_ecl.month.eq("2026-02"), "credit_loss_allowance"].sum()
    )
    np.testing.assert_allclose(detail.net_ar, detail.open_amount - detail.credit_loss_allowance)
    assert detail.evidence_basis.eq(EVIDENCE_BASIS).all()
    pd.testing.assert_frame_equal(invoices, before)


def test_invoice_ecl_uses_configured_rates_and_caps_at_open_amount():
    invoices, customer_ecl, config = fixture_data()
    config["provisions"] = {"credit_loss_rates": {"current": 0.02, "overdue_1_30": 1.5}}
    detail, checks = build_invoice_credit_loss_lineage(invoices, customer_ecl, config, "2026-02")
    assert detail.credit_loss_allowance.le(detail.open_amount).all()
    # The intentionally changed policy no longer ties to the published customer schedule.
    assert not checks["passed"]


@pytest.mark.parametrize("mutation,match", [
    (lambda df: df.assign(invoice_id=""), "unique"),
    (lambda df: df.assign(open_amount=float("nan")), "non-finite"),
    (lambda df: df.assign(aging_bucket="unmapped"), "Unsupported"),
    (lambda df: df.assign(open_amount=-1.0), "negative"),
])
def test_invalid_invoice_ecl_inputs_fail_closed(mutation, match):
    invoices, customer_ecl, config = fixture_data()
    with pytest.raises(ValueError, match=match):
        build_invoice_credit_loss_lineage(mutation(invoices), customer_ecl, config, "2026-02")


def test_missing_customer_schedule_match_fails_reconciliation():
    invoices, customer_ecl, config = fixture_data()
    orphaned = customer_ecl.loc[customer_ecl.customer.ne("B")]
    _, checks = build_invoice_credit_loss_lineage(invoices, orphaned, config, "2026-02")
    assert not checks["passed"]
    assert checks["ar_invoice_ecl_unmatched_customers"] == 1


def test_empty_invoice_scope_has_zero_ecl_and_passes_only_when_schedule_empty():
    empty = pd.DataFrame()
    detail, checks = build_invoice_credit_loss_lineage(empty, empty, {}, "2026-02")
    assert detail.empty
    assert checks["passed"]
    assert checks["ar_invoice_ecl_max_gap"] == 0.0
