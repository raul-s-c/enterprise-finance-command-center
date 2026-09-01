import pandas as pd

from enterprise_finance.engine import load_config, month_range
from enterprise_finance.fx_economics_v15 import apply_native_fx_to_operations, load_fx_policy
from enterprise_finance.macro import build_macro
from enterprise_finance.workforce import simulate_operations_with_workforce
from enterprise_finance.workforce_fx_v15 import build_workforce_schedule


def test_fx_does_not_drive_fte_but_moves_reported_payroll():
    config = load_config()
    months = month_range("2026-08", 6)
    macro = build_macro(months, config["group"]["seed"], allow_live=False)
    base = simulate_operations_with_workforce(config, months, macro)
    policy = load_fx_policy()
    ops = apply_native_fx_to_operations(base.operations, macro, config, policy)

    workforce = build_workforce_schedule(ops, config, macro)

    stressed_macro = macro.copy()
    stressed_macro["USD"] = stressed_macro["USD"] * 0.88
    stressed_macro["JPY"] = stressed_macro["JPY"] * 1.10
    stressed_ops = apply_native_fx_to_operations(base.operations, stressed_macro, config, policy)
    stressed_workforce = build_workforce_schedule(stressed_ops, config, stressed_macro)

    keys = ["month", "entity", "division", "function"]
    compare = workforce.merge(stressed_workforce, on=keys, suffixes=("_base", "_stress"))
    assert len(compare) == len(workforce) == len(stressed_workforce)

    for column in ["opening_fte", "target_fte", "hires", "attrition", "ending_fte", "average_fte"]:
        assert (compare[f"{column}_base"] - compare[f"{column}_stress"]).abs().max() <= 0.0001

    foreign = compare[compare.entity.isin(["US01", "JP01"])]
    assert not foreign.empty
    assert (foreign.personnel_cost_base - foreign.personnel_cost_stress).abs().max() > 1.0
    assert (
        foreign.revenue_per_fte_constant_currency_base
        - foreign.revenue_per_fte_constant_currency_stress
    ).abs().max() <= 0.01
