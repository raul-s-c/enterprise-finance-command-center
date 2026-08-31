from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


SEASONALITY = {1: 0.88, 2: 0.92, 3: 0.99, 4: 1.01, 5: 1.03, 6: 1.05, 7: 0.95, 8: 0.84, 9: 1.04, 10: 1.08, 11: 1.12, 12: 1.18}

ENTITY_DIVISIONS = {
    "DE01": ["Software", "Hardware"],
    "ES01": ["Hardware", "Events", "Spare Parts"],
    "US01": ["Software", "Hardware", "Events"],
    "JP01": ["Software", "Hardware", "Spare Parts"],
}

REGION_WEIGHT = {"DE01": 1.15, "ES01": 0.82, "US01": 1.35, "JP01": 0.92}

PRODUCT_ROWS = [
    {"product": "SW-CORE", "division": "Software", "name": "Aureon Core Platform", "base_price": 1420.0, "base_cost": 250.0, "base_demand": 18.0, "variable_sell_pct": 0.035, "fixed_prod_pct": 0.045, "successor": ""},
    {"product": "SW-EDGE", "division": "Software", "name": "Aureon Edge Suite", "base_price": 1960.0, "base_cost": 360.0, "base_demand": 13.0, "variable_sell_pct": 0.045, "fixed_prod_pct": 0.050, "successor": ""},
    {"product": "SW-ANL", "division": "Software", "name": "Aureon Analytics", "base_price": 1160.0, "base_cost": 190.0, "base_demand": 11.0, "variable_sell_pct": 0.030, "fixed_prod_pct": 0.040, "successor": ""},
    {"product": "HW-A100", "division": "Hardware", "name": "A100 Control Unit", "base_price": 17600.0, "base_cost": 10800.0, "base_demand": 3.8, "variable_sell_pct": 0.055, "fixed_prod_pct": 0.055, "successor": ""},
    {"product": "HW-A200", "division": "Hardware", "name": "A200 Secure Controller", "base_price": 28900.0, "base_cost": 17700.0, "base_demand": 2.9, "variable_sell_pct": 0.050, "fixed_prod_pct": 0.060, "successor": ""},
    {"product": "HW-B100", "division": "Hardware", "name": "B100 Edge Appliance", "base_price": 23900.0, "base_cost": 15700.0, "base_demand": 3.2, "variable_sell_pct": 0.060, "fixed_prod_pct": 0.060, "successor": ""},
    {"product": "HW-B200", "division": "Hardware", "name": "B200 Legacy Appliance", "base_price": 20500.0, "base_cost": 16750.0, "base_demand": 2.4, "variable_sell_pct": 0.065, "fixed_prod_pct": 0.060, "successor": "HW-C300"},
    {"product": "HW-C300", "division": "Hardware", "name": "C300 NextGen Appliance", "base_price": 26800.0, "base_cost": 15900.0, "base_demand": 3.4, "variable_sell_pct": 0.050, "fixed_prod_pct": 0.055, "successor": "", "initial_active": False},
    {"product": "EVT-INT", "division": "Events", "name": "Integration Event", "base_price": 155000.0, "base_cost": 76000.0, "base_demand": 0.58, "variable_sell_pct": 0.065, "fixed_prod_pct": 0.055, "successor": ""},
    {"product": "EVT-TRN", "division": "Events", "name": "Training Program", "base_price": 82000.0, "base_cost": 40500.0, "base_demand": 0.82, "variable_sell_pct": 0.055, "fixed_prod_pct": 0.050, "successor": ""},
    {"product": "EVT-LCH", "division": "Events", "name": "Launch Experience", "base_price": 225000.0, "base_cost": 118000.0, "base_demand": 0.42, "variable_sell_pct": 0.075, "fixed_prod_pct": 0.060, "successor": ""},
    {"product": "SP-MOD-01", "division": "Spare Parts", "name": "Control Module S1", "base_price": 1420.0, "base_cost": 690.0, "base_demand": 32.0, "variable_sell_pct": 0.075, "fixed_prod_pct": 0.035, "successor": ""},
    {"product": "SP-MOD-02", "division": "Spare Parts", "name": "Control Module S2", "base_price": 2180.0, "base_cost": 1080.0, "base_demand": 22.0, "variable_sell_pct": 0.070, "fixed_prod_pct": 0.035, "successor": ""},
    {"product": "SP-KIT-01", "division": "Spare Parts", "name": "Maintenance Kit K1", "base_price": 730.0, "base_cost": 315.0, "base_demand": 44.0, "variable_sell_pct": 0.080, "fixed_prod_pct": 0.030, "successor": ""},
    {"product": "SP-KIT-02", "division": "Spare Parts", "name": "Maintenance Kit K2", "base_price": 990.0, "base_cost": 430.0, "base_demand": 35.0, "variable_sell_pct": 0.075, "fixed_prod_pct": 0.030, "successor": ""},
    {"product": "SP-LEG-01", "division": "Spare Parts", "name": "Legacy Service Board", "base_price": 1250.0, "base_cost": 890.0, "base_demand": 18.0, "variable_sell_pct": 0.085, "fixed_prod_pct": 0.035, "successor": "SP-NXT-01"},
    {"product": "SP-LEG-02", "division": "Spare Parts", "name": "Legacy Interface Kit", "base_price": 860.0, "base_cost": 585.0, "base_demand": 20.0, "variable_sell_pct": 0.085, "fixed_prod_pct": 0.035, "successor": ""},
    {"product": "SP-NXT-01", "division": "Spare Parts", "name": "NextGen Service Board", "base_price": 1540.0, "base_cost": 720.0, "base_demand": 25.0, "variable_sell_pct": 0.070, "fixed_prod_pct": 0.030, "successor": "", "initial_active": False},
]


@dataclass(frozen=True)
class SimulationResult:
    operations: pd.DataFrame
    products: pd.DataFrame
    customers: pd.DataFrame
    portfolio_events: pd.DataFrame


def product_master() -> pd.DataFrame:
    frame = pd.DataFrame(PRODUCT_ROWS)
    if "initial_active" not in frame:
        frame["initial_active"] = True
    frame["initial_active"] = frame["initial_active"].map(lambda x: True if pd.isna(x) else bool(x))
    return frame


def customer_master(seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed + 203)
    rows: list[dict] = []
    names = ["Northstar", "Meridian", "Kestrel", "Orion", "Helix", "Atlas", "Vector", "Nimbus", "Redwood", "Summit", "Pioneer", "Cobalt", "Keystone", "Vertex", "Axiom", "Nova"]
    idx = 0
    for entity, divisions in ENTITY_DIVISIONS.items():
        for division in divisions:
            count = {"Software": 6, "Hardware": 5, "Events": 4, "Spare Parts": 5}[division]
            for j in range(count):
                idx += 1
                size = float(np.clip(rng.lognormal(mean=0.0, sigma=0.38), 0.55, 2.1))
                rows.append({
                    "customer": f"C{idx:03d}",
                    "customer_name": f"{names[(idx + j) % len(names)]} {entity}",
                    "entity": entity,
                    "division": division,
                    "customer_size": round(size, 4),
                    "segment": "Strategic" if size > 1.35 else ("Core" if size > 0.85 else "Growth"),
                })
    return pd.DataFrame(rows)


def _factory_for(entity: str, product: str, month_index: int) -> str:
    key = sum((i + 1) * ord(ch) for i, ch in enumerate(product)) + month_index
    if entity in {"DE01", "ES01"}:
        return "CZ01" if key % 100 < 68 else "CN01"
    if entity == "JP01":
        return "CN01" if key % 100 < 72 else "CZ01"
    return "CN01" if key % 100 < 58 else "CZ01"


def _price_index(inflation: float, month_index: int, annual_extra: float = 0.01) -> float:
    monthly = ((1 + max(inflation, 0.0) + annual_extra) ** (1 / 12)) - 1
    return (1 + monthly) ** month_index


def _review_portfolio(current_month: pd.Period, month_index: int, operations_so_far: list[dict], products: pd.DataFrame, active_products: set[str], pending: dict[str, dict], config: dict) -> list[dict]:
    rules = config["portfolio_rules"]
    trailing = int(rules["trailing_months"])
    frequency = int(rules["review_frequency_months"])
    if month_index + 1 < trailing or (month_index + 1) % frequency != 0:
        return []
    ops = pd.DataFrame(operations_so_far)
    if ops.empty:
        return []
    start = current_month - (trailing - 1)
    scope = ops[(ops["month"] >= str(start)) & (ops["month"] <= str(current_month))]
    events: list[dict] = []
    for division in ("Hardware", "Spare Parts"):
        threshold = float(rules["minimum_gross_margin"][division])
        div = scope[scope["division"] == division]
        if div.empty:
            continue
        grouped = div.groupby("product", as_index=False).agg(revenue=("revenue", "sum"), gross_profit=("gross_profit", "sum"))
        grouped["gross_margin"] = grouped["gross_profit"] / grouped["revenue"].replace(0, np.nan)
        candidates = grouped[grouped["product"].isin(active_products) & (grouped["gross_margin"] < threshold)].sort_values("gross_margin")
        for _, candidate in candidates.head(1).iterrows():
            product = str(candidate["product"])
            if product in pending:
                continue
            row = products.loc[products["product"] == product].iloc[0]
            successor = str(row.get("successor", "") or "")
            phaseout_month = current_month + int(rules["phaseout_delay_months"])
            launch_month = current_month + int(rules["replacement_delay_months"]) if successor else None
            pending[product] = {"phaseout": phaseout_month, "successor": successor, "launch": launch_month}
            events.append({"month": str(current_month), "division": division, "product": product, "event": "PHASE_OUT_APPROVED", "effective_month": str(phaseout_month), "successor": successor, "gross_margin": round(float(candidate["gross_margin"]), 4), "reason": f"Trailing gross margin below {threshold:.0%} portfolio threshold"})
            if successor:
                events.append({"month": str(current_month), "division": division, "product": successor, "event": "REPLACEMENT_APPROVED", "effective_month": str(launch_month), "successor": "", "gross_margin": None, "reason": f"Replacement for {product}"})
    return events


def simulate_operations(config: dict, months: pd.PeriodIndex, macro: pd.DataFrame) -> SimulationResult:
    seed = int(config["group"]["seed"])
    rng = np.random.default_rng(seed + 17)
    products = product_master()
    customers = customer_master(seed)
    active_products = set(products.loc[products["initial_active"], "product"])
    pending: dict[str, dict] = {}
    events: list[dict] = []
    rows: list[dict] = []
    customer_lookup = customers.groupby(["entity", "division"])

    for i, month in enumerate(months):
        for product, item in list(pending.items()):
            if item["phaseout"] == month and product in active_products:
                active_products.remove(product)
                events.append({"month": str(month), "division": products.loc[products["product"].eq(product), "division"].iloc[0], "product": product, "event": "PHASE_OUT_EFFECTIVE", "effective_month": str(month), "successor": item["successor"], "gross_margin": None, "reason": "Portfolio decision executed"})
            if item["successor"] and item["launch"] == month:
                active_products.add(item["successor"])
                events.append({"month": str(month), "division": products.loc[products["product"].eq(item["successor"]), "division"].iloc[0], "product": item["successor"], "event": "PRODUCT_LAUNCH", "effective_month": str(month), "successor": "", "gross_margin": None, "reason": f"Replacement for {product}"})

        m = macro.iloc[i]
        inflation = float(m["inflation"])
        industrial_factor = float(m["industrial_index"]) / 100.0
        energy_factor = float(m["energy_index"]) / 100.0
        for entity, divisions in ENTITY_DIVISIONS.items():
            for division in divisions:
                div_cfg = config["divisions"][division]
                annual_growth = float(div_cfg["annual_growth"])
                trend = (1 + annual_growth) ** (i / 12.0)
                season = SEASONALITY[month.month]
                product_scope = products[(products["division"] == division) & products["product"].isin(active_products)]
                cust_scope = customer_lookup.get_group((entity, division))
                for _, customer in cust_scope.iterrows():
                    for _, product in product_scope.iterrows():
                        size = float(customer["customer_size"])
                        base_demand = float(product["base_demand"])
                        noise = float(np.clip(rng.normal(1.0, 0.075 if division != "Events" else 0.16), 0.65, 1.35))
                        region = REGION_WEIGHT[entity]
                        price = float(product["base_price"]) * _price_index(inflation, i, 0.012 if division == "Software" else 0.006)

                        if division == "Software":
                            quantity = max(1.0, round(base_demand * size * region * trend * noise, 0))
                            revenue = quantity * price * (0.94 + 0.06 * season)
                            cost_unit = float(product["base_cost"]) * (1 + 0.45 * (energy_factor - 1)) * (1 + inflation) ** (i / 12.0)
                        elif division == "Events":
                            expected = base_demand * size * region * trend * (0.72 + 0.28 * season)
                            quantity = float(rng.poisson(max(expected, 0.05)))
                            if quantity == 0:
                                continue
                            revenue = quantity * price
                            cost_unit = float(product["base_cost"]) * (1 + inflation) ** (i / 12.0) * (0.98 + 0.08 * (energy_factor - 1))
                        else:
                            demand_macro = industrial_factor ** (1.18 if division == "Hardware" else 0.55)
                            quantity = max(0.0, round(base_demand * size * region * trend * season * demand_macro * noise, 0))
                            if quantity == 0:
                                continue
                            revenue = quantity * price
                            energy_sens = 0.18 if division == "Hardware" else 0.10
                            cost_unit = float(product["base_cost"]) * (1 + energy_sens * (energy_factor - 1)) * (1 + inflation * 0.55) ** (i / 12.0)

                        variable_production = quantity * cost_unit
                        variable_selling = revenue * float(product["variable_sell_pct"])
                        fixed_production = revenue * float(product["fixed_prod_pct"])
                        marginal_contribution = revenue - variable_production - variable_selling
                        gross_profit = marginal_contribution - fixed_production
                        opex_pct = {"Software": 0.205, "Hardware": 0.095, "Events": 0.135, "Spare Parts": 0.095}[division]
                        opex = revenue * opex_pct
                        ebit_before_dep = gross_profit - opex
                        factory = _factory_for(entity, str(product["product"]), i) if division in {"Hardware", "Spare Parts"} else ""
                        rows.append({
                            "month": str(month), "entity": entity, "division": division,
                            "customer": str(customer["customer"]), "customer_segment": str(customer["segment"]),
                            "product": str(product["product"]), "quantity": float(quantity), "unit_price": round(price, 4),
                            "revenue": round(revenue, 2), "variable_production_cost": round(variable_production, 2),
                            "variable_selling_cost": round(variable_selling, 2), "fixed_production_cost": round(fixed_production, 2),
                            "marginal_contribution": round(marginal_contribution, 2), "gross_profit": round(gross_profit, 2),
                            "opex": round(opex, 2), "ebit_before_dep": round(ebit_before_dep, 2), "source_factory": factory,
                        })
        events.extend(_review_portfolio(month, i, rows, products, active_products, pending, config))

    operations = pd.DataFrame(rows)
    event_frame = pd.DataFrame(events)
    if event_frame.empty:
        event_frame = pd.DataFrame(columns=["month", "division", "product", "event", "effective_month", "successor", "gross_margin", "reason"])
    return SimulationResult(operations=operations, products=products, customers=customers, portfolio_events=event_frame)
