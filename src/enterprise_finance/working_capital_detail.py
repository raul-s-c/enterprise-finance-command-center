from __future__ import annotations

from collections import defaultdict
import math

import numpy as np
import pandas as pd


PHYSICAL_DIVISIONS = {"Hardware", "Spare Parts"}
AR_BUCKETS = ["current", "overdue_1_30", "overdue_31_60", "overdue_61_90", "overdue_90_plus"]
INVENTORY_BUCKETS = ["age_0_30", "age_31_60", "age_61_90", "age_91_180", "age_180_plus"]


def _stable_customer_risk(customer: str, segment: str, customer_size: float) -> float:
    base = {"Strategic": 1.7, "Core": 2.5, "Growth": 3.2}.get(segment, 2.5)
    checksum = sum((idx + 1) * ord(ch) for idx, ch in enumerate(customer))
    noise = ((checksum % 101) / 100.0 - 0.5) * 1.25
    size_relief = min(max(customer_size - 1.0, -0.5), 1.0) * 0.35
    return float(np.clip(base + noise - size_relief, 1.0, 5.0))


def _payment_terms(config: dict, division: str) -> int:
    wc = config.get("working_capital", {})
    terms = wc.get("payment_terms_days", {})
    defaults = {"Software": 30, "Hardware": 45, "Events": 30, "Spare Parts": 45}
    return int(terms.get(division, defaults.get(division, 30)))


def _ar_gl_balance(journal: pd.DataFrame) -> pd.DataFrame:
    ar = journal[journal.account.eq("1100_AR")].copy()
    if ar.empty:
        return pd.DataFrame(columns=["month", "entity", "division", "gl_ar"])
    ar["movement"] = ar.debit - ar.credit
    monthly = ar.groupby(["month", "entity", "division"], as_index=False).movement.sum()
    entities = sorted(monthly.entity.unique())
    divisions = sorted(monthly.division.unique())
    months = sorted(monthly.month.unique())
    current: dict[tuple[str, str], float] = defaultdict(float)
    rows: list[dict] = []
    for month in months:
        scope = monthly[monthly.month.eq(month)]
        for _, row in scope.iterrows():
            current[(str(row.entity), str(row.division))] += float(row.movement)
        for entity in entities:
            for division in divisions:
                value = current[(entity, division)]
                if abs(value) > 0.005 or ((monthly.entity.eq(entity)) & (monthly.division.eq(division))).any():
                    rows.append({"month": month, "entity": entity, "division": division, "gl_ar": value})
    return pd.DataFrame(rows)


def build_ar_aging(journal: pd.DataFrame, customers: pd.DataFrame, config: dict) -> pd.DataFrame:
    sales = journal[(journal.account.eq("1100_AR")) & (journal.journal_type.eq("sale")) & journal.debit.gt(0)].copy()
    collections = journal[(journal.account.eq("1100_AR")) & (journal.journal_type.eq("collection")) & journal.credit.gt(0)].copy()
    if sales.empty:
        return pd.DataFrame(columns=["month", "entity", "division", "customer", "customer_name", "customer_segment", "risk_score", "payment_terms_days", *AR_BUCKETS, "total_ar", "overdue_ar", "overdue_pct", "weighted_age_days"])

    meta = customers[["customer", "customer_name", "segment", "customer_size"]].drop_duplicates("customer").set_index("customer").to_dict("index")
    sale_months = sorted(set(sales.month.unique()) | set(collections.month.unique()))
    open_lots: dict[tuple[str, str], list[dict]] = defaultdict(list)
    snapshots: list[dict] = []

    sales_agg = sales.groupby(["month", "entity", "division", "customer"], as_index=False).debit.sum()
    collections_agg = collections.groupby(["month", "entity", "division"], as_index=False).credit.sum()

    for month in sale_months:
        period = pd.Period(month, freq="M")
        month_sales = sales_agg[sales_agg.month.eq(month)]
        for _, row in month_sales.iterrows():
            customer = str(row.customer)
            info = meta.get(customer, {})
            segment = str(info.get("segment", "Core"))
            size = float(info.get("customer_size", 1.0))
            open_lots[(str(row.entity), str(row.division))].append({
                "customer": customer,
                "customer_name": str(info.get("customer_name", customer)),
                "segment": segment,
                "risk_score": _stable_customer_risk(customer, segment, size),
                "invoice_month": period,
                "outstanding": float(row.debit),
                "terms_days": _payment_terms(config, str(row.division)),
            })

        month_collections = collections_agg[collections_agg.month.eq(month)]
        for _, row in month_collections.iterrows():
            key = (str(row.entity), str(row.division))
            remaining = float(row.credit)
            lots = open_lots[key]
            while remaining > 0.005 and any(lot["outstanding"] > 0.005 for lot in lots):
                candidates = [lot for lot in lots if lot["outstanding"] > 0.005]
                candidates.sort(
                    key=lambda lot: (
                        (period.ordinal - lot["invoice_month"].ordinal) * 30
                        - lot["risk_score"] * 12.0
                        - lot["terms_days"] * 0.15,
                        -lot["risk_score"],
                        lot["customer"],
                    ),
                    reverse=True,
                )
                lot = candidates[0]
                paid = min(remaining, float(lot["outstanding"]))
                lot["outstanding"] -= paid
                remaining -= paid
            if remaining > 0.02:
                raise RuntimeError(f"AR collection allocation exceeded open receivables for {month} {key}: {remaining:.2f}")

        for (entity, division), lots in open_lots.items():
            customer_rows: dict[str, dict] = {}
            for lot in lots:
                amount = float(lot["outstanding"])
                if amount <= 0.005:
                    continue
                age_days = max((period.ordinal - lot["invoice_month"].ordinal) * 30, 0)
                overdue_days = age_days - int(lot["terms_days"])
                if overdue_days <= 0:
                    bucket = "current"
                elif overdue_days <= 30:
                    bucket = "overdue_1_30"
                elif overdue_days <= 60:
                    bucket = "overdue_31_60"
                elif overdue_days <= 90:
                    bucket = "overdue_61_90"
                else:
                    bucket = "overdue_90_plus"
                customer = lot["customer"]
                if customer not in customer_rows:
                    customer_rows[customer] = {
                        "month": month,
                        "entity": entity,
                        "division": division,
                        "customer": customer,
                        "customer_name": lot["customer_name"],
                        "customer_segment": lot["segment"],
                        "risk_score": float(lot["risk_score"]),
                        "payment_terms_days": int(lot["terms_days"]),
                        **{b: 0.0 for b in AR_BUCKETS},
                        "weighted_age_value": 0.0,
                    }
                customer_rows[customer][bucket] += amount
                customer_rows[customer]["weighted_age_value"] += amount * age_days
            for row in customer_rows.values():
                total = sum(float(row[b]) for b in AR_BUCKETS)
                overdue = total - float(row["current"])
                row["total_ar"] = total
                row["overdue_ar"] = overdue
                row["overdue_pct"] = overdue / total if total else 0.0
                row["weighted_age_days"] = row.pop("weighted_age_value") / total if total else 0.0
                snapshots.append(row)

    return pd.DataFrame(snapshots)


def _inventory_gl_balance(journal: pd.DataFrame) -> pd.DataFrame:
    inv = journal[journal.account.eq("1200_INVENTORY")].copy()
    if inv.empty:
        return pd.DataFrame(columns=["month", "entity", "division", "gl_inventory"])
    inv["movement"] = inv.debit - inv.credit
    monthly = inv.groupby(["month", "entity", "division"], as_index=False).movement.sum()
    keys = monthly[["entity", "division"]].drop_duplicates().itertuples(index=False, name=None)
    key_list = [(str(e), str(d)) for e, d in keys]
    months = sorted(monthly.month.unique())
    current: dict[tuple[str, str], float] = defaultdict(float)
    rows: list[dict] = []
    for month in months:
        scope = monthly[monthly.month.eq(month)]
        for _, row in scope.iterrows():
            current[(str(row.entity), str(row.division))] += float(row.movement)
        for entity, division in key_list:
            value = current[(entity, division)]
            if abs(value) > 0.005:
                rows.append({"month": month, "entity": entity, "division": division, "gl_inventory": value})
    return pd.DataFrame(rows)


def _inventory_bucket_values(total: float, monthly_usage: float, months_since_sale: int) -> dict[str, float]:
    buckets = {b: 0.0 for b in INVENTORY_BUCKETS}
    if total <= 0.0:
        return buckets
    if monthly_usage <= 0.005:
        buckets["age_180_plus"] = total
        return buckets
    coverage = total / monthly_usage
    remaining = total
    layer = 0
    while remaining > 0.005 and layer < 36:
        amount = min(monthly_usage, remaining)
        age_days = (months_since_sale + layer) * 30
        if age_days <= 30:
            bucket = "age_0_30"
        elif age_days <= 60:
            bucket = "age_31_60"
        elif age_days <= 90:
            bucket = "age_61_90"
        elif age_days <= 180:
            bucket = "age_91_180"
        else:
            bucket = "age_180_plus"
        buckets[bucket] += amount
        remaining -= amount
        layer += 1
    if remaining > 0.005:
        buckets["age_180_plus"] += remaining
    if coverage < 1.0 and buckets["age_0_30"] > total:
        buckets["age_0_30"] = total
    return buckets


def build_inventory_aging(journal: pd.DataFrame, operations: pd.DataFrame, products: pd.DataFrame, config: dict) -> pd.DataFrame:
    gl = _inventory_gl_balance(journal)
    if gl.empty:
        return pd.DataFrame(columns=["month", "entity", "division", "product", "product_family", "product_subfamily", "product_type", "quality_tier", "generation", *INVENTORY_BUCKETS, "inventory_value", "monthly_usage", "coverage_months", "months_since_sale", "slow_moving_value", "obsolescence_risk_value", "stock_status"])

    markup = float(config["transfer_pricing"]["manufacturing_cost_plus"])
    physical = operations[operations.division.isin(PHYSICAL_DIVISIONS)].copy()
    physical["inventory_cogs"] = (physical.variable_production_cost + physical.fixed_production_cost) * (1.0 + markup)
    monthly_product = physical.groupby(["month", "entity", "division", "product"], as_index=False).inventory_cogs.sum()
    product_meta = products.set_index("product").to_dict("index")
    rows: list[dict] = []

    for _, gl_row in gl.iterrows():
        month = str(gl_row.month)
        period = pd.Period(month, freq="M")
        entity = str(gl_row.entity)
        division = str(gl_row.division)
        total_inventory = max(float(gl_row.gl_inventory), 0.0)
        if total_inventory <= 0.005:
            continue
        hist = monthly_product[(monthly_product.entity.eq(entity)) & (monthly_product.division.eq(division)) & (monthly_product.month.le(month))].copy()
        if hist.empty:
            continue
        hist["period"] = pd.PeriodIndex(hist.month, freq="M")
        trailing12 = hist[hist.period.ge(period - 11)]
        trailing3 = hist[hist.period.ge(period - 2)]
        usage12 = trailing12.groupby("product").inventory_cogs.mean().to_dict()
        usage3 = trailing3.groupby("product").inventory_cogs.mean().to_dict()
        last_sale = hist.groupby("product").period.max().to_dict()
        product_set = sorted(set(usage12) | set(usage3))
        weights: dict[str, float] = {}
        for product in product_set:
            meta = product_meta.get(product, {})
            recent = float(usage3.get(product, 0.0))
            long_run = float(usage12.get(product, 0.0))
            quality = str(meta.get("quality_tier", "Professional"))
            generation = str(meta.get("generation", "Current"))
            strategic = str(meta.get("strategic_role", "Core"))
            tier_factor = {"Essential": 1.12, "Professional": 1.0, "Premium": 0.86}.get(quality, 1.0)
            generation_factor = 1.55 if generation == "Legacy" else 1.0
            strategic_factor = 1.20 if strategic in {"Aftermarket", "Cash Generator"} else (0.85 if strategic in {"Growth", "Strategic Growth"} else 1.0)
            division_factor = 1.25 if division == "Spare Parts" else 1.0
            weights[product] = max(recent * 0.78 + long_run * 0.22, long_run * 0.35, 1.0) * tier_factor * generation_factor * strategic_factor * division_factor
        weight_sum = sum(weights.values()) or 1.0

        allocated: list[tuple[str, float]] = []
        running = 0.0
        for idx, product in enumerate(product_set):
            if idx == len(product_set) - 1:
                value = total_inventory - running
            else:
                value = total_inventory * weights[product] / weight_sum
                running += value
            allocated.append((product, max(value, 0.0)))

        for product, value in allocated:
            meta = product_meta.get(product, {})
            usage = max(float(usage3.get(product, 0.0)), float(usage12.get(product, 0.0)) * 0.55)
            last = last_sale.get(product, period)
            months_since_sale = max(period.ordinal - last.ordinal, 0)
            buckets = _inventory_bucket_values(value, usage, months_since_sale)
            slow = float(buckets["age_91_180"] + buckets["age_180_plus"])
            legacy = str(meta.get("generation", "Current")) == "Legacy"
            obsolescence = float(buckets["age_180_plus"] + (0.30 if legacy else 0.10) * buckets["age_91_180"])
            coverage = value / usage if usage > 0.005 else 99.0
            if buckets["age_180_plus"] > value * 0.15:
                status = "Obsolescence risk"
            elif slow > value * 0.25:
                status = "Slow moving"
            elif coverage > 4.0:
                status = "Excess"
            else:
                status = "Healthy"
            rows.append({
                "month": month,
                "entity": entity,
                "division": division,
                "product": product,
                "product_family": str(meta.get("product_family", "")),
                "product_subfamily": str(meta.get("product_subfamily", "")),
                "product_type": str(meta.get("product_type", "")),
                "quality_tier": str(meta.get("quality_tier", "")),
                "generation": str(meta.get("generation", "")),
                **buckets,
                "inventory_value": value,
                "monthly_usage": usage,
                "coverage_months": coverage,
                "months_since_sale": months_since_sale,
                "slow_moving_value": slow,
                "obsolescence_risk_value": obsolescence,
                "stock_status": status,
            })

    return pd.DataFrame(rows)


def ar_aging_summary(ar_aging: pd.DataFrame) -> pd.DataFrame:
    if ar_aging.empty:
        return pd.DataFrame(columns=["month", *AR_BUCKETS, "total_ar", "overdue_ar", "overdue_pct", "weighted_risk"])
    grouped = ar_aging.groupby("month", as_index=False).agg(
        **{bucket: (bucket, "sum") for bucket in AR_BUCKETS},
        total_ar=("total_ar", "sum"),
        overdue_ar=("overdue_ar", "sum"),
    )
    risk = ar_aging.assign(risk_value=ar_aging.total_ar * ar_aging.risk_score).groupby("month", as_index=False).agg(risk_value=("risk_value", "sum"))
    grouped = grouped.merge(risk, on="month", how="left")
    grouped["overdue_pct"] = grouped.overdue_ar / grouped.total_ar.replace(0, np.nan)
    grouped["weighted_risk"] = grouped.risk_value / grouped.total_ar.replace(0, np.nan)
    return grouped.drop(columns="risk_value").fillna(0.0)


def inventory_aging_summary(inventory_aging: pd.DataFrame) -> pd.DataFrame:
    if inventory_aging.empty:
        return pd.DataFrame(columns=["month", *INVENTORY_BUCKETS, "inventory_value", "slow_moving_value", "obsolescence_risk_value", "slow_moving_pct", "obsolescence_risk_pct"])
    grouped = inventory_aging.groupby("month", as_index=False).agg(
        **{bucket: (bucket, "sum") for bucket in INVENTORY_BUCKETS},
        inventory_value=("inventory_value", "sum"),
        slow_moving_value=("slow_moving_value", "sum"),
        obsolescence_risk_value=("obsolescence_risk_value", "sum"),
    )
    grouped["slow_moving_pct"] = grouped.slow_moving_value / grouped.inventory_value.replace(0, np.nan)
    grouped["obsolescence_risk_pct"] = grouped.obsolescence_risk_value / grouped.inventory_value.replace(0, np.nan)
    return grouped.fillna(0.0)


def validate_working_capital_schedules(journal: pd.DataFrame, ar_aging: pd.DataFrame, inventory_aging: pd.DataFrame) -> dict:
    ar_gl = _ar_gl_balance(journal)
    if ar_aging.empty:
        ar_sched = pd.DataFrame(columns=["month", "entity", "division", "schedule_ar"])
        ar_bucket_gap = 0.0
    else:
        ar_sched = ar_aging.groupby(["month", "entity", "division"], as_index=False).total_ar.sum().rename(columns={"total_ar": "schedule_ar"})
        ar_bucket_gap = float((ar_aging[AR_BUCKETS].sum(axis=1) - ar_aging.total_ar).abs().max())
    ar_recon = ar_gl.merge(ar_sched, on=["month", "entity", "division"], how="outer").fillna(0.0)
    ar_gap = float((ar_recon.gl_ar - ar_recon.schedule_ar).abs().max()) if not ar_recon.empty else 0.0

    inv_gl = _inventory_gl_balance(journal)
    if inventory_aging.empty:
        inv_sched = pd.DataFrame(columns=["month", "entity", "division", "schedule_inventory"])
        inv_bucket_gap = 0.0
    else:
        inv_sched = inventory_aging.groupby(["month", "entity", "division"], as_index=False).inventory_value.sum().rename(columns={"inventory_value": "schedule_inventory"})
        inv_bucket_gap = float((inventory_aging[INVENTORY_BUCKETS].sum(axis=1) - inventory_aging.inventory_value).abs().max())
    inv_recon = inv_gl.merge(inv_sched, on=["month", "entity", "division"], how="outer").fillna(0.0)
    inv_gap = float((inv_recon.gl_inventory - inv_recon.schedule_inventory).abs().max()) if not inv_recon.empty else 0.0

    checks = {
        "ar_subledger_max_gap": round(ar_gap, 2),
        "ar_aging_bucket_max_gap": round(ar_bucket_gap, 2),
        "inventory_schedule_max_gap": round(inv_gap, 2),
        "inventory_aging_bucket_max_gap": round(inv_bucket_gap, 2),
    }
    checks["passed"] = all(abs(float(value)) <= 0.05 for value in checks.values())
    return checks
