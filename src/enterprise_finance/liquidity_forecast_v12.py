from __future__ import annotations

import pandas as pd

from .liquidity_forecast import build_liquidity_forecast as _build_base


def build_liquidity_forecast(*args, config: dict, **kwargs) -> pd.DataFrame:
    """Build the driver-based liquidity forecast with explicit facility controls."""
    out = _build_base(*args, config=config, **kwargs)
    if out.empty:
        return out
    rcf_limit = float(config.get("treasury", {}).get("rcf_limit", 35_000_000.0))
    out["rcf_limit"] = rcf_limit
    out["liquidity_shortfall"] = (
        out.minimum_operating_cash.astype(float) - out.ending_cash.astype(float)
    ).clip(lower=0.0)
    out["rcf_identity_gap"] = out.rcf_limit - out.rcf_drawn - out.undrawn_rcf
    return out


def validate_liquidity_forecast(forecast: pd.DataFrame, horizon: int = 12) -> dict:
    if forecast.empty:
        return {
            "liquidity_forecast_cash_rollforward_max_gap": 0.0,
            "liquidity_forecast_customer_cash_max_gap": 0.0,
            "liquidity_forecast_supplier_cash_max_gap": 0.0,
            "liquidity_forecast_rcf_identity_max_gap": 0.0,
            "liquidity_forecast_negative_balance_rows": 0,
            "liquidity_forecast_missing_scenario_months": horizon * 3,
            "liquidity_forecast_rcf_excess_rows": 0,
            "liquidity_forecast_shortfall_rows": 0,
            "passed": False,
        }

    cash_gap = float(forecast.cash_rollforward_gap.abs().max())
    customer_gap = float(forecast.customer_cash_identity_gap.abs().max())
    supplier_gap = float(forecast.supplier_cash_identity_gap.abs().max())
    rcf_gap = float(forecast.rcf_identity_gap.abs().max())

    balance_cols = [
        "ending_ar", "ending_inventory", "ending_ap",
        "ending_contract_liabilities", "ending_cash", "gross_debt",
    ]
    negative = int((forecast[balance_cols].min(axis=1) < -0.05).sum())

    coverage = forecast.groupby("scenario").month.nunique()
    missing = int(
        sum(max(horizon - int(value), 0) for value in coverage.values)
        + max(3 - len(coverage), 0) * horizon
    )
    rcf_excess = int(
        ((forecast.rcf_drawn < -0.05) | (forecast.rcf_drawn - forecast.rcf_limit > 0.05)).sum()
    )
    shortfall = int((forecast.liquidity_shortfall > 0.05).sum())

    checks = {
        "liquidity_forecast_cash_rollforward_max_gap": round(cash_gap, 2),
        "liquidity_forecast_customer_cash_max_gap": round(customer_gap, 2),
        "liquidity_forecast_supplier_cash_max_gap": round(supplier_gap, 2),
        "liquidity_forecast_rcf_identity_max_gap": round(rcf_gap, 2),
        "liquidity_forecast_negative_balance_rows": negative,
        "liquidity_forecast_missing_scenario_months": missing,
        "liquidity_forecast_rcf_excess_rows": rcf_excess,
        "liquidity_forecast_shortfall_rows": shortfall,
    }
    checks["passed"] = (
        cash_gap <= 0.02
        and customer_gap <= 0.02
        and supplier_gap <= 0.02
        and rcf_gap <= 0.02
        and negative == 0
        and missing == 0
        and rcf_excess == 0
        and shortfall == 0
    )
    return checks
