from __future__ import annotations

from dataclasses import dataclass
import hashlib

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

QUALITY_TIERS = {
    "Essential": {"code": "E", "price": 0.78, "cost": 0.84, "demand": 1.28, "selling": 1.08, "fixed": 0.95, "penetration": 0.58, "score": 1},
    "Professional": {"code": "P", "price": 1.00, "cost": 1.00, "demand": 1.00, "selling": 1.00, "fixed": 1.00, "penetration": 0.48, "score": 2},
    "Premium": {"code": "X", "price": 1.48, "cost": 1.22, "demand": 0.62, "selling": 0.92, "fixed": 1.10, "penetration": 0.34, "score": 3},
}

DIVISION_ECONOMICS = {
    "Software": {"prefix": "SW", "base_price": 1480.0, "cost_ratio": 0.17, "base_demand": 2.25, "variable_sell_pct": 0.035, "fixed_prod_pct": 0.045},
    "Hardware": {"prefix": "HW", "base_price": 24500.0, "cost_ratio": 0.60, "base_demand": 0.72, "variable_sell_pct": 0.055, "fixed_prod_pct": 0.055},
    "Events": {"prefix": "EV", "base_price": 146000.0, "cost_ratio": 0.49, "base_demand": 0.115, "variable_sell_pct": 0.065, "fixed_prod_pct": 0.055},
    "Spare Parts": {"prefix": "SP", "base_price": 1320.0, "cost_ratio": 0.47, "base_demand": 8.2, "variable_sell_pct": 0.075, "fixed_prod_pct": 0.035},
}

CATALOG = {
    "Software": [
        ("PLT", "Platform", [("Core Services", [("CORE", "Core Platform"), ("WF", "Workflow Engine")]), ("Edge Services", [("EDGE", "Edge Runtime"), ("API", "API Gateway")])], 1.00, 1.00),
        ("SEC", "Security", [("Identity", [("IAM", "Identity Access"), ("PAM", "Privileged Access")]), ("Protection", [("KMS", "Key Management"), ("CMP", "Compliance Monitor")])], 1.18, 0.78),
        ("ANL", "Analytics", [("Business Analytics", [("BI", "Business Intelligence"), ("FIN", "Finance Analytics")]), ("Advanced Analytics", [("PRD", "Predictive Analytics"), ("OPS", "Operations Analytics")])], 1.05, 0.88),
        ("AUT", "Automation", [("Orchestration", [("ORC", "Process Orchestrator"), ("RPA", "Automation Studio")]), ("Integration", [("INT", "Integration Hub"), ("MON", "Monitoring Suite")])], 1.10, 0.82),
    ],
    "Hardware": [
        ("CTL", "Control Systems", [("Controllers", [("MCU", "Compact Controller"), ("RCK", "Rack Controller")]), ("Resilient Control", [("RDN", "Redundant Controller"), ("SAF", "Safety Controller")])], 0.95, 1.08),
        ("EDG", "Edge Appliances", [("Gateways", [("GTW", "Industrial Gateway"), ("SEC", "Secure Gateway")]), ("Compute", [("CMP", "Edge Compute Node"), ("AI", "AI Edge Appliance")])], 1.12, 0.92),
        ("TRM", "Terminals", [("Fixed Terminals", [("FIX", "Fixed Terminal"), ("KSK", "Self-Service Kiosk")]), ("Mobile Terminals", [("MOB", "Mobile Terminal"), ("RUG", "Rugged Terminal")])], 0.88, 1.12),
        ("NET", "Network Devices", [("Access", [("ACC", "Access Node"), ("SWC", "Secure Switch")]), ("Distribution", [("DST", "Distribution Node"), ("RTR", "Secure Router")])], 1.02, 0.96),
        ("SEN", "Sensors & Readers", [("Readers", [("RFID", "RFID Reader"), ("BIO", "Biometric Reader")]), ("Sensing", [("CAM", "Vision Sensor"), ("HUB", "Sensor Hub")])], 0.72, 1.24),
    ],
    "Events": [
        ("DEP", "Deployment & Integration", [("Deployment", [("LCH", "Site Launch"), ("ROL", "Regional Rollout")]), ("Integration", [("MIG", "Migration Wave"), ("COM", "Commissioning Program")])], 1.15, 0.86),
        ("TRN", "Training & Enablement", [("Operational Training", [("OPR", "Operator Academy"), ("CRT", "Certification Program")]), ("Leadership Training", [("TEC", "Technical Bootcamp"), ("EXE", "Executive Workshop")])], 0.72, 1.28),
        ("EXP", "Customer Experience", [("Market Events", [("PRD", "Product Launch"), ("FOR", "Innovation Forum")]), ("Customer Events", [("USR", "User Conference"), ("DEM", "Demonstration Center")])], 1.32, 0.72),
        ("MNG", "Managed Programs", [("Partner Programs", [("PRT", "Partner Summit"), ("CUS", "Customer Council")]), ("Field Programs", [("RDS", "Regional Roadshow"), ("CERT", "Certification Roadshow")])], 0.92, 1.02),
    ],
    "Spare Parts": [
        ("MOD", "Control Modules", [("Electronic Boards", [("IO", "I/O Board"), ("CPU", "Processor Board")]), ("Power & Relay", [("PWR", "Power Module"), ("REL", "Relay Module")])], 1.28, 0.78),
        ("KIT", "Maintenance Kits", [("Preventive Kits", [("PRE", "Preventive Maintenance Kit"), ("CAL", "Calibration Kit")]), ("Overhaul Kits", [("OVR", "Overhaul Kit"), ("SAF", "Safety Service Kit")])], 0.82, 1.34),
        ("INT", "Interface Components", [("Network Interfaces", [("NET", "Network Interface"), ("USB", "Service Interface")]), ("User Interfaces", [("DSP", "Display Interface"), ("CNX", "Connector Set")])], 0.94, 1.05),
        ("MEC", "Mechanical Parts", [("Drive Components", [("DRV", "Drive Assembly"), ("FAN", "Cooling Fan")]), ("Enclosures", [("HSG", "Housing Kit"), ("COL", "Cooling Assembly")])], 1.05, 0.92),
        ("SEC", "Security Components", [("Secure Electronics", [("SEM", "Secure Element"), ("AUT", "Authentication Module")]), ("Input Devices", [("KPD", "Secure Keypad"), ("SNR", "Tamper Sensor")])], 1.20, 0.74),
        ("CON", "Consumables", [("Routine Consumables", [("FIL", "Filter Pack"), ("SEL", "Seal Pack")]), ("Power & Service", [("BAT", "Battery Pack"), ("LUB", "Service Lubricant Pack")])], 0.46, 1.68),
    ],
}

LEGACY_PRODUCTS = {
    "SW-PLT-API-E",
    "SW-SEC-CMP-E",
    "HW-CTL-MCU-E",
    "HW-EDG-GTW-E",
    "EV-DEP-COM-E",
    "EV-TRN-OPR-E",
    "SP-MOD-IO-E",
    "SP-INT-CNX-E",
}


@dataclass(frozen=True)
class SimulationResult:
    operations: pd.DataFrame
    products: pd.DataFrame
    customers: pd.DataFrame
    portfolio_events: pd.DataFrame


def _catalog_rows() -> list[dict]:
    rows: list[dict] = []
    for division, families in CATALOG.items():
        econ = DIVISION_ECONOMICS[division]
        for family_code, family_name, subfamilies, price_factor, demand_factor in families:
            type_index = 0
            for subfamily_name, product_types in subfamilies:
                for type_code, type_name in product_types:
                    type_index += 1
                    type_price = 0.90 + 0.07 * type_index
                    type_cost = 0.93 + 0.035 * type_index
                    type_demand = 1.14 - 0.07 * type_index
                    for tier_name, tier in QUALITY_TIERS.items():
                        product_id = f"{econ['prefix']}-{family_code}-{type_code}-{tier['code']}"
                        base_price = econ["base_price"] * price_factor * type_price * tier["price"]
                        base_cost = base_price * econ["cost_ratio"] * type_cost * tier["cost"]
                        base_demand = econ["base_demand"] * demand_factor * type_demand * tier["demand"]
                        row = {
                            "product": product_id,
                            "division": division,
                            "product_family": family_name,
                            "product_subfamily": subfamily_name,
                            "product_type": type_name,
                            "quality_tier": tier_name,
                            "quality_score": tier["score"],
                            "generation": "G2",
                            "strategic_role": "Volume" if tier_name == "Essential" else ("Core" if tier_name == "Professional" else "Premium"),
                            "name": f"Aureon {type_name} {tier_name}",
                            "base_price": round(base_price, 2),
                            "base_cost": round(base_cost, 2),
                            "base_demand": round(base_demand, 4),
                            "variable_sell_pct": round(econ["variable_sell_pct"] * tier["selling"], 5),
                            "fixed_prod_pct": round(econ["fixed_prod_pct"] * tier["fixed"], 5),
                            "portfolio_penetration": tier["penetration"],
                            "successor": "",
                            "initial_active": True,
                        }
                        if product_id in LEGACY_PRODUCTS:
                            legacy_cost_ratio = {"Software": 0.34, "Hardware": 0.72, "Events": 0.64, "Spare Parts": 0.58}[division]
                            row["generation"] = "G1 Legacy"
                            row["strategic_role"] = "Harvest"
                            row["base_cost"] = round(base_price * legacy_cost_ratio, 2)
                            successor = f"{product_id}-NXT"
                            row["successor"] = successor
                            successor_row = dict(row)
                            successor_row.update({
                                "product": successor,
                                "generation": "G3",
                                "strategic_role": "Growth",
                                "name": f"Aureon {type_name} NextGen {tier_name}",
                                "base_price": round(base_price * 1.08, 2),
                                "base_cost": round(base_price * legacy_cost_ratio * 0.76, 2),
                                "base_demand": round(base_demand * 1.12, 4),
                                "portfolio_penetration": min(float(tier["penetration"]) + 0.08, 0.82),
                                "successor": "",
                                "initial_active": False,
                            })
                            rows.append(row)
                            rows.append(successor_row)
                        else:
                            rows.append(row)
    return rows


def product_master() -> pd.DataFrame:
    frame = pd.DataFrame(_catalog_rows())
    frame["initial_active"] = frame["initial_active"].astype(bool)
    frame["catalog_rank"] = frame.groupby(["division", "product_family", "product_subfamily"]).cumcount() + 1
    return frame


def customer_master(seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed + 203)
    rows: list[dict] = []
    names = ["Northstar", "Meridian", "Kestrel", "Orion", "Helix", "Atlas", "Vector", "Nimbus", "Redwood", "Summit", "Pioneer", "Cobalt", "Keystone", "Vertex", "Axiom", "Nova"]
    idx = 0
    for entity, divisions in ENTITY_DIVISIONS.items():
        for division in divisions:
            count = {"Software": 7, "Hardware": 7, "Events": 5, "Spare Parts": 7}[division]
            for j in range(count):
                idx += 1
                size = float(np.clip(rng.lognormal(mean=0.0, sigma=0.38), 0.55, 2.1))
                segment = "Strategic" if size > 1.35 else ("Core" if size > 0.85 else "Growth")
                rows.append({
                    "customer": f"C{idx:03d}",
                    "customer_name": f"{names[(idx + j) % len(names)]} {entity}",
                    "entity": entity,
                    "division": division,
                    "customer_size": round(size, 4),
                    "segment": segment,
                    "portfolio_breadth": round(float(np.clip(rng.normal(1.0, 0.16), 0.68, 1.35)), 4),
                })
    return pd.DataFrame(rows)


def _stable_score(*values: str) -> float:
    digest = hashlib.sha256("|".join(values).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / float(2**64 - 1)


def _customer_product_eligible(customer: pd.Series, product: pd.Series) -> bool:
    penetration = float(product["portfolio_penetration"]) * float(customer["portfolio_breadth"])
    segment = str(customer["segment"])
    tier = str(product["quality_tier"])
    if segment == "Strategic":
        penetration += 0.12 if tier != "Essential" else 0.05
    elif segment == "Growth":
        penetration += 0.08 if tier == "Essential" else (-0.06 if tier == "Premium" else 0.0)
    score = _stable_score(str(customer["customer"]), str(product["product"]), str(product["product_family"]))
    return score < float(np.clip(penetration, 0.18, 0.86))


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
    for division, threshold_value in rules["minimum_gross_margin"].items():
        threshold = float(threshold_value)
        div = scope[scope["division"] == division]
        if div.empty:
            continue
        grouped = div.groupby("product", as_index=False).agg(revenue=("revenue", "sum"), gross_profit=("gross_profit", "sum"))
        grouped["gross_margin"] = grouped["gross_profit"] / grouped["revenue"].replace(0, np.nan)
        candidates = grouped[grouped["product"].isin(active_products) & (grouped["gross_margin"] < threshold)].sort_values(["gross_margin", "revenue"])
        for _, candidate in candidates.head(1).iterrows():
            product = str(candidate["product"])
            if product in pending:
                continue
            row = products.loc[products["product"] == product].iloc[0]
            successor = str(row.get("successor", "") or "")
            phaseout_month = current_month + int(rules["phaseout_delay_months"])
            launch_month = current_month + int(rules["replacement_delay_months"]) if successor else None
            pending[product] = {"phaseout": phaseout_month, "successor": successor, "launch": launch_month}
            base_event = {
                "month": str(current_month),
                "division": division,
                "product_family": str(row["product_family"]),
                "product_subfamily": str(row["product_subfamily"]),
                "product_type": str(row["product_type"]),
                "quality_tier": str(row["quality_tier"]),
            }
            events.append({
                **base_event, "product": product, "event": "PHASE_OUT_APPROVED", "effective_month": str(phaseout_month),
                "successor": successor, "gross_margin": round(float(candidate["gross_margin"]), 4),
                "reason": f"Trailing gross margin below {threshold:.0%} portfolio threshold",
            })
            if successor:
                successor_row = products.loc[products["product"] == successor].iloc[0]
                events.append({
                    "month": str(current_month), "division": division,
                    "product_family": str(successor_row["product_family"]), "product_subfamily": str(successor_row["product_subfamily"]),
                    "product_type": str(successor_row["product_type"]), "quality_tier": str(successor_row["quality_tier"]),
                    "product": successor, "event": "REPLACEMENT_APPROVED", "effective_month": str(launch_month),
                    "successor": "", "gross_margin": None, "reason": f"Replacement for {product}",
                })
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
                row = products.loc[products["product"].eq(product)].iloc[0]
                events.append({
                    "month": str(month), "division": str(row["division"]), "product_family": str(row["product_family"]),
                    "product_subfamily": str(row["product_subfamily"]), "product_type": str(row["product_type"]),
                    "quality_tier": str(row["quality_tier"]), "product": product, "event": "PHASE_OUT_EFFECTIVE",
                    "effective_month": str(month), "successor": item["successor"], "gross_margin": None, "reason": "Portfolio decision executed",
                })
            if item["successor"] and item["launch"] == month:
                active_products.add(item["successor"])
                row = products.loc[products["product"].eq(item["successor"])].iloc[0]
                events.append({
                    "month": str(month), "division": str(row["division"]), "product_family": str(row["product_family"]),
                    "product_subfamily": str(row["product_subfamily"]), "product_type": str(row["product_type"]),
                    "quality_tier": str(row["quality_tier"]), "product": item["successor"], "event": "PRODUCT_LAUNCH",
                    "effective_month": str(month), "successor": "", "gross_margin": None, "reason": f"Replacement for {product}",
                })

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
                        if not _customer_product_eligible(customer, product):
                            continue
                        size = float(customer["customer_size"])
                        base_demand = float(product["base_demand"])
                        noise = float(np.clip(rng.normal(1.0, 0.075 if division != "Events" else 0.16), 0.65, 1.35))
                        region = REGION_WEIGHT[entity]
                        tier = str(product["quality_tier"])
                        tier_demand_stability = {"Essential": 1.04, "Professional": 1.00, "Premium": 0.93}[tier]
                        price = float(product["base_price"]) * _price_index(inflation, i, 0.012 if division == "Software" else 0.006)

                        if division == "Software":
                            quantity = max(1.0, round(base_demand * size * region * trend * noise * tier_demand_stability, 0))
                            revenue = quantity * price * (0.94 + 0.06 * season)
                            cost_unit = float(product["base_cost"]) * (1 + 0.45 * (energy_factor - 1)) * (1 + inflation) ** (i / 12.0)
                        elif division == "Events":
                            expected = base_demand * size * region * trend * (0.72 + 0.28 * season) * tier_demand_stability
                            quantity = float(rng.poisson(max(expected, 0.025)))
                            if quantity == 0:
                                continue
                            revenue = quantity * price
                            cost_unit = float(product["base_cost"]) * (1 + inflation) ** (i / 12.0) * (0.98 + 0.08 * (energy_factor - 1))
                        else:
                            demand_macro = industrial_factor ** (1.18 if division == "Hardware" else 0.55)
                            quantity = max(0.0, round(base_demand * size * region * trend * season * demand_macro * noise * tier_demand_stability, 0))
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
                            "product": str(product["product"]), "product_family": str(product["product_family"]),
                            "product_subfamily": str(product["product_subfamily"]), "product_type": str(product["product_type"]),
                            "quality_tier": tier, "generation": str(product["generation"]), "strategic_role": str(product["strategic_role"]),
                            "quantity": float(quantity), "unit_price": round(price, 4),
                            "revenue": round(revenue, 2), "variable_production_cost": round(variable_production, 2),
                            "variable_selling_cost": round(variable_selling, 2), "fixed_production_cost": round(fixed_production, 2),
                            "marginal_contribution": round(marginal_contribution, 2), "gross_profit": round(gross_profit, 2),
                            "opex": round(opex, 2), "ebit_before_dep": round(ebit_before_dep, 2), "source_factory": factory,
                        })
        events.extend(_review_portfolio(month, i, rows, products, active_products, pending, config))

    operations = pd.DataFrame(rows)
    event_frame = pd.DataFrame(events)
    if event_frame.empty:
        event_frame = pd.DataFrame(columns=[
            "month", "division", "product_family", "product_subfamily", "product_type", "quality_tier",
            "product", "event", "effective_month", "successor", "gross_margin", "reason",
        ])
    return SimulationResult(operations=operations, products=products, customers=customers, portfolio_events=event_frame)
