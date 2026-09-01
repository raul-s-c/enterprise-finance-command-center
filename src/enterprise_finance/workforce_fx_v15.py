from __future__ import annotations

import pandas as pd

from .workforce import build_workforce_schedule as build_base_workforce_schedule


def build_workforce_schedule(
    operations: pd.DataFrame,
    config: dict,
    macro: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build Workforce capacity from constant-currency demand when available.

    Reported EUR Revenue may move solely because FX moves. Hiring capacity should
    respond to underlying business demand, not translation noise. v0.15 therefore
    replaces the Revenue driver with the preserved constant-currency Revenue only
    for Workforce planning; the reporting P&L keeps the translated EUR Revenue.
    """
    if operations.empty or "revenue_constant_currency_eur" not in operations.columns:
        return build_base_workforce_schedule(operations, config, macro)
    driver = operations.copy()
    driver["reported_revenue_eur"] = driver.revenue.astype(float)
    driver["revenue"] = driver.revenue_constant_currency_eur.astype(float)
    return build_base_workforce_schedule(driver, config, macro)
