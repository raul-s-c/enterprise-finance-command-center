import pandas as pd
import yaml

from enterprise_finance import macro as macro_module
from enterprise_finance.financial_sensitivities import (
    SHOCKS,
    build_financial_sensitivities,
    validate_macro_and_sensitivities,
)
from enterprise_finance.macro import _jsonstat_series, build_macro, build_macro_lineage, source_manifest


def _inputs():
    forecasts = pd.read_csv("data/processed/forecast.csv")
    liquidity = pd.read_csv("data/processed/liquidity_forecast.csv")
    debt = pd.read_csv("data/processed/debt_schedule.csv")
    with open("config/company.yml", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    return forecasts, liquidity, debt, config


def test_jsonstat_series_preserves_month_positions_and_sparse_values():
    payload = {
        "dimension": {"time": {"category": {"index": {"2026-06": 0, "2026-07": 1, "2026-08": 2}}}},
        "value": {"0": 99.5, "2": 101.2},
    }
    assert _jsonstat_series(payload) == {"2026-06": 99.5, "2026-08": 101.2}


def test_live_macro_overlays_each_official_driver_and_records_lineage(monkeypatch):
    months = pd.period_range("2026-07", "2026-08", freq="M")
    monkeypatch.setattr(macro_module, "_fetch_ecb_monthly", lambda currency, start, end: {"2026-08": 0.9})
    monkeypatch.setattr(macro_module, "_fetch_eurostat_hicp", lambda start, end: {"2026-08": 0.02})
    monkeypatch.setattr(macro_module, "_fetch_eurostat_industrial", lambda start, end: {"2026-08": 101.0})
    monkeypatch.setattr(macro_module, "_fetch_ecb_policy_rate", lambda start, end: {"2026-08": 0.024})
    monkeypatch.setattr(macro_module, "_fetch_world_bank_energy", lambda start, end: {"2026-08": 97.0})
    macro = build_macro(months, 7, allow_live=True)
    august = macro[macro.month.eq("2026-08")].iloc[0]
    assert august.inflation_source == "Eurostat_HICP"
    assert august.industrial_index_source == "Eurostat_STS"
    assert august.energy_index_source == "World_Bank_Pink_Sheet"
    assert august.policy_rate_source == "ECB_MRO"
    assert august.USD_source == "ECB_EXR"
    lineage = build_macro_lineage(macro, "2026-08")
    assert len(lineage) == len(months) * 8
    assert set(lineage.status) == {"Official", "Fallback"}
    assert source_manifest(macro)["macro_drivers"]["inflation"]["official_rows"] == 1


def test_offline_macro_is_deterministic_and_has_complete_fallback_lineage():
    months = pd.period_range("2026-01", "2026-08", freq="M")
    left = build_macro(months, 17, allow_live=False)
    right = build_macro(months, 17, allow_live=False)
    pd.testing.assert_frame_equal(left, right)
    lineage = build_macro_lineage(left, "2026-08")
    assert len(lineage) == 64
    assert lineage.status.eq("Fallback").all()


def test_sensitivities_are_non_additive_directional_and_do_not_mutate_forecast():
    forecasts, liquidity, debt, config = _inputs()
    original = forecasts.copy(deep=True)
    detail, summary = build_financial_sensitivities(forecasts, liquidity, debt, config, "2026-08")
    pd.testing.assert_frame_equal(forecasts, original)
    assert summary.shock.nunique() == len(SHOCKS)
    assert not summary.portfolio_additive.any()
    impacts = summary.set_index("shock").ebit_impact
    assert impacts["Price +1%"] > 0
    assert impacts["Volume +1%"] > 0
    assert impacts["Industrial production -1%"] < 0
    assert impacts["Inflation +100 bps"] < 0
    assert impacts["Wage inflation +100 bps"] < 0
    assert impacts["Energy index +10%"] < 0
    assert impacts["EUR strengthening +5%"] < 0
    assert summary.loc[summary.shock.eq("Policy rate +100 bps"), "interest_expense_impact"].iloc[0] > 0
    price = summary.loc[summary.shock.eq("Price +1%")].iloc[0]
    base = liquidity[
        liquidity.scenario.eq("Base") & liquidity.horizon_month.eq(liquidity.horizon_month.max())
    ].iloc[-1]
    expected_leverage_delta = round(
        (base.net_debt + price.net_debt_impact) / (base.ebitda_ttm + price.ebit_impact)
        - base.net_leverage,
        4,
    )
    assert price.net_leverage_delta == expected_leverage_delta
    assert not detail.empty


def test_macro_and_sensitivity_controls_reconcile_detail_to_summary():
    forecasts, liquidity, debt, config = _inputs()
    macro = build_macro(pd.period_range("2025-09", "2026-08", freq="M"), 19, allow_live=False)
    lineage = build_macro_lineage(macro, "2026-08")
    detail, summary = build_financial_sensitivities(forecasts, liquidity, debt, config, "2026-08")
    checks = validate_macro_and_sensitivities(macro, lineage, detail, summary)
    assert checks["passed"] is True
    assert checks["sensitivity_detail_summary_max_gap"] == 0
    assert checks["sensitivity_ebit_identity_max_gap"] <= 0.02
