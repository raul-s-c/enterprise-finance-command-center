"""Two real, offline wrapper builds in an isolated directory; no production data writes."""
import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from enterprise_finance.engine_v22 import build


@pytest.mark.integration
def test_consecutive_closes_preserve_history_and_advance_forecast_24m(tmp_path, monkeypatch):
    source = Path(__file__).resolve().parents[1] / "config/company.yml"
    config = yaml.safe_load(source.read_text(encoding="utf-8"))
    # 24 months covers frozen budget history, prior-year comparisons and the
    # complete forecast while keeping this isolated CI regression bounded.
    config["group"]["actual_months"] = 24
    config["group"]["live_macro"] = False
    monkeypatch.chdir(tmp_path)
    Path("config").mkdir()
    Path("config/company.yml").write_text(yaml.safe_dump(config), encoding="utf-8")
    assert build("2026-08", allow_live_macro=False).validation_passed
    first = pd.read_csv("data/processed/management_action_history.csv").fillna("")
    first_reviews = pd.read_csv("data/processed/performance_review_history.csv").fillna("")
    assert not first.empty
    assert build("2026-09", allow_live_macro=False).validation_passed
    history = pd.read_csv("data/processed/management_action_history.csv").fillna("")
    reviews = pd.read_csv("data/processed/performance_review_history.csv").fillna("")
    pd.testing.assert_frame_equal(first.reset_index(drop=True),
        history[history.snapshot_month.eq("2026-08")].reset_index(drop=True), check_dtype=False)
    pd.testing.assert_frame_equal(first_reviews.reset_index(drop=True),
        reviews[reviews.review_month.eq("2026-08")].reset_index(drop=True), check_dtype=False)
    assert set(history.snapshot_month) == {"2026-08", "2026-09"}
    assert not history.duplicated(["snapshot_month", "action_id"]).any()
    actions = pd.read_csv("data/processed/management_actions.csv").fillna("")
    assert set(first.action_id).issubset(set(actions.action_id))
    forecast = pd.read_csv("data/processed/forecast_vintages.csv")
    current = forecast[forecast.vintage.eq("2026-09")]
    assert set(current.scenario) == {"Base", "Upside", "Downside"}
    assert set(current.horizon_month) == set(range(1, 25))
    assert current.month.min() == "2026-10"
    assert current.month.max() == "2028-09"
    for name in ["liquidity_forecast.csv", "forecast_pnl.csv", "forecast_balance_sheet.csv", "forecast_cash_flow.csv", "workforce_forecast.csv"]:
        frame = pd.read_csv(f"data/processed/{name}")
        current_frame = frame[frame.vintage.eq("2026-09")] if "vintage" in frame else frame
        assert set(current_frame.horizon_month) == set(range(1, 25)), name
    manifest = json.loads(Path("web/data/manifest.json").read_text())
    dashboard = json.loads(Path("web/data/dashboard.json").read_text())
    assert manifest["version"] == dashboard["meta"]["version"] == "0.22.1"
    assert manifest["forecast_months"] == 24
    assert manifest["base_24m_forecast_ending_cash"] == pytest.approx(
        pd.read_csv("data/processed/three_statement_forecast_summary.csv").query("scenario == 'Base'").iloc[0].ending_cash_24m, abs=0.01
    )
    assert manifest["end_month"] == dashboard["meta"]["end_month"] == "2026-09"
    assert manifest["validation"]["passed"]
    assert dashboard["validation"] == manifest["validation"]
    assert Path("data/processed/intercompany_fx_contracts.csv").exists()
