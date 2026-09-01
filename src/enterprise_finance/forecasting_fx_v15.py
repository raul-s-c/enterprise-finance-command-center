from __future__ import annotations

import numpy as np
import pandas as pd

from .forecasting import forecast_accuracy, latest_forecast, validate_forecast_scale
from .forecasting_v14 import build_forecast_vintages as build_workforce_forecast_vintages
from .fx_economics_v15 import load_fx_policy


PHYSICAL_DIVISIONS = {"Hardware", "Spare Parts"}


def _money(value: float) -> float:
    return round(float(value), 2)


def _entity_currency(config: dict) -> dict[str, str]:
    return {str(row["code"]): str(row["currency"]) for row in config.get("entities", [])}


def _fx_lookup(macro: pd.DataFrame) -> dict[tuple[str, str], float]:
    currencies = [c for c in ["EUR", "USD", "JPY", "CNY", "CZK"] if c in macro.columns]
    return {
        (str(row.month), currency): float(getattr(row, currency))
        for row in macro.itertuples(index=False)
        for currency in currencies
        if float(getattr(row, currency)) > 0
    }


def _constant_currency_operations(operations: pd.DataFrame) -> pd.DataFrame:
    """Return a view suitable for business/workforce forecasting without FX noise."""
    out = operations.copy()
    mappings = {
        "revenue": "revenue_constant_currency_eur",
        "gross_profit": "gross_profit_constant_currency_eur",
        "marginal_contribution": "marginal_contribution_constant_currency_eur",
        "opex": "opex_constant_currency_eur",
        "personnel_cost_allocated": "personnel_cost_allocated_constant_currency_eur",
        "non_people_opex": "non_people_opex_constant_currency_eur",
    }
    for target, source in mappings.items():
        if source in out.columns:
            out[target] = out[source].astype(float)
    return out


def _factory_cost_shares(
    constant_ops: pd.DataFrame,
    vintage: str,
    entity: str,
    division: str,
) -> dict[str, float]:
    if division not in PHYSICAL_DIVISIONS or "source_factory" not in constant_ops.columns:
        return {}
    end = pd.Period(vintage, freq="M")
    scope = constant_ops[
        constant_ops.month.le(vintage)
        & constant_ops.month.ge(str(end - 5))
        & constant_ops.entity.eq(entity)
        & constant_ops.division.eq(division)
        & constant_ops.source_factory.ne("")
    ].copy()
    if scope.empty:
        return {}
    scope["factory_cost"] = (
        scope.variable_production_cost.astype(float)
        + scope.fixed_production_cost.astype(float)
    )
    grouped = scope.groupby("source_factory").factory_cost.sum()
    total = float(grouped.sum())
    if total <= 0.005:
        return {}
    return {str(factory): float(value) / total for factory, value in grouped.items()}


def _variable_selling_ratio(
    constant_ops: pd.DataFrame,
    vintage: str,
    entity: str,
    division: str,
) -> float:
    end = pd.Period(vintage, freq="M")
    scope = constant_ops[
        constant_ops.month.le(vintage)
        & constant_ops.month.ge(str(end - 5))
        & constant_ops.entity.eq(entity)
        & constant_ops.division.eq(division)
    ]
    revenue = float(scope.revenue.sum())
    return float(scope.variable_selling_cost.sum()) / revenue if revenue > 0.005 else 0.0


def _assumption_factor(
    currency: str,
    vintage: str,
    fx: dict[tuple[str, str], float],
    calibration: dict[str, float],
) -> tuple[float, float]:
    current = float(fx.get((vintage, currency), 1.0 if currency == "EUR" else 0.0))
    if current <= 0:
        raise ValueError(f"Missing FX assumption for {currency} at vintage {vintage}")
    return current, current / float(calibration[currency])


def _weighted_factory_factor(
    shares: dict[str, float],
    entity_currency: dict[str, str],
    vintage: str,
    fx: dict[tuple[str, str], float],
    calibration: dict[str, float],
    buyer_factor: float,
) -> float:
    if not shares:
        return buyer_factor
    factor = 0.0
    for factory, share in shares.items():
        currency = entity_currency.get(factory, "EUR")
        _, currency_factor = _assumption_factor(currency, vintage, fx, calibration)
        factor += float(share) * currency_factor
    return factor


def build_forecast_vintages(
    config: dict,
    operations: pd.DataFrame,
    months: pd.PeriodIndex,
    macro: pd.DataFrame,
    fx_policy_path: str = "config/fx-policy.yml",
) -> pd.DataFrame:
    """Build constant-currency business forecasts and translate them at vintage FX.

    A forecast vintage may use only FX known at that vintage. The current monthly FX
    is therefore frozen across the horizon. This avoids pretending to forecast FX and
    preserves historical-vintage integrity: later realized currency changes become a
    measurable source of forecast error rather than hindsight in the forecast.
    """
    constant_ops = _constant_currency_operations(operations)
    constant_fc = build_workforce_forecast_vintages(config, constant_ops, months)
    if constant_fc.empty:
        return constant_fc

    policy = load_fx_policy(fx_policy_path)
    calibration = {str(k): float(v) for k, v in policy["calibration_fx_to_eur"].items()}
    entity_currency = _entity_currency(config)
    fx = _fx_lookup(macro)
    out = constant_fc.copy()

    money_columns = [
        "revenue_forecast", "gross_profit_forecast", "marginal_contribution_forecast",
        "opex_forecast", "personnel_cost_forecast", "non_people_opex_forecast",
    ]
    for column in money_columns:
        if column in out.columns:
            out[f"{column}_constant_currency_eur"] = out[column].astype(float)

    out["functional_currency"] = "EUR"
    out["fx_assumption_to_eur"] = 1.0
    out["manufacturing_fx_factor"] = 1.0

    profile_cache: dict[tuple[str, str, str], tuple[float, dict[str, float]]] = {}

    for idx, row in out.iterrows():
        vintage = str(row["vintage"])
        entity = str(row["entity"])
        division = str(row["division"])
        currency = entity_currency.get(entity, "EUR")
        assumption_rate, buyer_factor = _assumption_factor(currency, vintage, fx, calibration)
        key = (vintage, entity, division)
        if key not in profile_cache:
            profile_cache[key] = (
                _variable_selling_ratio(constant_ops, vintage, entity, division),
                _factory_cost_shares(constant_ops, vintage, entity, division),
            )
        variable_sell_ratio, factory_shares = profile_cache[key]
        manufacturing_factor = _weighted_factory_factor(
            factory_shares, entity_currency, vintage, fx, calibration, buyer_factor
        )

        revenue_cc = float(row["revenue_forecast_constant_currency_eur"])
        gp_cc = float(row["gross_profit_forecast_constant_currency_eur"])
        mc_cc = float(row["marginal_contribution_forecast_constant_currency_eur"])
        variable_sell_cc = max(revenue_cc * variable_sell_ratio, 0.0)
        direct_cc = max(revenue_cc - mc_cc - variable_sell_cc, 0.0)
        fixed_cc = max(mc_cc - gp_cc, 0.0)

        revenue_reported = _money(revenue_cc * buyer_factor)
        variable_sell_reported = _money(variable_sell_cc * buyer_factor)
        direct_reported = _money(direct_cc * manufacturing_factor)
        fixed_reported = _money(fixed_cc * manufacturing_factor)
        mc_reported = _money(revenue_reported - direct_reported - variable_sell_reported)
        gp_reported = _money(mc_reported - fixed_reported)

        personnel_cc = float(row.get("personnel_cost_forecast_constant_currency_eur", 0.0))
        non_people_cc = float(row.get("non_people_opex_forecast_constant_currency_eur", 0.0))
        personnel_reported = _money(personnel_cc * buyer_factor)
        non_people_reported = _money(non_people_cc * buyer_factor)
        opex_reported = _money(personnel_reported + non_people_reported)

        out.at[idx, "functional_currency"] = currency
        out.at[idx, "fx_assumption_to_eur"] = assumption_rate
        out.at[idx, "manufacturing_fx_factor"] = manufacturing_factor
        out.at[idx, "revenue_forecast"] = revenue_reported
        out.at[idx, "marginal_contribution_forecast"] = mc_reported
        out.at[idx, "gross_profit_forecast"] = gp_reported
        out.at[idx, "personnel_cost_forecast"] = personnel_reported
        out.at[idx, "non_people_opex_forecast"] = non_people_reported
        out.at[idx, "opex_forecast"] = opex_reported
        out.at[idx, "variable_selling_forecast_constant_currency_eur"] = _money(variable_sell_cc)
        out.at[idx, "direct_cost_forecast_constant_currency_eur"] = _money(direct_cc)
        out.at[idx, "fixed_production_forecast_constant_currency_eur"] = _money(fixed_cc)

    return out


def validate_fx_forecast(
    forecasts: pd.DataFrame,
    operations: pd.DataFrame,
    macro: pd.DataFrame,
    config: dict,
) -> dict:
    if forecasts.empty:
        return {
            "fx_forecast_opex_identity_max_gap": 0.0,
            "fx_forecast_missing_assumption_rows": 1,
            "fx_forecast_fte_currency_sensitive_rows": 0,
            "passed": False,
        }
    opex_gap = float((
        forecasts.opex_forecast.astype(float)
        - forecasts.personnel_cost_forecast.astype(float)
        - forecasts.non_people_opex_forecast.astype(float)
    ).abs().max())
    missing = int((forecasts.fx_assumption_to_eur.astype(float) <= 0).sum())

    # FTE fields are generated before FX translation and therefore must be identical
    # across scenarios only according to business Revenue assumptions, never because
    # the same vintage FX assumption differs by horizon month.
    fte_currency_sensitive = 0
    for (_, entity, division, scenario), grp in forecasts.groupby(["vintage", "entity", "division", "scenario"]):
        if grp.fx_assumption_to_eur.nunique() > 1:
            fte_currency_sensitive += 1

    return {
        "fx_forecast_opex_identity_max_gap": round(opex_gap, 2),
        "fx_forecast_missing_assumption_rows": missing,
        "fx_forecast_vintage_rate_variation_groups": int(fte_currency_sensitive),
        "passed": opex_gap <= 0.02 and missing == 0 and fte_currency_sensitive == 0,
    }
