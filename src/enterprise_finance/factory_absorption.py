from __future__ import annotations

import numpy as np
import pandas as pd

from .reporting import management_pnl


FINANCIAL_ACCOUNTS = ["6100_DEPRECIATION", "7000_INTEREST", "7100_TAX"]


def management_pnl_with_factory_absorption(
    operations: pd.DataFrame,
    journal: pd.DataFrame,
    factory_entities: list[str] | set[str],
) -> pd.DataFrame:
    """Extend the operating management P&L with factory-only economics.

    Commercial operating rows already contain standard fixed production overhead.
    Factory rows add the difference between that standard absorption and actual
    factory fixed cost, plus factory depreciation, interest and tax that would
    otherwise be omitted because manufacturing entities do not book external
    customer revenue in the operating dataset.
    """
    base = management_pnl(operations, journal).copy()
    base["factory_absorption_variance"] = 0.0

    factories = set(factory_entities)
    scope = journal[
        journal.entity.isin(factories)
        & ~journal.journal_type.eq("closing")
        & journal.account.isin(["5450_FACTORY_ABSORPTION_VARIANCE", *FINANCIAL_ACCOUNTS])
    ].copy()
    if scope.empty:
        return base

    scope["amount"] = scope.debit - scope.credit
    pivot = scope.pivot_table(
        index=["month", "entity"], columns="account", values="amount", aggfunc="sum", fill_value=0.0
    ).reset_index()
    for account in ["5450_FACTORY_ABSORPTION_VARIANCE", *FINANCIAL_ACCOUNTS]:
        if account not in pivot.columns:
            pivot[account] = 0.0

    rows: list[dict] = []
    for r in pivot.itertuples(index=False):
        variance = float(getattr(r, "5450_FACTORY_ABSORPTION_VARIANCE"))
        depreciation = float(getattr(r, "6100_DEPRECIATION"))
        interest = float(getattr(r, "7000_INTEREST"))
        tax = float(getattr(r, "7100_TAX"))
        gross_profit = -variance
        ebit = gross_profit - depreciation
        ebt = ebit - interest
        rows.append({
            "month": str(r.month),
            "entity": str(r.entity),
            "division": "Hardware",
            "revenue": 0.0,
            "variable_production_cost": 0.0,
            "variable_selling_cost": 0.0,
            "fixed_production_cost": variance,
            "marginal_contribution": 0.0,
            "gross_profit": gross_profit,
            "opex": 0.0,
            "depreciation": depreciation,
            "ebit": ebit,
            "interest": interest,
            "ebt": ebt,
            "tax": tax,
            "net_income": ebt - tax,
            "factory_absorption_variance": variance,
        })

    factory_rows = pd.DataFrame(rows)
    return pd.concat([base, factory_rows], ignore_index=True, sort=False).fillna(0.0)


def hardware_factory_accounting_schedule(
    operations: pd.DataFrame,
    products: pd.DataFrame,
    factory: pd.DataFrame,
    config: dict,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build factory economics from accounting-engine absorption outputs."""
    if factory.empty:
        return pd.DataFrame(), pd.DataFrame()

    econ = factory.copy()
    if "actual_fixed_factory_cost" not in econ:
        econ["actual_fixed_factory_cost"] = econ.factory.map(lambda x: float(config["factories"][x]["fixed_monthly_cost"]))
    if "absorbed_fixed_cost" not in econ:
        econ["absorbed_fixed_cost"] = econ.actual_fixed_factory_cost * econ.utilization.clip(lower=0.0, upper=1.0)
    if "absorption_variance" not in econ:
        econ["absorption_variance"] = econ.actual_fixed_factory_cost - econ.absorbed_fixed_cost
    if "under_absorption" not in econ:
        econ["under_absorption"] = econ.absorption_variance.clip(lower=0.0)
    if "over_absorption" not in econ:
        econ["over_absorption"] = (-econ.absorption_variance).clip(lower=0.0)
    if "fixed_cost_absorption_pct" not in econ:
        econ["fixed_cost_absorption_pct"] = econ.absorbed_fixed_cost / econ.actual_fixed_factory_cost.replace(0, np.nan)

    econ["fixed_factory_cost"] = econ.actual_fixed_factory_cost
    econ["capacity_headroom_units"] = (econ.capacity_units - econ.produced_units).clip(lower=0.0)
    econ["fixed_cost_per_produced_unit"] = econ.actual_fixed_factory_cost / econ.produced_units.replace(0, np.nan)
    econ["headroom_pct"] = econ.capacity_headroom_units / econ.capacity_units.replace(0, np.nan)
    econ["utilization_check"] = econ.produced_units / econ.capacity_units.replace(0, np.nan) - econ.utilization
    econ["absorption_rollforward_gap"] = econ.actual_fixed_factory_cost - econ.absorbed_fixed_cost - econ.absorption_variance
    econ = econ.fillna(0.0)

    hw = operations[operations.division.eq("Hardware") & operations.source_factory.ne("")].copy()
    if hw.empty:
        return econ, pd.DataFrame()

    missing = [c for c in ["product_family", "quality_tier"] if c not in hw.columns]
    if missing:
        hw = hw.merge(products[["product", *missing]].drop_duplicates("product"), on="product", how="left")
    mix = hw.groupby(["month", "source_factory", "product_family", "quality_tier"], as_index=False).agg(
        units=("quantity", "sum"),
        revenue=("revenue", "sum"),
        gross_profit=("gross_profit", "sum"),
    )
    totals = mix.groupby(["month", "source_factory"], as_index=False).units.sum().rename(columns={"units": "factory_units_in_sales"})
    mix = mix.merge(totals, on=["month", "source_factory"], how="left")
    mix["unit_mix_pct"] = mix.units / mix.factory_units_in_sales.replace(0, np.nan)
    mix["gross_margin_pct"] = mix.gross_profit / mix.revenue.replace(0, np.nan)
    return econ, mix.fillna(0.0)
