from pathlib import Path

import pandas as pd
import yaml

from enterprise_finance.accounting import balance_sheet, build_accounting, validate_journal
from enterprise_finance.engine import build, load_config, month_range
from enterprise_finance.forecasting import build_forecast_vintages
from enterprise_finance.macro import build_macro
from enterprise_finance.model import product_master, simulate_operations
from enterprise_finance.reporting import group_balance_sheet
from enterprise_finance.working_capital_detail import build_ar_aging, build_inventory_aging, validate_working_capital_schedules


def _fixture(periods=12):
    config = load_config()
    months = month_range("2026-07", periods)
    macro = build_macro(months, config["group"]["seed"], allow_live=False)
    simulation = simulate_operations(config, months, macro)
    accounting = build_accounting(config, months, macro, simulation.operations)
    return config, months, macro, simulation, accounting


def test_product_catalog_has_finance_grade_hierarchy():
    products = product_master()
    required = {"division", "product_family", "product_subfamily", "product_type", "quality_tier", "generation", "strategic_role"}
    assert required.issubset(products.columns)
    assert len(products) >= 200
    assert products["product"].nunique() == len(products)
    assert products["quality_tier"].nunique() == 3
    counts = products.groupby("division")["product"].nunique().to_dict()
    assert all(counts.get(division, 0) >= 45 for division in ["Software", "Hardware", "Events", "Spare Parts"])
    assert products.groupby("division")["product_family"].nunique().min() >= 4


def test_deterministic_operations():
    config = load_config()
    months = month_range("2026-07", 6)
    macro = build_macro(months, config["group"]["seed"], allow_live=False)
    a = simulate_operations(config, months, macro)
    b = simulate_operations(config, months, macro)
    assert a.operations.equals(b.operations)
    assert a.portfolio_events.equals(b.portfolio_events)
    assert a.operations["product"].nunique() >= 150


def test_every_journal_balances():
    _, _, _, _, accounting = _fixture(4)
    checks = validate_journal(accounting.journal)
    assert checks["journal_balance_max_gap"] <= 0.02
    assert checks["trial_balance_gap"] <= 0.02


def test_balance_sheet_and_intercompany_reconcile():
    config, _, _, _, accounting = _fixture(6)
    legal_bs = balance_sheet(accounting.journal)
    group_bs = group_balance_sheet(legal_bs, config["transfer_pricing"]["manufacturing_cost_plus"])
    assert legal_bs.balance_check.abs().max() <= 0.05
    assert group_bs.balance_check.abs().max() <= 0.05
    ic = legal_bs.groupby("month", as_index=False).agg(ar=("ic_receivables", "sum"), ap=("ic_payables", "sum"))
    assert (ic.ar - ic.ap).abs().max() <= 0.05


def test_working_capital_schedules_reconcile_to_gl():
    config, _, _, simulation, accounting = _fixture(8)
    ar = build_ar_aging(accounting.journal, simulation.customers, config)
    inventory = build_inventory_aging(accounting.journal, simulation.operations, simulation.products, config)
    checks = validate_working_capital_schedules(accounting.journal, ar, inventory)
    assert checks["passed"]
    assert checks["ar_subledger_max_gap"] <= 0.05
    assert checks["inventory_schedule_max_gap"] <= 0.05
    assert not ar.empty
    assert ar.total_ar.sum() > 0
    assert not inventory.empty
    assert inventory.inventory_value.sum() > 0
    assert {"current", "overdue_1_30", "overdue_31_60", "overdue_61_90", "overdue_90_plus"}.issubset(ar.columns)
    assert {"age_0_30", "age_31_60", "age_61_90", "age_91_180", "age_180_plus"}.issubset(inventory.columns)


def test_forecasts_never_use_future_vintage_month():
    config, months, _, simulation, _ = _fixture(8)
    fc = build_forecast_vintages(config, simulation.operations, months)
    assert not fc.empty
    assert (pd.PeriodIndex(fc.month, freq="M") > pd.PeriodIndex(fc.vintage, freq="M")).all()


def test_full_pipeline(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    source_config = Path(__file__).resolve().parents[1] / "config" / "company.yml"
    config = yaml.safe_load(source_config.read_text(encoding="utf-8"))
    config["group"]["actual_months"] = 8
    config["group"]["forecast_months"] = 6
    config["group"]["live_macro"] = False
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "company.yml").write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    result = build("2026-07", allow_live_macro=False)
    assert result.validation_passed
    assert (tmp_path / "web" / "data" / "dashboard.json").exists()
    assert (tmp_path / "data" / "runtime" / "journal.csv.gz").exists()
    assert (tmp_path / "data" / "runtime" / "operational.csv.gz").exists()
    assert (tmp_path / "data" / "processed" / "journal_sample.csv").exists()
    assert (tmp_path / "data" / "processed" / "operational_sample.csv").exists()
    assert (tmp_path / "data" / "processed" / "ar_aging.csv").exists()
    assert (tmp_path / "data" / "processed" / "inventory_aging.csv").exists()
    products = pd.read_csv(tmp_path / "data" / "processed" / "products.csv")
    assert len(products) >= 200
