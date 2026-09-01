from pathlib import Path
import json

import pandas as pd
import yaml

from enterprise_finance.accounting import build_accounting
from enterprise_finance.engine import load_config, month_range
from enterprise_finance.engine_v08 import build as build_v08
from enterprise_finance.macro import build_macro
from enterprise_finance.model import simulate_operations
from enterprise_finance.supplier_payables import (
    AP_BUCKETS,
    ap_aging_summary,
    build_ap_aging,
    supplier_concentration,
    supplier_master,
    validate_ap_aging,
)


def _fixture(periods=8):
    config = load_config()
    months = month_range("2026-08", periods)
    macro = build_macro(months, config["group"]["seed"], allow_live=False)
    simulation = simulate_operations(config, months, macro)
    accounting = build_accounting(config, months, macro, simulation.operations)
    return config, accounting


def test_ap_aging_reconciles_to_legal_payables():
    config, accounting = _fixture(8)
    schedule = build_ap_aging(accounting.journal, config)
    assert not schedule.empty
    assert schedule.supplier.nunique() >= 20
    assert (schedule.total_ap >= -0.005).all()
    assert (schedule[AP_BUCKETS].sum(axis=1) - schedule.total_ap).abs().max() <= 0.05

    checks = validate_ap_aging(accounting.journal, schedule)
    assert checks["passed"]
    assert checks["ap_subledger_max_gap"] <= 0.05
    assert checks["ap_aging_bucket_max_gap"] <= 0.05
    assert checks["ap_negative_supplier_balances"] == 0
    assert checks["supplier_concentration_out_of_range"] == 0

    summary = ap_aging_summary(schedule)
    assert not summary.empty
    assert summary.top5_spend_concentration.between(0.0, 1.0).all()
    assert (summary.trailing_12m_supplier_count >= summary.supplier_count).all()

    latest = supplier_concentration(schedule, "2026-08")
    assert not latest.empty
    assert latest.supplier_spend_share.between(0.0, 1.0).all()
    assert set(latest.risk_flag.unique()).issubset({"Normal", "Payment overdue", "High concentration", "Single-source critical"})

    master = supplier_master(schedule)
    assert master.supplier.is_unique
    assert master.supplier_criticality.between(1, 5).all()


def test_supplier_derivation_is_deterministic():
    config, accounting = _fixture(6)
    first = build_ap_aging(accounting.journal, config)
    second = build_ap_aging(accounting.journal, config)
    cols = ["month", "entity", "division", "supplier", "total_ap", "trailing_12m_spend"]
    pd.testing.assert_frame_equal(
        first[cols].sort_values(cols[:4]).reset_index(drop=True),
        second[cols].sort_values(cols[:4]).reset_index(drop=True),
    )


def test_v08_full_close_outputs_supplier_schedules(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    source_config = Path(__file__).resolve().parents[1] / "config" / "company.yml"
    config = yaml.safe_load(source_config.read_text(encoding="utf-8"))
    config["group"]["actual_months"] = 8
    config["group"]["forecast_months"] = 6
    config["group"]["live_macro"] = False
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "company.yml").write_text(
        yaml.safe_dump(config, sort_keys=False), encoding="utf-8"
    )

    result = build_v08("2026-08", allow_live_macro=False)
    assert result.validation_passed

    validation = json.loads((tmp_path / "data" / "processed" / "validation.json").read_text(encoding="utf-8"))
    assert validation["passed"]
    assert validation["ap_subledger_max_gap"] <= 0.05
    assert validation["ap_aging_bucket_max_gap"] <= 0.05

    ap = pd.read_csv(tmp_path / "data" / "processed" / "ap_aging.csv")
    suppliers = pd.read_csv(tmp_path / "data" / "processed" / "suppliers.csv")
    concentration = pd.read_csv(tmp_path / "data" / "processed" / "supplier_concentration.csv")
    assert not ap.empty
    assert not suppliers.empty
    assert not concentration.empty

    dashboard = json.loads((tmp_path / "web" / "data" / "dashboard.json").read_text(encoding="utf-8"))
    manifest = json.loads((tmp_path / "web" / "data" / "manifest.json").read_text(encoding="utf-8"))
    assert dashboard["meta"]["version"] == "0.8.0"
    assert manifest["version"] == "0.8.0"
    assert manifest["supplier_count"] == len(suppliers)
    assert "latest_supplier_top5_concentration" in manifest
