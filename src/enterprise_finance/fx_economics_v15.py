from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

from .model import SimulationResult
from .workforce import simulate_operations_with_workforce


MONEY_COLUMNS_BUYER = [
    "revenue",
    "variable_selling_cost",
    "non_people_opex",
    "personnel_cost_allocated",
    "opex",
]


def _money(value: float) -> float:
    return round(float(value), 2)


def load_fx_policy(path: str = "config/fx-policy.yml") -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def _entity_currency(config: dict) -> dict[str, str]:
    return {str(row["code"]): str(row["currency"]) for row in config.get("entities", [])}


def _fx_lookup(macro: pd.DataFrame) -> dict[tuple[str, str], float]:
    currencies = [c for c in ["EUR", "USD", "JPY", "CNY", "CZK"] if c in macro.columns]
    out: dict[tuple[str, str], float] = {}
    for row in macro.itertuples(index=False):
        for currency in currencies:
            value = float(getattr(row, currency))
            if value > 0:
                out[(str(row.month), currency)] = value
    return out


def _translate_reference_amount(reference_eur: float, calibration_fx: float, current_fx: float) -> tuple[float, float]:
    """Return functional-currency amount and current reported EUR amount.

    The pre-FX operating model is treated as a constant-currency economic base.
    Dividing by a fixed calibration FX creates a stable local price/cost level.
    Translating that local amount at the monthly FX makes reported EUR performance
    respond to currency without letting spot FX alter underlying volume or local
    commercial economics.
    """
    local = float(reference_eur) / float(calibration_fx)
    reported = local * float(current_fx)
    return _money(local), _money(reported)


def apply_native_fx_to_operations(
    operations: pd.DataFrame,
    macro: pd.DataFrame,
    config: dict,
    fx_policy: dict,
) -> pd.DataFrame:
    if operations.empty:
        return operations.copy()

    entity_currency = _entity_currency(config)
    calibration = {str(k): float(v) for k, v in fx_policy["calibration_fx_to_eur"].items()}
    fx = _fx_lookup(macro)
    out = operations.copy()

    # Preserve the underlying constant-currency economics for auditability and
    # Workforce demand planning. Current columns are then overwritten with the
    # monthly EUR reporting translation.
    reference_columns = [
        "revenue", "variable_production_cost", "variable_selling_cost",
        "fixed_production_cost", "marginal_contribution", "gross_profit",
        "opex", "ebit_before_dep", "unit_price",
    ]
    for column in reference_columns:
        if column in out.columns:
            out[f"{column}_constant_currency_eur"] = out[column].astype(float)
    if "non_people_opex" in out.columns:
        out["non_people_opex_constant_currency_eur"] = out.non_people_opex.astype(float)
    if "personnel_cost_allocated" in out.columns:
        out["personnel_cost_allocated_constant_currency_eur"] = out.personnel_cost_allocated.astype(float)

    revenue_currency: list[str] = []
    revenue_local: list[float] = []
    manufacturing_currency: list[str] = []
    manufacturing_cost_local: list[float] = []

    for idx, row in out.iterrows():
        month = str(row["month"])
        entity = str(row["entity"])
        division = str(row["division"])
        buyer_currency = entity_currency.get(entity, "EUR")
        buyer_current = float(fx.get((month, buyer_currency), 1.0 if buyer_currency == "EUR" else 0.0))
        buyer_calibration = float(calibration[buyer_currency])
        if buyer_current <= 0:
            raise ValueError(f"Missing monthly FX for {entity} {buyer_currency} {month}")

        rev_local, rev_eur = _translate_reference_amount(float(row["revenue_constant_currency_eur"]), buyer_calibration, buyer_current)
        out.at[idx, "revenue"] = rev_eur
        revenue_currency.append(buyer_currency)
        revenue_local.append(rev_local)

        if "unit_price" in out.columns:
            price_local, price_eur = _translate_reference_amount(float(row["unit_price_constant_currency_eur"]), buyer_calibration, buyer_current)
            out.at[idx, "unit_price"] = price_eur
            out.at[idx, "unit_price_local"] = price_local

        # Selling costs and operating expenses belong to the commercial/legal
        # entity and therefore originate in that entity's functional currency.
        for column in ["variable_selling_cost", "non_people_opex", "personnel_cost_allocated", "opex"]:
            reference_column = f"{column}_constant_currency_eur"
            if column in out.columns and reference_column in out.columns:
                local, reported = _translate_reference_amount(float(row[reference_column]), buyer_calibration, buyer_current)
                out.at[idx, column] = reported
                out.at[idx, f"{column}_local"] = local

        # Software/Events delivery cost is local to the commercial entity. Physical
        # manufacturing economics originate in the source factory functional currency.
        source_factory = str(row.get("source_factory", ""))
        cost_entity = source_factory if division in {"Hardware", "Spare Parts"} and source_factory else entity
        cost_currency = entity_currency.get(cost_entity, buyer_currency)
        cost_current = float(fx.get((month, cost_currency), 1.0 if cost_currency == "EUR" else 0.0))
        cost_calibration = float(calibration[cost_currency])
        if cost_current <= 0:
            raise ValueError(f"Missing monthly FX for cost source {cost_entity} {cost_currency} {month}")

        direct_local, direct_eur = _translate_reference_amount(
            float(row["variable_production_cost_constant_currency_eur"]), cost_calibration, cost_current
        )
        fixed_local, fixed_eur = _translate_reference_amount(
            float(row["fixed_production_cost_constant_currency_eur"]), cost_calibration, cost_current
        )
        out.at[idx, "variable_production_cost"] = direct_eur
        out.at[idx, "fixed_production_cost"] = fixed_eur
        manufacturing_currency.append(cost_currency)
        manufacturing_cost_local.append(_money(direct_local + fixed_local))
        out.at[idx, "variable_production_cost_local"] = direct_local
        out.at[idx, "fixed_production_cost_local"] = fixed_local

        variable_selling = float(out.at[idx, "variable_selling_cost"])
        opex = float(out.at[idx, "opex"])
        marginal = _money(rev_eur - direct_eur - variable_selling)
        gross_profit = _money(marginal - fixed_eur)
        out.at[idx, "marginal_contribution"] = marginal
        out.at[idx, "gross_profit"] = gross_profit
        out.at[idx, "ebit_before_dep"] = _money(gross_profit - opex)

    out["revenue_currency"] = revenue_currency
    out["revenue_local"] = revenue_local
    out["manufacturing_currency"] = manufacturing_currency
    out["manufacturing_cost_local"] = manufacturing_cost_local
    return out


def simulate_operations_with_native_fx(
    config: dict,
    months: pd.PeriodIndex,
    macro: pd.DataFrame,
    fx_policy_path: str = "config/fx-policy.yml",
) -> SimulationResult:
    """Generate Workforce-aware operations, then translate native local economics."""
    base = simulate_operations_with_workforce(config, months, macro)
    policy = load_fx_policy(fx_policy_path)
    operations = apply_native_fx_to_operations(base.operations, macro, config, policy)
    return SimulationResult(
        operations=operations,
        products=base.products,
        customers=base.customers,
        portfolio_events=base.portfolio_events,
    )


def validate_native_fx_economics(operations: pd.DataFrame, macro: pd.DataFrame, config: dict, fx_policy: dict) -> dict:
    if operations.empty:
        return {
            "native_fx_revenue_roundtrip_max_gap": 0.0,
            "native_fx_missing_currency_rows": 1,
            "native_fx_reported_sensitivity_rows": 0,
            "passed": False,
        }
    entity_currency = _entity_currency(config)
    fx = _fx_lookup(macro)
    gaps: list[float] = []
    sensitive = 0
    missing = 0
    for row in operations.itertuples(index=False):
        entity = str(row.entity)
        month = str(row.month)
        currency = entity_currency.get(entity, "EUR")
        current = float(fx.get((month, currency), 1.0 if currency == "EUR" else 0.0))
        if current <= 0:
            missing += 1
            continue
        reconstructed = _money(float(row.revenue_local) * current)
        gaps.append(abs(reconstructed - float(row.revenue)))
        if currency != "EUR" and abs(float(row.revenue) - float(row.revenue_constant_currency_eur)) > 0.01:
            sensitive += 1
    max_gap = max(gaps) if gaps else 0.0
    return {
        "native_fx_revenue_roundtrip_max_gap": round(max_gap, 2),
        "native_fx_missing_currency_rows": int(missing),
        "native_fx_reported_sensitivity_rows": int(sensitive),
        "passed": max_gap <= 0.02 and missing == 0 and sensitive > 0,
    }
