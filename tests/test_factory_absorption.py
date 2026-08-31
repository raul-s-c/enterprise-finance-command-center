from pathlib import Path

import pandas as pd
import yaml

from enterprise_finance.accounting import (
    balance_sheet,
    build_accounting,
    validate_factory_absorption_accounting,
    validate_journal,
)
from enterprise_finance.engine import load_config, month_range
from enterprise_finance.engine_v06 import build as build_v06
from enterprise_finance.factory_absorption import (
    hardware_factory_accounting_schedule,
    management_pnl_with_factory_absorption,
)
from enterprise_finance.macro import build_macro
from enterprise_finance.model import simulate_operations


def _fixture(periods=6):
    config = load_config()
    months = month_range("2026-07", periods)
    macro = build_macro(months, config["group"]["seed"], allow_live=False)
    simulation = simulate_operations(config, months, macro)
    accounting = build_accounting(config, months, macro, simulation.operations)
    return config, simulation, accounting


def test_factory_absorption_is_posted_and_reconciled():
    config, simulation, accounting = _fixture(6)
    factory = accounting.factory
    required = {
        "actual_fixed_factory_cost",
        "absorbed_fixed_cost",
        "absorption_variance",
        "under_absorption",
        "over_absorption",
        "fixed_cost_absorption_pct",
    }
    assert required.issubset(factory.columns)
    assert not factory.empty
    assert (factory.actual_fixed_factory_cost > 0).all()
    assert (factory.actual_fixed_factory_cost - factory.absorbed_fixed_cost - factory.absorption_variance).abs().max() <= 0.02

    checks = validate_factory_absorption_accounting(factory, accounting.journal)
    assert checks["passed"]
    assert checks["factory_absorption_rollforward_max_gap"] <= 0.02
    assert checks["factory_absorption_journal_max_gap"] <= 0.02

    variance_journal = accounting.journal[
        accounting.journal.account.eq("5450_FACTORY_ABSORPTION_VARIANCE")
        & ~accounting.journal.journal_type.eq("closing")
    ]
    assert not variance_journal.empty

    journal_checks = validate_journal(accounting.journal)
    assert journal_checks["journal_balance_max_gap"] <= 0.02
    legal_bs = balance_sheet(accounting.journal)
    assert legal_bs.balance_check.abs().max() <= 0.05

    management = management_pnl_with_factory_absorption(
        simulation.operations, accounting.journal, set(config["factories"])
    )
    factory_management = management[management.entity.isin(config["factories"])]
    assert not factory_management.empty
    schedule_variance = factory.groupby("month", as_index=False).absorption_variance.sum()
    management_variance = factory_management.groupby("month", as_index=False).factory_absorption_variance.sum()
    recon = schedule_variance.merge(management_variance, on="month", how="outer").fillna(0.0)
    assert (recon.absorption_variance - recon.factory_absorption_variance).abs().max() <= 0.02

    econ, mix = hardware_factory_accounting_schedule(
        simulation.operations, simulation.products, factory, config
    )
    assert not econ.empty
    assert econ.absorption_rollforward_gap.abs().max() <= 0.02
    assert econ.utilization_check.abs().max() <= 0.0001
    assert not mix.empty


def test_v06_enriched_close_outputs_factory_variance(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    source_config = Path(__file__).resolve().parents[1] / "config" / "company.yml"
    config = yaml.safe_load(source_config.read_text(encoding="utf-8"))
    config["group"]["actual_months"] = 4
    config["group"]["forecast_months"] = 3
    config["group"]["live_macro"] = False
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "company.yml").write_text(
        yaml.safe_dump(config, sort_keys=False), encoding="utf-8"
    )

    result = build_v06("2026-07", allow_live_macro=False)
    assert result.validation_passed

    validation = pd.read_json(tmp_path / "data" / "processed" / "validation.json", typ="series")
    assert validation["passed"]
    assert validation["factory_absorption_rollforward_max_gap"] <= 0.02
    assert validation["factory_absorption_journal_max_gap"] <= 0.02

    pnl = pd.read_csv(tmp_path / "data" / "processed" / "pnl.csv")
    assert "factory_absorption_variance" in pnl.columns
    factory = pd.read_csv(tmp_path / "data" / "processed" / "factory.csv")
    assert "absorption_variance" in factory.columns

    import json
    dashboard = json.loads((tmp_path / "web" / "data" / "dashboard.json").read_text(encoding="utf-8"))
    manifest = json.loads((tmp_path / "web" / "data" / "manifest.json").read_text(encoding="utf-8"))
    assert dashboard["meta"]["version"] == "0.6.0"
    assert manifest["version"] == "0.6.0"
    assert "latest_factory_absorption_variance" in manifest
