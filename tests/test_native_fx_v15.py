from pathlib import Path

import pandas as pd
import yaml

from enterprise_finance.engine import load_config, month_range
from enterprise_finance.fx_economics_v15 import (
    apply_native_fx_to_operations,
    load_fx_policy,
    validate_native_fx_economics,
)
from enterprise_finance.macro import build_macro
from enterprise_finance.workforce import simulate_operations_with_workforce


def _fixture():
    config = load_config()
    months = month_range("2026-08", 4)
    macro = build_macro(months, config["group"]["seed"], allow_live=False)
    base = simulate_operations_with_workforce(config, months, macro)
    policy = load_fx_policy()
    return config, macro, base.operations, policy


def test_native_fx_roundtrip_and_eur_entities_are_stable():
    config, macro, base_ops, policy = _fixture()
    reported = apply_native_fx_to_operations(base_ops, macro, config, policy)
    checks = validate_native_fx_economics(reported, macro, config, policy)
    assert checks["passed"], checks
    assert checks["native_fx_revenue_roundtrip_max_gap"] <= 0.02
    assert checks["native_fx_reported_sensitivity_rows"] > 0

    eur_scope = reported[reported.entity.isin(["DE01", "ES01"])]
    assert not eur_scope.empty
    assert (eur_scope.revenue - eur_scope.revenue_constant_currency_eur).abs().max() <= 0.01


def test_fx_moves_reported_eur_without_moving_local_business():
    config, macro, base_ops, policy = _fixture()
    original = apply_native_fx_to_operations(base_ops, macro, config, policy)

    stressed_macro = macro.copy()
    stressed_macro["USD"] = stressed_macro["USD"] * 0.90
    stressed_macro["JPY"] = stressed_macro["JPY"] * 1.08
    stressed = apply_native_fx_to_operations(base_ops, stressed_macro, config, policy)

    us_orig = original[original.entity.eq("US01")].reset_index(drop=True)
    us_stress = stressed[stressed.entity.eq("US01")].reset_index(drop=True)
    assert len(us_orig) == len(us_stress) > 0
    assert (us_orig.revenue_local - us_stress.revenue_local).abs().max() <= 0.01
    assert (us_orig.revenue - us_stress.revenue).abs().max() > 1.0

    jp_orig = original[original.entity.eq("JP01")].reset_index(drop=True)
    jp_stress = stressed[stressed.entity.eq("JP01")].reset_index(drop=True)
    assert len(jp_orig) == len(jp_stress) > 0
    assert (jp_orig.revenue_local - jp_stress.revenue_local).abs().max() <= 0.01
    assert (jp_orig.revenue - jp_stress.revenue).abs().max() > 1.0


def test_physical_manufacturing_cost_uses_factory_currency():
    config, macro, base_ops, policy = _fixture()
    reported = apply_native_fx_to_operations(base_ops, macro, config, policy)
    physical = reported[reported.division.isin(["Hardware", "Spare Parts"]) & reported.source_factory.ne("")]
    assert not physical.empty

    expected = {"CZ01": "CZK", "CN01": "CNY"}
    for factory, currency in expected.items():
        scope = physical[physical.source_factory.eq(factory)]
        assert not scope.empty
        assert set(scope.manufacturing_currency.unique()) == {currency}

    fx = {
        (str(r.month), currency): float(getattr(r, currency))
        for r in macro.itertuples(index=False)
        for currency in ["CZK", "CNY"]
    }
    sample = physical.head(200)
    for r in sample.itertuples(index=False):
        rate = fx[(str(r.month), str(r.manufacturing_currency))]
        reconstructed = round(
            (float(r.variable_production_cost_local) + float(r.fixed_production_cost_local)) * rate,
            2,
        )
        reported_cost = round(float(r.variable_production_cost) + float(r.fixed_production_cost), 2)
        assert abs(reconstructed - reported_cost) <= 0.02
