import pandas as pd

from enterprise_finance.cash_movement_lineage import build_cash_movement_lineage


def _journal():
    return pd.DataFrame([
        {"month":"2026-09","entity":"US01","division":"Hardware","journal_id":"COLL-1","account":"1000_CASH","debit":100,"credit":0,"cash_flow_category":"customer_collections","counterparty":"EXTERNAL","description":"Customer collections"},
        {"month":"2026-09","entity":"US01","division":"Hardware","journal_id":"PAY-1","account":"1000_CASH","debit":0,"credit":70,"cash_flow_category":"supplier_payments","counterparty":"EXTERNAL","description":"Supplier payments"},
        {"month":"2026-09","entity":"US01","division":"Hardware","journal_id":"CAPEX-1","account":"1000_CASH","debit":0,"credit":20,"cash_flow_category":"capex","counterparty":"EXTERNAL","description":"Project spend"},
        {"month":"2026-09","entity":"US01","division":"Corporate","journal_id":"INT-1","account":"1000_CASH","debit":0,"credit":5,"cash_flow_category":"interest","counterparty":"Lender","description":"Interest"},
        {"month":"2026-09","entity":"US01","division":"Corporate","journal_id":"TAX-1","account":"1000_CASH","debit":0,"credit":2,"cash_flow_category":"tax","counterparty":"Tax authority","description":"Tax"},
        {"month":"2026-09","entity":"US01","division":"Corporate","journal_id":"IC-1","account":"1000_CASH","debit":3,"credit":0,"cash_flow_category":"intercompany_settlement","counterparty":"ES01","description":"Intercompany settlement"},
        {"month":"2026-09","entity":"US01","division":"Corporate","journal_id":"ICT-1","account":"1000_CASH","debit":0,"credit":4,"cash_flow_category":"intercompany_treasury","counterparty":"ES01","description":"Intercompany treasury"},
        {"month":"2026-09","entity":"US01","division":"Corporate","journal_id":"OPEN-1","account":"1000_CASH","debit":200,"credit":0,"cash_flow_category":"opening","counterparty":"Opening balance","description":"Opening cash"},
    ])


def _ar():
    return pd.DataFrame([
        {"application_month":"2026-09","entity":"US01","division":"Hardware","source_journal_id":"COLL-1","allocation_type":"cash_collection","applied_amount":60,"invoice_id":"INV-1","customer":"CUS-1"},
        {"application_month":"2026-09","entity":"US01","division":"Hardware","source_journal_id":"COLL-1","allocation_type":"cash_collection","applied_amount":40,"invoice_id":"INV-2","customer":"CUS-2"},
    ])


def _ap():
    return pd.DataFrame([
        {"application_month":"2026-09","entity":"US01","posted_division":"Hardware","reduction_journal_id":"PAY-1","accrual_journal_id":"AP-1","applied_amount":50,"supplier":"SUP-1","supplier_name":"Supplier One"},
        {"application_month":"2026-09","entity":"US01","posted_division":"Hardware","reduction_journal_id":"PAY-1","accrual_journal_id":"AP-2","applied_amount":20,"supplier":"SUP-2","supplier_name":"Supplier Two"},
    ])


def _capex():
    return pd.DataFrame([
        {"month":"2026-09","journal_id":"CAPEX-1","event":"SPEND","project":"PROJECT-1","project_name":"Factory automation","amount":20},
        {"month":"2026-09","journal_id":"GOLIVE-1","event":"GO_LIVE","project":"PROJECT-2","project_name":"Cloud platform","amount":12},
    ])


def _expected():
    return pd.DataFrame([{
        "month":"2026-09","entity":"US01",
        "customer_collections":100,"supplier_payments":-70,"capex":-20,
        "interest":-5,"tax":-2,"debt_repayment":0,
        "intercompany_settlement":3,"intercompany_treasury":-4,"opening":200,
    }])


def test_current_close_cash_allocations_reconcile_to_journal_and_cash_flow():
    rows, checks = build_cash_movement_lineage(_journal(), _ar(), _ap(), _capex(), _expected(), "2026-09")

    assert checks["passed"]
    assert checks["cash_movement_lineage_max_gap"] == 0
    assert checks["cash_movement_journal_max_gap"] == 0
    assert checks["cash_movement_cashflow_max_gap"] == 0
    assert checks["cash_movement_lineage_rows"] == 10
    assert rows.loc[rows.cash_flow_category.eq("customer_collections"), "movement_amount"].sum() == 100
    assert rows.loc[rows.cash_flow_category.eq("supplier_payments"), "movement_amount"].sum() == -70
    assert rows.loc[rows.cash_flow_category.eq("capex"), "movement_amount"].tolist() == [-20]
    assert set(rows.loc[rows.cash_flow_category.eq("customer_collections"), "source_record_id"]) == {"INV-1", "INV-2"}
    assert set(rows.loc[rows.cash_flow_category.eq("supplier_payments"), "source_record_id"]) == {"AP-1", "AP-2"}
    assert rows.loc[rows.cash_flow_category.eq("capex"), "source_record_type"].tolist() == ["CAPEX project event"]
    assert not rows.source_journal_id.duplicated().all()


def test_unallocated_aggregate_collection_is_not_mislabeled_as_invoice_evidence():
    rows, checks = build_cash_movement_lineage(
        _journal(), _ar().iloc[0:0], _ap(), _capex(), _expected(), "2026-09"
    )

    collection = rows.loc[rows.cash_flow_category.eq("customer_collections")].iloc[0]
    assert not checks["passed"]
    assert checks["cash_movement_unlinked_collection_journals"] == 1
    assert collection.source_record_type == "Cash journal posting"
    assert collection.source_record_id == "COLL-1"
    assert "no supporting subledger allocation" in collection.allocation_basis


def test_analytical_allocation_amount_must_match_posted_cash_journal():
    ar = _ar().copy()
    ar.loc[1, "applied_amount"] = 30
    rows, checks = build_cash_movement_lineage(_journal(), ar, _ap(), _capex(), _expected(), "2026-09")

    assert not checks["passed"]
    assert checks["cash_movement_lineage_max_gap"] == 10
    assert rows.loc[rows.cash_flow_category.eq("customer_collections")].empty


def test_non_cash_go_live_is_not_classified_as_capex_cash_spend():
    rows, checks = build_cash_movement_lineage(_journal(), _ar(), _ap(), _capex(), _expected(), "2026-09")

    assert checks["passed"]
    capex = rows.loc[rows.cash_flow_category.eq("capex")]
    assert capex.source_record_id.tolist() == ["PROJECT-1"]
    assert "PROJECT-2" not in set(capex.source_record_id)
