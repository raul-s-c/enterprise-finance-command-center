import pandas as pd

from enterprise_finance.budgeting_v09 import (
    build_annual_budgets,
    build_one_budget,
    budget_performance,
    validate_budgets,
)
from enterprise_finance.forecasting import build_forecast_vintages
from enterprise_finance.planning_v09 import fy_plan_bridge


def _config():
    return {
        "group": {"forecast_months": 18},
        "divisions": {
            "Software": {"annual_growth": 0.10},
            "Hardware": {"annual_growth": 0.04},
        },
        "budget": {
            "finalization_month": 10,
            "history_months": 12,
            "minimum_history_months": 6,
            "margin_improvement_pct": 0.004,
            "mc_improvement_pct": 0.003,
            "opex_leverage_pct": 0.002,
            "factory_absorption_improvement_pct": 0.10,
            "cost_center_efficiency_pct": 0.01,
            "growth_stretch": {"Software": 0.015, "Hardware": 0.010},
        },
    }


def _management():
    rows = []
    months = pd.period_range("2024-01", "2026-08", freq="M")
    for i, month in enumerate(months):
        revenue = 1_000_000 * (1.006 ** i)
        gp = revenue * 0.76
        opex = revenue * 0.39
        dep = 35_000.0
        rows.append({
            "month": str(month), "entity": "DE01", "division": "Software",
            "revenue": revenue, "marginal_contribution": revenue * 0.70,
            "gross_profit": gp, "opex": opex, "depreciation": dep,
            "ebit": gp - opex - dep,
        })
        # Manufacturing cost center: no external revenue but material P&L.
        absorption = -120_000 + (i % 5) * 8_000
        factory_dep = 58_000.0
        rows.append({
            "month": str(month), "entity": "CZ01", "division": "Hardware",
            "revenue": 0.0, "marginal_contribution": 0.0,
            "gross_profit": absorption, "opex": 0.0, "depreciation": factory_dep,
            "ebit": absorption - factory_dep,
        })
    return pd.DataFrame(rows)


def test_budget_is_frozen_and_uses_no_future_actuals():
    management = _management()
    config = _config()
    full = build_one_budget(management, config, 2026)
    truncated = build_one_budget(management[management.month <= "2025-10"], config, 2026)
    keys = ["month", "entity", "division"]
    metrics = ["revenue_budget", "gross_profit_budget", "opex_budget", "depreciation_budget", "ebit_budget"]
    recon = full[keys + metrics].merge(truncated[keys + metrics], on=keys, suffixes=("_full", "_cut"))
    for metric in metrics:
        assert (recon[f"{metric}_full"] - recon[f"{metric}_cut"]).abs().max() <= 0.01
    assert (full.max_source_month <= full.budget_vintage).all()


def test_budget_covers_commercial_and_factory_models():
    management = _management()
    config = _config()
    budgets = build_annual_budgets(management, config, "2026-08")
    current = budgets[budgets.budget_year.eq(2026)]
    coverage = current.groupby(["entity", "division"]).month.nunique()
    assert (coverage == 12).all()
    assert set(current.budget_model.unique()) == {"Driver-based commercial", "Cost center run-rate"}
    factory = current[current.entity.eq("CZ01")]
    assert factory.revenue_budget.abs().max() == 0
    assert factory.ebit_budget.abs().sum() > 0
    checks = validate_budgets(management, budgets, config)
    assert checks["passed"]
    performance = budget_performance(management, budgets, "2026-08")
    assert not performance.empty
    assert "ebit_variance" in performance.columns


def test_fy_plan_bridge_keeps_budget_and_forecast_distinct():
    management = _management()
    config = _config()
    budgets = build_annual_budgets(management, config, "2026-08")
    months = pd.period_range("2024-01", "2026-08", freq="M")
    forecasts = build_forecast_vintages(config, management, months)
    bridge = fy_plan_bridge(management, budgets, forecasts, "2026-08")
    assert not bridge.empty
    assert {"DE01", "CZ01"}.issubset(set(bridge.entity))
    assert "latest_fy_revenue" in bridge.columns
    assert "fc_1_fy_revenue" in bridge.columns
    assert "fc_3_fy_revenue" in bridge.columns
    assert "fc_6_fy_revenue" in bridge.columns
    assert "latest_fy_ebit" in bridge.columns
    factory = bridge[bridge.entity.eq("CZ01")].iloc[0]
    assert factory.latest_fy_ebit != 0
