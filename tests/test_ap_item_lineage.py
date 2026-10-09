import pandas as pd
import pytest

from enterprise_finance.accounting import build_accounting
from enterprise_finance.ap_item_lineage import build_ap_item_lineage
from enterprise_finance.engine import load_config, month_range
from enterprise_finance.macro import build_macro
from enterprise_finance.model import simulate_operations
from enterprise_finance.supplier_payables import build_ap_aging


def fixture():
    journal = pd.DataFrame([
        dict(month="2026-01", entity="ES01", division="Hardware", account="2100_AP",
             journal_id="ACCRUAL-1", journal_type="factory_cost", debit=0.0, credit=100.0,
             product="HW-1", customer="C1"),
        dict(month="2026-01", entity="ES01", division="Hardware", account="2100_AP",
             journal_id="ACCRUAL-2", journal_type="factory_cost", debit=0.0, credit=75.0,
             product="HW-2", customer="C2"),
        dict(month="2026-01", entity="ES01", division="Hardware", account="2100_AP",
             journal_id="PAYMENT-1", journal_type="supplier_payment", debit=10.0, credit=0.0,
             product="", customer=""),
        dict(month="2026-02", entity="ES01", division="Hardware", account="2100_AP",
             journal_id="ACCRUAL-3", journal_type="factory_cost", debit=0.0, credit=60.0,
             product="HW-3", customer="C3"),
        dict(month="2026-02", entity="ES01", division="Hardware", account="2100_AP",
             journal_id="PAYMENT-2", journal_type="supplier_payment", debit=10.0, credit=0.0,
             product="", customer=""),
    ])
    config = {"divisions": {"Hardware": {"dpo": 45}}}
    return journal, config


def test_source_accrual_items_reconcile_supplier_buckets_and_reduction_sources():
    journal, config = fixture()
    supplier_aging = build_ap_aging(journal, config)
    before = journal.copy(deep=True)
    items, applications, checks = build_ap_item_lineage(
        journal, config, "2026-02", supplier_aging
    )

    assert checks["passed"]
    assert checks["ap_item_aging_max_gap"] <= 0.05
    assert checks["ap_item_application_max_gap"] <= 0.05
    assert set(items.source_item_id) == {"ACCRUAL-1", "ACCRUAL-2", "ACCRUAL-3"}
    assert set(applications.reduction_journal_id) == {"PAYMENT-1", "PAYMENT-2"}
    assert applications.applied_amount.sum() == pytest.approx(20.0)
    assert applications.allocation_basis.str.contains("Modeled").all()
    assert items.evidence_basis.str.contains("not supplier invoice").all()
    assert items.open_amount.sum() == pytest.approx(supplier_aging.loc[
        supplier_aging.month.eq("2026-02"), "total_ap"
    ].sum())
    pd.testing.assert_frame_equal(journal, before)


def test_missing_source_ids_and_reductions_exceeding_open_ap_fail_closed():
    journal, config = fixture()
    supplier_aging = build_ap_aging(journal, config)
    journal.loc[journal.journal_id.eq("ACCRUAL-1"), "journal_id"] = ""
    with pytest.raises(ValueError, match="unique, non-empty"):
        build_ap_item_lineage(journal, config, "2026-02", supplier_aging)

    journal, config = fixture()
    supplier_aging = build_ap_aging(journal, config)
    journal.loc[journal.journal_id.eq("PAYMENT-2"), "debit"] = 500.0
    with pytest.raises(RuntimeError, match="exceeds modeled open accruals"):
        build_ap_item_lineage(journal, config, "2026-02", supplier_aging)


def test_generated_ap_source_items_reconcile_to_existing_supplier_aging():
    config = load_config()
    months = month_range("2026-08", 8)
    macro = build_macro(months, config["group"]["seed"], allow_live=False)
    operations = simulate_operations(config, months, macro).operations
    journal = build_accounting(config, months, macro, operations).journal
    supplier_aging = build_ap_aging(journal, config)

    items, applications, checks = build_ap_item_lineage(
        journal, config, months[-1], supplier_aging
    )

    assert checks["passed"]
    assert checks["ap_item_aging_max_gap"] <= 0.05
    assert checks["ap_item_application_max_gap"] <= 0.05
    assert len(items) > 0
    assert len(applications) > 0
    assert items.source_item_id.is_unique
    assert items.evidence_basis.str.contains("not supplier invoice").all()
