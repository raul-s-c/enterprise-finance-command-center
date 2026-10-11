"""Shared, ledger-cent-exact CAPEX installment schedule."""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

import numpy as np
import pandas as pd


CENT = Decimal("0.01")


def capex_spend_schedule(project: dict) -> dict[str, float]:
    """Allocate an approved project budget over its planned months exactly.

    The weighted profile is rounded to ledger cents for each installment;
    the final installment is the remaining approved budget. This is the
    arithmetic remainder of the plan, not an accounting balancing entry.
    """
    build_months = int(project["build_months"])
    if build_months <= 0:
        raise ValueError("CAPEX project build_months must be positive")
    budget = Decimal(str(project["budget"])).quantize(CENT, rounding=ROUND_HALF_UP)
    if budget < 0:
        raise ValueError("CAPEX project budget must not be negative")

    start = pd.Period(project["start"], freq="M")
    months = pd.period_range(start=start, periods=build_months, freq="M")
    weights = np.sin(np.linspace(0.25, np.pi - 0.25, build_months))
    weights = weights / weights.sum()
    amounts = [
        (budget * Decimal(str(float(weight)))).quantize(CENT, rounding=ROUND_HALF_UP)
        for weight in weights
    ]
    amounts[-1] = budget - sum(amounts[:-1], Decimal("0.00"))
    if any(amount < 0 for amount in amounts) or sum(amounts) != budget:
        raise RuntimeError("CAPEX installment schedule does not equal its approved budget")
    return {str(month): float(amount) for month, amount in zip(months, amounts)}
