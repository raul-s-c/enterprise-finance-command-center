from __future__ import annotations

import numpy as np
import pandas as pd


SOFTWARE_RECURRING_SHARE = {
    "Platform": 0.92,
    "Security": 0.90,
    "Analytics": 0.84,
    "Automation": 0.82,
}

PRODUCT_ATTRIBUTES = [
    "product_family", "product_subfamily", "product_type", "quality_tier",
    "generation", "strategic_role",
]


def _with_product_attributes(frame: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    missing = [column for column in PRODUCT_ATTRIBUTES if column not in frame.columns]
    if not missing:
        return frame.copy()
    lookup = products[["product", *missing]].drop_duplicates("product")
    return frame.merge(lookup, on="product", how="left")


def software_subscription_schedule(operations: pd.DataFrame, products: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    sw = operations[operations.division.eq("Software")].copy()
    if sw.empty:
        return pd.DataFrame(), pd.DataFrame()
    sw = _with_product_attributes(sw, products)
    detail = sw.groupby(
        ["month", "entity", "customer", "product", "product_family", "quality_tier"], as_index=False
    ).agg(revenue=("revenue", "sum"))
    detail["recurring_share"] = detail.product_family.map(SOFTWARE_RECURRING_SHARE).fillna(0.85)
    detail["mrr"] = detail.revenue * detail.recurring_share
    detail["services_revenue"] = detail.revenue - detail.mrr

    months = pd.period_range(detail.month.min(), detail.month.max(), freq="M").astype(str)
    keys = detail[["entity", "customer", "product", "product_family", "quality_tier"]].drop_duplicates()
    grid = keys.merge(pd.DataFrame({"month": months}), how="cross")
    grid = grid.merge(
        detail[["month", "entity", "customer", "product", "product_family", "quality_tier", "revenue", "mrr", "services_revenue"]],
        on=["month", "entity", "customer", "product", "product_family", "quality_tier"],
        how="left",
    ).fillna({"revenue": 0.0, "mrr": 0.0, "services_revenue": 0.0})
    grid = grid.sort_values(["entity", "customer", "product", "month"]).reset_index(drop=True)
    grid["opening_mrr"] = grid.groupby(["entity", "customer", "product"]).mrr.shift(1).fillna(0.0)
    prev = grid.opening_mrr
    cur = grid.mrr
    grid["new_mrr"] = np.where((prev <= 0.005) & (cur > 0.005), cur, 0.0)
    grid["churn_mrr"] = np.where((prev > 0.005) & (cur <= 0.005), prev, 0.0)
    grid["expansion_mrr"] = np.where((prev > 0.005) & (cur > prev), cur - prev, 0.0)
    grid["contraction_mrr"] = np.where((prev > 0.005) & (cur > 0.005) & (cur < prev), prev - cur, 0.0)
    grid["ending_mrr"] = cur
    grid["arr"] = grid.ending_mrr * 12.0
    grid["new_arr"] = grid.new_mrr * 12.0
    grid["expansion_arr"] = grid.expansion_mrr * 12.0
    grid["contraction_arr"] = grid.contraction_mrr * 12.0
    grid["churn_arr"] = grid.churn_mrr * 12.0
    grid["rollforward_gap"] = (
        grid.opening_mrr + grid.new_mrr + grid.expansion_mrr
        - grid.contraction_mrr - grid.churn_mrr - grid.ending_mrr
    )

    summary = grid.groupby(["month", "entity"], as_index=False).agg(
        revenue=("revenue", "sum"),
        services_revenue=("services_revenue", "sum"),
        opening_mrr=("opening_mrr", "sum"),
        ending_mrr=("ending_mrr", "sum"),
        new_mrr=("new_mrr", "sum"),
        expansion_mrr=("expansion_mrr", "sum"),
        contraction_mrr=("contraction_mrr", "sum"),
        churn_mrr=("churn_mrr", "sum"),
        arr=("arr", "sum"),
        new_arr=("new_arr", "sum"),
        expansion_arr=("expansion_arr", "sum"),
        contraction_arr=("contraction_arr", "sum"),
        churn_arr=("churn_arr", "sum"),
    )
    summary["recurring_revenue"] = summary.ending_mrr
    summary["recurring_mix"] = summary.recurring_revenue / summary.revenue.replace(0, np.nan)
    summary["nrr"] = (
        summary.opening_mrr + summary.expansion_mrr - summary.contraction_mrr - summary.churn_mrr
    ) / summary.opening_mrr.replace(0, np.nan)
    summary["grr"] = (
        summary.opening_mrr - summary.contraction_mrr - summary.churn_mrr
    ) / summary.opening_mrr.replace(0, np.nan)
    summary["arr_rollforward_gap"] = (
        summary.opening_mrr + summary.new_mrr + summary.expansion_mrr
        - summary.contraction_mrr - summary.churn_mrr - summary.ending_mrr
    ) * 12.0
    return grid, summary.fillna(0.0)


def events_backlog_schedule(operations: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    evt = operations[operations.division.eq("Events")].copy()
    if evt.empty:
        return pd.DataFrame()
    evt = _with_product_attributes(evt, products)
    revenue = evt.groupby(["month", "entity", "product_family"], as_index=False).agg(
        recognized_revenue=("revenue", "sum"),
        project_units=("quantity", "sum"),
    )
    rows: list[dict] = []
    for (entity, family), grp in revenue.groupby(["entity", "product_family"]):
        grp = grp.sort_values("month")
        opening = 0.0
        history: list[float] = []
        checksum = sum(ord(c) for c in f"{entity}-{family}")
        for idx, r in enumerate(grp.itertuples(index=False)):
            recognized = float(r.recognized_revenue)
            seasonal = 1.0 + 0.13 * np.sin((idx + checksum % 12) / 2.4)
            commercial_momentum = 1.0 + ((checksum % 9) - 4) * 0.008
            planned = max(recognized * seasonal * commercial_momentum, 0.0)
            bookings = max(planned, recognized - opening)
            ending = opening + bookings - recognized
            history.append(recognized)
            run_rate = float(np.mean(history[-3:])) if history else 0.0
            rows.append({
                "month": str(r.month),
                "entity": str(entity),
                "product_family": str(family),
                "opening_backlog": opening,
                "bookings": bookings,
                "recognized_revenue": recognized,
                "ending_backlog": ending,
                "book_to_bill": bookings / recognized if recognized else 0.0,
                "backlog_coverage_months": ending / run_rate if run_rate else 0.0,
                "project_units": float(r.project_units),
                "rollforward_gap": opening + bookings - recognized - ending,
            })
            opening = ending
    return pd.DataFrame(rows)


def hardware_factory_schedule(
    operations: pd.DataFrame,
    products: pd.DataFrame,
    factory: pd.DataFrame,
    config: dict,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if factory.empty:
        return pd.DataFrame(), pd.DataFrame()
    econ = factory.copy()
    econ["fixed_factory_cost"] = econ.factory.map(lambda x: float(config["factories"][x]["fixed_monthly_cost"]))
    econ["absorbed_fixed_cost"] = econ.fixed_factory_cost * econ.utilization.clip(lower=0.0, upper=1.0)
    econ["under_absorption"] = econ.fixed_factory_cost - econ.absorbed_fixed_cost
    econ["capacity_headroom_units"] = (econ.capacity_units - econ.produced_units).clip(lower=0.0)
    econ["fixed_cost_per_produced_unit"] = econ.fixed_factory_cost / econ.produced_units.replace(0, np.nan)
    econ["headroom_pct"] = econ.capacity_headroom_units / econ.capacity_units.replace(0, np.nan)
    econ["utilization_check"] = econ.produced_units / econ.capacity_units.replace(0, np.nan) - econ.utilization
    econ = econ.fillna(0.0)

    hw = operations[operations.division.eq("Hardware") & operations.source_factory.ne("")].copy()
    if hw.empty:
        return econ, pd.DataFrame()
    hw = _with_product_attributes(hw, products)
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


def spare_parts_schedule(
    operations: pd.DataFrame,
    inventory_aging: pd.DataFrame,
) -> pd.DataFrame:
    months = sorted(operations.month.unique())
    entities = sorted(set(operations.loc[operations.division.eq("Spare Parts"), "entity"]))
    if not months or not entities:
        return pd.DataFrame()
    hw = operations[operations.division.eq("Hardware")].groupby(["month", "entity"], as_index=False).agg(hardware_units=("quantity", "sum"))
    sp = operations[operations.division.eq("Spare Parts")].groupby(["month", "entity"], as_index=False).agg(
        spare_parts_revenue=("revenue", "sum"),
        spare_parts_units=("quantity", "sum"),
        active_skus=("product", "nunique"),
    )
    inv = inventory_aging[inventory_aging.division.eq("Spare Parts")].groupby(["month", "entity"], as_index=False).agg(
        inventory_value=("inventory_value", "sum"),
        monthly_usage=("monthly_usage", "sum"),
        slow_moving_value=("slow_moving_value", "sum"),
        obsolescence_risk_value=("obsolescence_risk_value", "sum"),
    ) if not inventory_aging.empty else pd.DataFrame(columns=["month", "entity", "inventory_value", "monthly_usage", "slow_moving_value", "obsolescence_risk_value"])

    base = pd.MultiIndex.from_product([months, entities], names=["month", "entity"]).to_frame(index=False)
    base = base.merge(hw, on=["month", "entity"], how="left").merge(sp, on=["month", "entity"], how="left").merge(inv, on=["month", "entity"], how="left").fillna(0.0)
    rows: list[dict] = []
    installed: dict[str, float] = {entity: 0.0 for entity in entities}
    monthly_survival = 0.995
    for r in base.sort_values(["month", "entity"]).itertuples(index=False):
        entity = str(r.entity)
        opening = installed[entity]
        additions = float(r.hardware_units)
        retirements = opening * (1.0 - monthly_survival)
        ending = opening - retirements + additions
        installed[entity] = ending
        inventory = float(r.inventory_value)
        usage = float(r.monthly_usage)
        risk_value = max(float(r.slow_moving_value), float(r.obsolescence_risk_value))
        health = 1.0 - min(risk_value / inventory, 1.0) if inventory > 0.0 else 1.0
        rows.append({
            "month": str(r.month),
            "entity": entity,
            "opening_installed_base": opening,
            "hardware_additions": additions,
            "estimated_retirements": retirements,
            "ending_installed_base": ending,
            "spare_parts_revenue": float(r.spare_parts_revenue),
            "spare_parts_units": float(r.spare_parts_units),
            "active_skus": int(r.active_skus),
            "revenue_per_installed_unit": float(r.spare_parts_revenue) / ending if ending else 0.0,
            "inventory_value": inventory,
            "inventory_coverage_months": inventory / usage if usage > 0.005 else 0.0,
            "inventory_health_pct": health,
            "installed_base_rollforward_gap": opening - retirements + additions - ending,
        })
    return pd.DataFrame(rows)


def validate_operating_schedules(
    operations: pd.DataFrame,
    software_detail: pd.DataFrame,
    software_summary: pd.DataFrame,
    events: pd.DataFrame,
    factory_economics: pd.DataFrame,
    spare_parts: pd.DataFrame,
) -> dict:
    checks: dict[str, float | bool] = {}
    if software_detail.empty:
        checks["software_revenue_reconciliation_max_gap"] = 0.0
        checks["software_arr_rollforward_max_gap"] = 0.0
    else:
        sw_actual = operations[operations.division.eq("Software")].groupby("month", as_index=False).revenue.sum().rename(columns={"revenue": "actual_revenue"})
        sw_schedule = software_detail.groupby("month", as_index=False).revenue.sum().rename(columns={"revenue": "schedule_revenue"})
        sw_recon = sw_actual.merge(sw_schedule, on="month", how="outer").fillna(0.0)
        checks["software_revenue_reconciliation_max_gap"] = round(float((sw_recon.actual_revenue - sw_recon.schedule_revenue).abs().max()), 2)
        checks["software_arr_rollforward_max_gap"] = round(float(software_summary.arr_rollforward_gap.abs().max()), 2) if not software_summary.empty else 0.0
    checks["events_backlog_rollforward_max_gap"] = round(float(events.rollforward_gap.abs().max()), 2) if not events.empty else 0.0
    checks["factory_utilization_recalculation_max_gap"] = round(float(factory_economics.utilization_check.abs().max()), 4) if not factory_economics.empty else 0.0
    checks["spare_parts_installed_base_rollforward_max_gap"] = round(float(spare_parts.installed_base_rollforward_gap.abs().max()), 4) if not spare_parts.empty else 0.0
    tolerances = {
        "software_revenue_reconciliation_max_gap": 0.05,
        "software_arr_rollforward_max_gap": 0.05,
        "events_backlog_rollforward_max_gap": 0.05,
        "factory_utilization_recalculation_max_gap": 0.0001,
        "spare_parts_installed_base_rollforward_max_gap": 0.0001,
    }
    checks["passed"] = all(abs(float(checks[key])) <= tolerance for key, tolerance in tolerances.items())
    return checks
