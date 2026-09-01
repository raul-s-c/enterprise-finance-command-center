from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .model import SimulationResult, simulate_operations as simulate_base_operations


FUNCTION_MIX = {
    "Software": {
        "R&D": 0.38,
        "Sales": 0.24,
        "Customer Success": 0.20,
        "G&A": 0.18,
    },
    "Hardware": {
        "Sales": 0.30,
        "Product Management": 0.20,
        "Supply Chain & Commercial Ops": 0.25,
        "G&A": 0.25,
    },
    "Events": {
        "Project Delivery": 0.45,
        "Sales": 0.20,
        "Program Management": 0.20,
        "G&A": 0.15,
    },
    "Spare Parts": {
        "Service Operations": 0.35,
        "Sales": 0.20,
        "Planning": 0.25,
        "G&A": 0.20,
    },
}

FUNCTION_COST_MULTIPLIER = {
    "R&D": 1.15,
    "Sales": 1.10,
    "Customer Success": 0.92,
    "G&A": 1.00,
    "Product Management": 1.12,
    "Supply Chain & Commercial Ops": 0.93,
    "Project Delivery": 0.90,
    "Program Management": 1.02,
    "Service Operations": 0.88,
    "Planning": 0.94,
}

DEFAULT_ENTITY_SALARY = {
    "DE01": 92000.0,
    "ES01": 62000.0,
    "US01": 118000.0,
    "JP01": 86000.0,
}

DEFAULT_REVENUE_PER_FTE = {
    "Software": 1_050_000.0,
    "Hardware": 1_500_000.0,
    "Events": 900_000.0,
    "Spare Parts": 1_250_000.0,
}

DEFAULT_NON_PEOPLE_OPEX_PCT = {
    "Software": 0.055,
    "Hardware": 0.030,
    "Events": 0.045,
    "Spare Parts": 0.030,
}


@dataclass(frozen=True)
class WorkforceResult:
    schedule: pd.DataFrame
    operations: pd.DataFrame


def _cfg(config: dict) -> dict:
    cfg = config.get("workforce", {})
    return {
        "fully_loaded_factor": float(cfg.get("fully_loaded_factor", 1.28)),
        "annual_attrition": float(cfg.get("annual_attrition", 0.11)),
        "hire_gap_closure": float(cfg.get("hire_gap_closure", 0.55)),
        "recruitment_cost_per_hire": float(cfg.get("recruitment_cost_per_hire", 7500.0)),
        "salary_growth": float(cfg.get("salary_growth", 0.032)),
        "productivity_growth": float(cfg.get("productivity_growth", 0.012)),
        "minimum_fte_per_entity_division": float(cfg.get("minimum_fte_per_entity_division", 5.0)),
        "entity_salary": {**DEFAULT_ENTITY_SALARY, **{str(k): float(v) for k, v in cfg.get("entity_base_salary", {}).items()}},
        "revenue_per_fte": {**DEFAULT_REVENUE_PER_FTE, **{str(k): float(v) for k, v in cfg.get("revenue_per_fte", {}).items()}},
        "non_people_opex_pct": {**DEFAULT_NON_PEOPLE_OPEX_PCT, **{str(k): float(v) for k, v in cfg.get("non_people_opex_pct", {}).items()}},
    }


def build_workforce_schedule(
    operations: pd.DataFrame,
    config: dict,
    macro: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build a deterministic workforce roll-forward from lagged business demand.

    Workforce is maintained at Month x Entity x Division x Function. Headcount is
    not generated at employee level. The target FTE reacts to trailing revenue with
    a hiring lag; attrition occurs continuously and excess capacity is primarily
    absorbed through natural attrition rather than automatic layoffs.
    """
    if operations.empty:
        return pd.DataFrame()
    settings = _cfg(config)
    monthly = operations.groupby(["month", "entity", "division"], as_index=False).revenue.sum()
    months = sorted(str(m) for m in monthly.month.unique())
    keys = monthly[["entity", "division"]].drop_duplicates().sort_values(["entity", "division"])
    revenue_lookup = {
        (str(r.month), str(r.entity), str(r.division)): float(r.revenue)
        for r in monthly.itertuples(index=False)
    }
    macro_inflation = {}
    if macro is not None and not macro.empty and "month" in macro.columns and "inflation" in macro.columns:
        macro_inflation = {str(r.month): float(r.inflation) for r in macro[["month", "inflation"]].itertuples(index=False)}

    rows: list[dict] = []
    ending_fte: dict[tuple[str, str, str], float] = {}
    revenue_history: dict[tuple[str, str], list[float]] = {}

    for month_idx, month in enumerate(months):
        for entity, division in keys.itertuples(index=False, name=None):
            entity = str(entity)
            division = str(division)
            revenue = float(revenue_lookup.get((month, entity, division), 0.0))
            pair = (entity, division)
            history = revenue_history.setdefault(pair, [])
            revenue_per_fte = float(settings["revenue_per_fte"][division])
            productivity = (1.0 + float(settings["productivity_growth"])) ** (month_idx / 12.0)
            effective_revenue_per_fte = revenue_per_fte * productivity
            minimum_total = float(settings["minimum_fte_per_entity_division"])

            if history:
                trailing_revenue = float(np.mean(history[-3:]))
            else:
                # Initial state approximates the pre-history workforce required to
                # support the first observed close. Subsequent months use only lagged
                # observable revenue.
                trailing_revenue = revenue
            target_total = max(minimum_total, trailing_revenue * 12.0 / max(effective_revenue_per_fte, 1.0))

            wage_inflation = max(float(settings["salary_growth"]), float(macro_inflation.get(month, 0.0)) * 0.55)
            entity_salary = float(settings["entity_salary"].get(entity, 80000.0))

            for function, mix in FUNCTION_MIX[division].items():
                target_fte = target_total * float(mix)
                key = (entity, division, function)
                if key not in ending_fte:
                    opening = target_fte
                else:
                    opening = ending_fte[key]
                attrition = opening * float(settings["annual_attrition"]) / 12.0
                after_attrition = max(opening - attrition, 0.0)
                gap = max(target_fte - after_attrition, 0.0)
                hires = gap * float(settings["hire_gap_closure"])
                ending = after_attrition + hires
                average_fte = (opening + ending) / 2.0
                annual_loaded_cost = (
                    entity_salary
                    * float(FUNCTION_COST_MULTIPLIER[function])
                    * float(settings["fully_loaded_factor"])
                    * (1.0 + wage_inflation) ** (month_idx / 12.0)
                )
                payroll = average_fte * annual_loaded_cost / 12.0
                recruitment = hires * float(settings["recruitment_cost_per_hire"])
                personnel_cost = payroll + recruitment
                ending_fte[key] = ending
                rows.append({
                    "month": month,
                    "entity": entity,
                    "division": division,
                    "function": function,
                    "opening_fte": round(opening, 4),
                    "target_fte": round(target_fte, 4),
                    "hires": round(hires, 4),
                    "attrition": round(attrition, 4),
                    "ending_fte": round(ending, 4),
                    "average_fte": round(average_fte, 4),
                    "annual_loaded_cost_per_fte": round(annual_loaded_cost, 2),
                    "payroll_cost": round(payroll, 2),
                    "recruitment_cost": round(recruitment, 2),
                    "personnel_cost": round(personnel_cost, 2),
                    "revenue": round(revenue * float(mix), 2),
                    "revenue_per_fte": round((revenue * float(mix)) / max(average_fte, 0.0001), 2),
                })
            history.append(revenue)

    return pd.DataFrame(rows)


def enrich_operations_with_workforce(
    operations: pd.DataFrame,
    workforce: pd.DataFrame,
    config: dict,
) -> pd.DataFrame:
    if operations.empty:
        return operations.copy()
    settings = _cfg(config)
    out = operations.copy()
    totals = workforce.groupby(["month", "entity", "division"], as_index=False).agg(
        personnel_cost=("personnel_cost", "sum"),
        opening_fte=("opening_fte", "sum"),
        hires=("hires", "sum"),
        attrition=("attrition", "sum"),
        ending_fte=("ending_fte", "sum"),
        average_fte=("average_fte", "sum"),
    )
    revenue_total = out.groupby(["month", "entity", "division"], as_index=False).revenue.sum().rename(columns={"revenue": "entity_division_revenue"})
    out = out.merge(totals, on=["month", "entity", "division"], how="left").merge(
        revenue_total, on=["month", "entity", "division"], how="left"
    )
    out["allocation_share"] = out.revenue / out.entity_division_revenue.replace(0.0, np.nan)
    out["allocation_share"] = out.allocation_share.fillna(0.0)
    out["personnel_cost_allocated"] = out.personnel_cost.fillna(0.0) * out.allocation_share
    out["workforce_opening_fte_allocated"] = out.opening_fte.fillna(0.0) * out.allocation_share
    out["workforce_hires_allocated"] = out.hires.fillna(0.0) * out.allocation_share
    out["workforce_attrition_allocated"] = out.attrition.fillna(0.0) * out.allocation_share
    out["workforce_ending_fte_allocated"] = out.ending_fte.fillna(0.0) * out.allocation_share
    out["workforce_average_fte_allocated"] = out.average_fte.fillna(0.0) * out.allocation_share
    out["non_people_opex"] = out.apply(
        lambda r: float(r.revenue) * float(settings["non_people_opex_pct"].get(str(r.division), 0.04)), axis=1
    )
    out["opex"] = out.non_people_opex + out.personnel_cost_allocated
    out["ebit_before_dep"] = out.gross_profit - out.opex
    return out.drop(columns=[
        "personnel_cost", "opening_fte", "hires", "attrition", "ending_fte", "average_fte",
        "entity_division_revenue", "allocation_share",
    ])


def simulate_operations_with_workforce(
    config: dict,
    months: pd.PeriodIndex,
    macro: pd.DataFrame,
) -> SimulationResult:
    base = simulate_base_operations(config, months, macro)
    workforce = build_workforce_schedule(base.operations, config, macro)
    enriched = enrich_operations_with_workforce(base.operations, workforce, config)
    return SimulationResult(
        operations=enriched,
        products=base.products,
        customers=base.customers,
        portfolio_events=base.portfolio_events,
    )


def workforce_rollforward_checks(workforce: pd.DataFrame) -> dict:
    if workforce.empty:
        return {
            "workforce_rollforward_max_gap": 0.0,
            "workforce_negative_fte_rows": 0,
            "passed": False,
        }
    gap = workforce.opening_fte - workforce.attrition + workforce.hires - workforce.ending_fte
    negative = int((workforce[["opening_fte", "hires", "attrition", "ending_fte", "average_fte"]].min(axis=1) < -0.0001).sum())
    max_gap = float(gap.abs().max())
    return {
        "workforce_rollforward_max_gap": round(max_gap, 4),
        "workforce_negative_fte_rows": negative,
        "passed": max_gap <= 0.001 and negative == 0,
    }


def allocation_checks(operations: pd.DataFrame, workforce: pd.DataFrame) -> dict:
    if operations.empty or workforce.empty:
        return {"workforce_personnel_allocation_max_gap": 0.0, "passed": False}
    target = workforce.groupby(["month", "entity", "division"], as_index=False).personnel_cost.sum()
    allocated = operations.groupby(["month", "entity", "division"], as_index=False).personnel_cost_allocated.sum()
    recon = target.merge(allocated, on=["month", "entity", "division"], how="outer", suffixes=("_schedule", "_allocated")).fillna(0.0)
    gap = float((recon.personnel_cost_schedule - recon.personnel_cost_allocated).abs().max()) if not recon.empty else 0.0
    return {"workforce_personnel_allocation_max_gap": round(gap, 2), "passed": gap <= 0.05}
