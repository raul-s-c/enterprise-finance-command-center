from __future__ import annotations

import pandas as pd

from .fx_economics_v15 import load_fx_policy
from .workforce import build_workforce_schedule as build_base_workforce_schedule


MONEY_COLUMNS = [
    "annual_loaded_cost_per_fte",
    "payroll_cost",
    "recruitment_cost",
    "personnel_cost",
]


def _money(value: float) -> float:
    return round(float(value), 2)


def _entity_currency(config: dict) -> dict[str, str]:
    return {str(row["code"]): str(row["currency"]) for row in config.get("entities", [])}


def _fx_lookup(macro: pd.DataFrame | None) -> dict[tuple[str, str], float]:
    if macro is None or macro.empty:
        return {}
    currencies = [c for c in ["EUR", "USD", "JPY", "CNY", "CZK"] if c in macro.columns]
    return {
        (str(row.month), currency): float(getattr(row, currency))
        for row in macro.itertuples(index=False)
        for currency in currencies
        if float(getattr(row, currency)) > 0
    }


def build_workforce_schedule(
    operations: pd.DataFrame,
    config: dict,
    macro: pd.DataFrame | None = None,
    fx_policy_path: str = "config/fx-policy.yml",
) -> pd.DataFrame:
    """Plan FTE from constant-currency demand and translate payroll to reporting EUR.

    FX must not create artificial hiring or attrition. The FTE roll-forward therefore
    uses the preserved constant-currency Revenue. Monetary Workforce costs are then
    interpreted as calibrated functional-currency economics and translated at the
    monthly FX rate so reported EUR payroll still carries a genuine FX effect.
    """
    if operations.empty or "revenue_constant_currency_eur" not in operations.columns:
        return build_base_workforce_schedule(operations, config, macro)

    driver = operations.copy()
    driver["reported_revenue_eur"] = driver.revenue.astype(float)
    driver["revenue"] = driver.revenue_constant_currency_eur.astype(float)
    schedule = build_base_workforce_schedule(driver, config, macro)
    if schedule.empty:
        return schedule

    policy = load_fx_policy(fx_policy_path)
    calibration = {str(k): float(v) for k, v in policy["calibration_fx_to_eur"].items()}
    currencies = _entity_currency(config)
    fx = _fx_lookup(macro)
    out = schedule.copy()

    out["revenue_constant_currency_eur"] = out.revenue.astype(float)
    out["revenue_per_fte_constant_currency"] = out.revenue_per_fte.astype(float)

    for idx, row in out.iterrows():
        month = str(row["month"])
        entity = str(row["entity"])
        currency = currencies.get(entity, "EUR")
        calibration_rate = float(calibration[currency])
        current_rate = float(fx.get((month, currency), 1.0 if currency == "EUR" else 0.0))
        if current_rate <= 0:
            raise ValueError(f"Missing FX for Workforce schedule: {entity} {currency} {month}")

        revenue_reference = float(row["revenue_constant_currency_eur"])
        revenue_local = _money(revenue_reference / calibration_rate)
        revenue_reported = _money(revenue_local * current_rate)
        out.at[idx, "functional_currency"] = currency
        out.at[idx, "fx_to_eur"] = current_rate
        out.at[idx, "revenue_local"] = revenue_local
        out.at[idx, "revenue"] = revenue_reported
        avg_fte = float(row["average_fte"])
        out.at[idx, "reported_revenue_per_fte"] = _money(revenue_reported / avg_fte) if avg_fte > 0.0001 else 0.0

        for column in MONEY_COLUMNS:
            reference = float(row[column])
            local = _money(reference / calibration_rate)
            reported = _money(local * current_rate)
            out.at[idx, f"{column}_constant_currency_eur"] = reference
            out.at[idx, f"{column}_local"] = local
            out.at[idx, column] = reported

    # Keep the primary productivity KPI constant-currency so FX cannot masquerade as
    # operating productivity. Reported Revenue/FTE remains available separately.
    out["revenue_per_fte"] = out.revenue_per_fte_constant_currency
    return out
