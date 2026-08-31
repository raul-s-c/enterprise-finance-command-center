from pathlib import Path

import pandas as pd

from enterprise_finance.accounting import balance_sheet, build_accounting, validate_journal
from enterprise_finance.engine import build, load_config, month_range
from enterprise_finance.forecasting import build_forecast_vintages
from enterprise_finance.macro import build_macro
from enterprise_finance.model import product_master, simulate_operations
from enterprise_finance.reporting import group_balance_sheet


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
    assert products.product.nunique() == len(products)
    assert products.quality_tier.nunique() == 3
    counts = products.groupby("division").product.nunique().to_dict()
    assert all(counts.get(division, 0) >= 45 for division in ["Software", "Hardware", "Events", "Spare Parts"])
    assert products.groupby("division").product_family.nunique().min() >= 4


def test_deterministic_operations():
    config = load_config()
    months = month_range("2026-07", 8)
    macro = build_macro(months, config["group"]["seed"], allow_live=False)
    a = simulate_operations(config, months, macro)
    b = simulate_operations(config, months, macro)
    assert a.operations.equals(b.operations)
    assert a.portfolio_events.equals(b.portfolio_events)
    assert a.operations.product.nunique() >= 150


def test_every_journal_balances():
    _, _, _, _, accounting = _fixture(8)
    checks = validate_journal(accounting.journal)
    assert checks["journal_balance_max_gap"] <= 0.02
    assert checks["trial_balance_gap"] <= 0.02


def test_balance_sheet_and_intercompany_reconcile():
    config, _, _, _, accounting = _fixture(10)
    legal_bs = balance_sheet(accounting.journal)
    group_bs = group_balance_sheet(legal_bs, config["transfer_pricing"]["manufacturing_cost_plus"])
    assert legal_bs.balance_check.abs().max() <= 0.05
    assert group_bs.balance_check.abs().max() <= 0.05
    ic = legal_bs.groupby("month", as_index=False).agg(ar=("ic_receivables", "sum"), ap=("ic_payables", "sum"))
    assert (ic.ar - ic.ap).abs().max() <= 0.05


def test_forecasts_never_use_future_vintage_month():
    config, months, _, simulation, _ = _fixture(12)
    fc = build_forecast_vintages(config, simulation.operations, months)
    assert not fc.empty
    assert (pd.PeriodIndex(fc.month, freq="M") > pd.PeriodIndex(fc.vintage, freq="M")).all()


def test_full_pipeline(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    source_config = Path(__file__).resolve().parents[1] / "config" / "company.yml"
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "company.yml").write_text(source_config.read_text(), encoding="utf-8")
    result = build("2026-07", allow_live_macro=False)
    assert result.validation_passed
    assert (tmp_path / "web" / "data" / "dashboard.json").exists()
    assert (tmp_path / "data" / "processed" / "journal.csv.gz").exists()
    assert (tmp_path / "data" / "processed" / "operational.csv.gz").exists()
    products = pd.read_csv(tmp_path / "data" / "processed" / "products.csv")
    assert len(products) >= 200
