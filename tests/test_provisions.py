from pathlib import Path
import json

import pandas as pd
import yaml

from enterprise_finance.accounting import build_accounting, cash_flow, validate_journal
from enterprise_finance.engine import load_config, month_range
from enterprise_finance.engine_v07 import build as build_v07
from enterprise_finance.macro import build_macro
from enterprise_finance.model import simulate_operations
from enterprise_finance.provisions import (
    AR_ALLOWANCE_ACCOUNT,
    INVENTORY_ALLOWANCE_ACCOUNT,
    append_provision_journals,
    build_credit_loss_schedule,
    build_inventory_provision_schedule,
    group_balance_sheet_with_provisions,
    legal_balance_sheet_with_provisions,
    validate_provisions,
)
from enterprise_finance.working_capital_detail import build_ar_aging, build_inventory_aging


def _fixture(periods=8):
    config = load_config()
    months = month_range("2026-08", periods)
    macro = build_macro(months, config["group"]["seed"], allow_live=False)
    simulation = simulate_operations(config, months, macro)
    accounting = build_accounting(config, months, macro, simulation.operations)
    ar = build_ar_aging(accounting.journal, simulation.customers, config)
    inventory = build_inventory_aging(accounting.journal, simulation.operations, simulation.products, config)
    return config, simulation, accounting, ar, inventory


def test_provision_targets_are_bounded_and_risk_sensitive():
    config, _, _, ar, inventory = _fixture()
    ecl = build_credit_loss_schedule(ar, config)
    inv = build_inventory_provision_schedule(inventory, config)

    assert not ecl.empty
    assert not inv.empty
    assert (ecl.credit_loss_allowance >= -0.01).all()
    assert (ecl.credit_loss_allowance <= ecl.gross_ar + 0.01).all()
    assert (inv.inventory_provision >= -0.01).all()
    assert (inv.inventory_provision <= inv.gross_inventory + 0.01).all()

    latest = ecl[ecl.month.eq(ecl.month.max())]
    high_risk = latest[latest.risk_score >= latest.risk_score.quantile(0.75)]
    low_risk = latest[latest.risk_score <= latest.risk_score.quantile(0.25)]
    if not high_risk.empty and not low_risk.empty:
        assert high_risk.allowance_pct.mean() >= low_risk.allowance_pct.mean() * 0.70

    old_inventory = inv[inv.age_180_plus > 0]
    if not old_inventory.empty:
        assert old_inventory.provision_pct.max() > 0.10


def test_provision_journal_reconciles_and_has_no_cash_entry():
    config, _, accounting, ar, inventory = _fixture()
    ecl = build_credit_loss_schedule(ar, config)
    inv = build_inventory_provision_schedule(inventory, config)
    journal, provision_journal = append_provision_journals(accounting.journal, ecl, inv)

    assert not provision_journal.empty
    assert provision_journal.account.isin([AR_ALLOWANCE_ACCOUNT, INVENTORY_ALLOWANCE_ACCOUNT]).any()
    assert not provision_journal.account.eq("1000_CASH").any()

    checks = validate_journal(journal)
    assert checks["journal_balance_max_gap"] <= 0.02
    assert checks["trial_balance_gap"] <= 0.02

    provision_checks = validate_provisions(journal, ecl, inv)
    assert provision_checks["passed"]
    assert provision_checks["credit_loss_allowance_max_gap"] <= 0.05
    assert provision_checks["inventory_provision_max_gap"] <= 0.05

    before_cf = cash_flow(accounting.journal).groupby("month", as_index=False).net_cash_movement.sum()
    after_cf = cash_flow(journal).groupby("month", as_index=False).net_cash_movement.sum()
    cash_recon = before_cf.merge(after_cf, on="month", suffixes=("_before", "_after"))
    assert (cash_recon.net_cash_movement_before - cash_recon.net_cash_movement_after).abs().max() <= 0.01


def test_provision_adjusted_balance_sheet_stays_balanced():
    config, _, accounting, ar, inventory = _fixture()
    ecl = build_credit_loss_schedule(ar, config)
    inv = build_inventory_provision_schedule(inventory, config)
    journal, _ = append_provision_journals(accounting.journal, ecl, inv)

    legal_bs = legal_balance_sheet_with_provisions(journal)
    group_bs = group_balance_sheet_with_provisions(
        legal_bs, float(config["transfer_pricing"]["manufacturing_cost_plus"])
    )

    assert legal_bs.balance_check.abs().max() <= 0.05
    assert group_bs.balance_check.abs().max() <= 0.05
    assert (legal_bs.trade_receivables <= legal_bs.trade_receivables_gross + 0.01).all()
    assert (legal_bs.inventory <= legal_bs.inventory_gross + 0.01).all()
    assert (group_bs.credit_loss_allowance >= -0.01).all()
    assert (group_bs.inventory_provision >= -0.01).all()


def test_v07_full_close_outputs_asset_quality(tmp_path, monkeypatch):
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

    result = build_v07("2026-08", allow_live_macro=False)
    assert result.validation_passed

    validation = json.loads((tmp_path / "data" / "processed" / "validation.json").read_text(encoding="utf-8"))
    assert validation["passed"]
    assert validation["credit_loss_allowance_max_gap"] <= 0.05
    assert validation["inventory_provision_max_gap"] <= 0.05

    for filename in [
        "credit_loss_allowance.csv",
        "inventory_provision.csv",
        "provision_summary.csv",
        "provision_journal.csv",
    ]:
        assert (tmp_path / "data" / "processed" / filename).exists()

    pnl = pd.read_csv(tmp_path / "data" / "processed" / "pnl.csv")
    assert {"credit_loss_expense", "inventory_provision_expense"}.issubset(pnl.columns)
    bs = pd.read_csv(tmp_path / "data" / "processed" / "balance_sheet.csv")
    assert {"trade_receivables_gross", "credit_loss_allowance", "inventory_gross", "inventory_provision"}.issubset(bs.columns)

    dashboard = json.loads((tmp_path / "web" / "data" / "dashboard.json").read_text(encoding="utf-8"))
    manifest = json.loads((tmp_path / "web" / "data" / "manifest.json").read_text(encoding="utf-8"))
    assert dashboard["meta"]["version"] == "0.7.0"
    assert manifest["version"] == "0.7.0"
    assert "latest_credit_loss_allowance" in manifest
    assert "latest_inventory_provision" in manifest
    assert manifest["provision_journal_rows"] > 0
