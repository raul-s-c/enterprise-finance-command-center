import pandas as pd
import pytest

from enterprise_finance.fixed_asset_lineage import build_fixed_asset_lineage


def fixture():
    project = {
        "id": "CAPEX-TEST-01", "name": "Assembly cell", "entity": "CZ01",
        "division": "Hardware", "budget": 100.0, "start": "2026-01",
        "build_months": 2, "useful_life_months": 10, "capacity_increase_pct": 0.15,
    }
    events = pd.DataFrame([
        {"month": "2026-01", "project": project["id"], "project_name": project["name"],
         "entity": project["entity"], "division": project["division"], "event": "SPEND",
         "amount": 40.0, "go_live": "2026-02", "useful_life_months": 10, "capacity_increase_pct": 0.15},
        {"month": "2026-02", "project": project["id"], "project_name": project["name"],
         "entity": project["entity"], "division": project["division"], "event": "SPEND",
         "amount": 60.0, "go_live": "2026-02", "useful_life_months": 10, "capacity_increase_pct": 0.15},
        {"month": "2026-02", "project": project["id"], "project_name": project["name"],
         "entity": project["entity"], "division": project["division"], "event": "GO_LIVE",
         "amount": 100.0, "go_live": "2026-02", "useful_life_months": 10, "capacity_increase_pct": 0.15},
    ])

    def entry(month, entity, division, journal_id, journal_type, account, debit=0.0, credit=0.0):
        return {"month": month, "entity": entity, "division": division, "journal_id": journal_id,
                "journal_type": journal_type, "account": account, "debit": debit, "credit": credit}

    journal = pd.DataFrame([
        entry("2026-01", "CZ01", "Hardware", "CAPEX-2026-01-CAPEX-TEST-01", "capex", "1510_CIP", debit=40),
        entry("2026-01", "CZ01", "Hardware", "CAPEX-2026-01-CAPEX-TEST-01", "capex", "1000_CASH", credit=40),
        entry("2026-02", "CZ01", "Hardware", "CAPEX-2026-02-CAPEX-TEST-01", "capex", "1510_CIP", debit=60),
        entry("2026-02", "CZ01", "Hardware", "CAPEX-2026-02-CAPEX-TEST-01", "capex", "1000_CASH", credit=60),
        entry("2026-02", "CZ01", "Hardware", "GOLIVE-2026-02-CAPEX-TEST-01", "capex_transfer", "1500_PPE", debit=100),
        entry("2026-02", "CZ01", "Hardware", "GOLIVE-2026-02-CAPEX-TEST-01", "capex_transfer", "1510_CIP", credit=100),
        entry("2026-03", "CZ01", "Corporate", "DEP-2026-03-CZ01", "depreciation", "6100_DEPRECIATION", debit=10),
        entry("2026-03", "CZ01", "Corporate", "DEP-2026-03-CZ01", "depreciation", "1590_ACCUM_DEP", credit=10),
    ])
    config = {"capex_projects": [project]}
    return journal, events, config


def test_project_register_reconciles_spend_go_live_and_aggregated_depreciation():
    journal, events, config = fixture()
    register, trace, checks = build_fixed_asset_lineage(journal, events, config, "2026-03")

    assert checks["passed"]
    row = register.iloc[0]
    assert row.status == "In service"
    assert row.cash_spend_ltd == pytest.approx(100.0)
    assert row.cip_closing == pytest.approx(0.0)
    assert row.gross_ppe == pytest.approx(100.0)
    assert row.depreciation_ltd_modeled == pytest.approx(10.0)
    assert row.net_book_value == pytest.approx(90.0)
    assert set(trace.journal_id) == {
        "CAPEX-2026-01-CAPEX-TEST-01", "CAPEX-2026-02-CAPEX-TEST-01",
        "GOLIVE-2026-02-CAPEX-TEST-01",
    }
    assert trace.event.str.contains("SPEND|GO_LIVE").all()
    assert "aggregated by entity" in row.depreciation_basis


def test_source_event_mismatch_fails_closed():
    journal, events, config = fixture()
    events.loc[events.event.eq("SPEND") & events.month.eq("2026-01"), "amount"] = 99.0
    with pytest.raises(RuntimeError, match="does not match journal"):
        build_fixed_asset_lineage(journal, events, config, "2026-03")


def test_duplicate_project_events_are_rejected():
    journal, events, config = fixture()
    events = pd.concat([events, events.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="must be unique"):
        build_fixed_asset_lineage(journal, events, config, "2026-03")


def test_missing_aggregated_depreciation_posting_fails_reconciliation():
    journal, events, config = fixture()
    journal = journal.loc[~journal.journal_type.eq("depreciation")].copy()
    journal.loc[len(journal)] = {
        "month": "2026-03", "entity": "CZ01", "division": "Hardware", "journal_id": "OTHER-MARCH",
        "journal_type": "sale", "account": "4000_EXTERNAL_REVENUE", "debit": 0.0, "credit": 1.0,
    }
    _, _, checks = build_fixed_asset_lineage(journal, events, config, "2026-03")
    assert not checks["passed"]
    assert checks["fixed_asset_depreciation_max_gap"] == pytest.approx(10.0)
