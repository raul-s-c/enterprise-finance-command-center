import pandas as pd

from enterprise_finance.forecasting import build_forecast_vintages, validate_forecast_scale


def _config():
    return {
        "group": {"forecast_months": 18},
        "divisions": {
            "Software": {"annual_growth": 0.10},
            "Hardware": {"annual_growth": 0.04},
        },
    }


def _operations():
    rows = []
    months = pd.period_range("2025-01", "2026-08", freq="M")
    seasonality = {1:.88,2:.92,3:.99,4:1.01,5:1.03,6:1.05,7:.95,8:.84,9:1.04,10:1.08,11:1.12,12:1.18}
    for i, month in enumerate(months):
        monthly_revenue = 10_000_000 * (1.004 ** i) * seasonality[month.month]
        # Deliberately split the monthly company result into many transaction rows.
        # A transaction-mean baseline would therefore be wrong by roughly 1/100.
        for tx in range(100):
            revenue = monthly_revenue / 100
            rows.append({
                "month": str(month),
                "entity": "DE01",
                "division": "Software",
                "revenue": revenue,
                "gross_profit": revenue * 0.76,
                "marginal_contribution": revenue * 0.70,
                "opex": revenue * 0.39,
            })
    return pd.DataFrame(rows), months


def test_forecast_uses_monthly_totals_not_transaction_means():
    operations, months = _operations()
    forecasts = build_forecast_vintages(_config(), operations, months)
    latest = forecasts[
        forecasts.vintage.eq("2026-08")
        & forecasts.scenario.eq("Base")
        & forecasts.horizon_month.eq(1)
    ]
    actual = operations.groupby("month", as_index=False).revenue.sum()
    trailing = actual[actual.month.ge("2026-03") & actual.month.le("2026-08")].revenue.mean()
    next_month = latest.revenue_forecast.sum()
    assert next_month > trailing * 0.70
    assert next_month < trailing * 1.50

    checks = validate_forecast_scale(forecasts, operations, "2026-08")
    assert checks["passed"]
    assert checks["forecast_scale_out_of_range"] == 0


def test_forecast_scale_control_rejects_unit_error():
    operations, months = _operations()
    forecasts = build_forecast_vintages(_config(), operations, months)
    broken = forecasts.copy()
    broken.loc[
        broken.vintage.eq("2026-08") & broken.scenario.eq("Base") & broken.horizon_month.eq(1),
        "revenue_forecast",
    ] *= 0.01
    checks = validate_forecast_scale(broken, operations, "2026-08")
    assert not checks["passed"]
    assert checks["forecast_scale_out_of_range"] == 1
