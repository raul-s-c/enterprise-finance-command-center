import pandas as pd

from enterprise_finance.engine import load_config, month_range
from enterprise_finance.forecasting_fx_v15 import build_forecast_vintages, validate_fx_forecast
from enterprise_finance.fx_economics_v15 import apply_native_fx_to_operations, load_fx_policy
from enterprise_finance.macro import build_macro
from enterprise_finance.workforce import simulate_operations_with_workforce


def _fixture():
    config = load_config()
    months = month_range("2026-08", 10)
    macro = build_macro(months, config["group"]["seed"], allow_live=False)
    base = simulate_operations_with_workforce(config, months, macro)
    policy = load_fx_policy()
    operations = apply_native_fx_to_operations(base.operations, macro, config, policy)
    return config, months, macro, operations


def test_fx_forecast_uses_only_vintage_rate():
    config, months, macro, operations = _fixture()
    forecasts = build_forecast_vintages(config, operations, months, macro)
    assert not forecasts.empty
    controls = validate_fx_forecast(forecasts, operations, macro, config)
    assert controls["passed"], controls

    lookup = {
        (str(r.month), currency): float(getattr(r, currency))
        for r in macro.itertuples(index=False)
        for currency in ["EUR", "USD", "JPY", "CNY", "CZK"]
    }
    for r in forecasts.head(1000).itertuples(index=False):
        expected = lookup[(str(r.vintage), str(r.functional_currency))]
        assert abs(float(r.fx_assumption_to_eur) - expected) <= 1e-10


def test_future_fx_changes_do_not_rewrite_existing_vintage():
    config, months, macro, operations = _fixture()
    original = build_forecast_vintages(config, operations, months, macro)
    target_vintage = sorted(original.vintage.unique())[-2]
    original_vintage = original[original.vintage.eq(target_vintage)].reset_index(drop=True)
    assert not original_vintage.empty

    stressed = macro.copy()
    future_mask = stressed.month.gt(target_vintage)
    stressed.loc[future_mask, "USD"] = stressed.loc[future_mask, "USD"] * 0.70
    stressed.loc[future_mask, "JPY"] = stressed.loc[future_mask, "JPY"] * 1.30
    rebuilt = build_forecast_vintages(config, operations, months, stressed)
    rebuilt_vintage = rebuilt[rebuilt.vintage.eq(target_vintage)].reset_index(drop=True)

    cols = [
        "revenue_forecast", "gross_profit_forecast", "opex_forecast",
        "personnel_cost_forecast", "workforce_fte_forecast", "fx_assumption_to_eur",
    ]
    assert len(original_vintage) == len(rebuilt_vintage)
    for column in cols:
        assert (original_vintage[column] - rebuilt_vintage[column]).abs().max() <= 0.0001


def test_physical_forecast_carries_factory_fx_exposure():
    config, months, macro, operations = _fixture()
    forecasts = build_forecast_vintages(config, operations, months, macro)
    physical = forecasts[forecasts.division.isin(["Hardware", "Spare Parts"])]
    assert not physical.empty
    # Commercial-currency and manufacturing-currency translation factors should not
    # be mechanically identical for every foreign physical forecast row.
    buyer_factor = []
    policy = load_fx_policy()
    calibration = policy["calibration_fx_to_eur"]
    for r in physical.itertuples(index=False):
        buyer_factor.append(float(r.fx_assumption_to_eur) / float(calibration[str(r.functional_currency)]))
    physical = physical.copy()
    physical["buyer_factor"] = buyer_factor
    assert ((physical.manufacturing_fx_factor - physical.buyer_factor).abs() > 1e-6).any()
