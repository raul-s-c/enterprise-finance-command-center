from __future__ import annotations

from collections import defaultdict
import hashlib

import numpy as np
import pandas as pd


AP_BUCKETS = ["current", "overdue_1_30", "overdue_31_60", "overdue_61_90", "overdue_90_plus"]

CATEGORY_META = {
    "factory_cost": ("Manufacturing Supply", "MFG", 5, 8),
    "factory_absorption_variance": ("Factory Fixed Cost", "FAC", 5, 2),
    "variable_selling": ("Logistics & Freight", "LOG", 4, 4),
    "service_cost": ("Delivery Partners", "DEL", 4, 5),
    "fixed_production": ("Delivery Capacity", "CAP", 4, 3),
    "opex": ("Corporate Services", "OPS", 3, 6),
}

CATEGORY_NAMES = {
    "MFG": "Industrial Supply",
    "FAC": "Facilities Services",
    "LOG": "Logistics Partner",
    "DEL": "Delivery Partner",
    "CAP": "Capacity Provider",
    "OPS": "Business Services",
    "GEN": "General Supplier",
}


def _stable_bucket(value: str, buckets: int) -> int:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return int(digest[:12], 16) % max(buckets, 1)


def _supplier_for_row(row: pd.Series) -> dict:
    category, code, criticality, count = CATEGORY_META.get(
        str(row.journal_type), ("General Suppliers", "GEN", 2, 4)
    )
    seed = "|".join([
        str(row.entity), str(row.division), str(row.journal_type),
        str(row.get("product", "")), str(row.get("customer", "")), str(row.journal_id),
    ])
    bucket = _stable_bucket(seed, count) + 1
    supplier = f"SUP-{row.entity}-{code}-{bucket:02d}"
    supplier_name = f"{CATEGORY_NAMES.get(code, 'Supplier')} {row.entity} {bucket:02d}"
    single_source = bool(criticality >= 4 and _stable_bucket(f"single|{supplier}", 100) < 16)
    return {
        "supplier": supplier,
        "supplier_name": supplier_name,
        "supplier_category": category,
        "supplier_criticality": criticality,
        "single_source": single_source,
    }


def _terms_days(config: dict, division: str, category: str) -> int:
    category_terms = config.get("supplier_management", {}).get("payment_terms_days", {})
    if category in category_terms:
        return int(category_terms[category])
    return int(round(float(config.get("divisions", {}).get(division, {}).get("dpo", 45))))


def _ap_gl_balance(journal: pd.DataFrame) -> pd.DataFrame:
    """Return cumulative legal AP by month and legal entity.

    Division remains an analytical source attribute on supplier lots, but the
    liability itself is reconciled at legal-entity level. This matches the
    accounting engine, where factory payments can settle cost accrued for more
    than one commercial division.
    """
    ap = journal[journal.account.eq("2100_AP")].copy()
    if ap.empty:
        return pd.DataFrame(columns=["month", "entity", "gl_ap"])
    ap["movement"] = ap.credit - ap.debit
    monthly = ap.groupby(["month", "entity"], as_index=False).movement.sum()
    months = sorted(monthly.month.unique())
    entities = sorted(monthly.entity.unique())
    running: dict[str, float] = defaultdict(float)
    rows: list[dict] = []
    for month in months:
        scope = monthly[monthly.month.eq(month)]
        for _, row in scope.iterrows():
            running[str(row.entity)] += float(row.movement)
        for entity in entities:
            value = running[entity]
            if abs(value) > 0.005:
                rows.append({"month": month, "entity": entity, "gl_ap": value})
    return pd.DataFrame(rows)


def build_ap_aging(journal: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Reconstruct supplier-level AP while reconciling to legal-entity AP."""
    ap = journal[journal.account.eq("2100_AP")].copy()
    if ap.empty:
        return pd.DataFrame(columns=[
            "month", "entity", "division", "supplier", "supplier_name", "supplier_category",
            "supplier_criticality", "single_source", "payment_terms_days", *AP_BUCKETS,
            "total_ap", "overdue_ap", "overdue_pct", "weighted_age_days", "trailing_12m_spend",
            "supplier_spend_share", "group_top5_spend_concentration", "group_supplier_count_trailing12",
        ])

    accruals = ap[ap.credit.gt(0.005)].copy()
    reductions = ap[ap.debit.gt(0.005)].copy()
    if accruals.empty:
        return pd.DataFrame()

    supplier_fields = accruals.apply(_supplier_for_row, axis=1, result_type="expand")
    accruals = pd.concat([accruals.reset_index(drop=True), supplier_fields.reset_index(drop=True)], axis=1)
    accruals["terms_days"] = [
        _terms_days(config, str(division), str(category))
        for division, category in zip(accruals.division, accruals.supplier_category)
    ]

    accrual_monthly = accruals.groupby(
        ["month", "entity", "division", "supplier", "supplier_name", "supplier_category",
         "supplier_criticality", "single_source", "terms_days"],
        as_index=False,
    ).credit.sum()
    spend_monthly = accrual_monthly.groupby(["month", "division", "supplier"], as_index=False).credit.sum()
    supplier_spend_monthly = accrual_monthly.groupby(["month", "supplier"], as_index=False).credit.sum()

    # Keep the posting division as a settlement preference, but allocate against
    # any open legal-entity AP if that preferred division is insufficient.
    reduction_monthly = reductions.groupby(
        ["month", "entity", "division", "journal_type"], as_index=False
    ).debit.sum()
    months = sorted(set(accrual_monthly.month.unique()) | set(reduction_monthly.month.unique()))
    open_lots: dict[str, list[dict]] = defaultdict(list)
    snapshots: list[dict] = []

    for month in months:
        period = pd.Period(month, freq="M")
        for _, row in accrual_monthly[accrual_monthly.month.eq(month)].iterrows():
            open_lots[str(row.entity)].append({
                "division": str(row.division),
                "supplier": str(row.supplier),
                "supplier_name": str(row.supplier_name),
                "supplier_category": str(row.supplier_category),
                "supplier_criticality": int(row.supplier_criticality),
                "single_source": bool(row.single_source),
                "accrual_month": period,
                "outstanding": float(row.credit),
                "terms_days": int(row.terms_days),
            })

        month_reductions = reduction_monthly[reduction_monthly.month.eq(month)].copy()
        month_reductions["priority"] = month_reductions.journal_type.eq(
            "factory_absorption_variance"
        ).map({True: 0, False: 1})

        for _, row in month_reductions.sort_values(["priority", "entity", "division"]).iterrows():
            entity = str(row.entity)
            posted_division = str(row.division)
            remaining = float(row.debit)
            lots = open_lots[entity]
            while remaining > 0.005:
                candidates = [lot for lot in lots if lot["outstanding"] > 0.005]
                if not candidates:
                    raise RuntimeError(
                        f"AP reduction exceeded legal-entity open payables for {month} {entity}: {remaining:.2f}"
                    )

                if str(row.journal_type) == "factory_absorption_variance":
                    preferred = [lot for lot in candidates if lot["supplier_category"] == "Factory Fixed Cost"]
                    if not preferred:
                        preferred = [lot for lot in candidates if lot["division"] == posted_division]
                else:
                    preferred = [lot for lot in candidates if lot["division"] == posted_division]
                if not preferred:
                    preferred = candidates

                preferred.sort(
                    key=lambda lot: (
                        lot["accrual_month"].ordinal,
                        -lot["supplier_criticality"],
                        lot["supplier"],
                        lot["division"],
                    )
                )
                lot = preferred[0]
                applied = min(remaining, float(lot["outstanding"]))
                lot["outstanding"] -= applied
                remaining -= applied

        trailing_start = period - 11
        supplier_scope = supplier_spend_monthly[
            (pd.PeriodIndex(supplier_spend_monthly.month, freq="M") >= trailing_start)
            & (pd.PeriodIndex(supplier_spend_monthly.month, freq="M") <= period)
        ]
        supplier_trailing = supplier_scope.groupby("supplier").credit.sum().to_dict()
        total_trailing = float(sum(supplier_trailing.values()))
        ranked_spend = sorted((float(value) for value in supplier_trailing.values()), reverse=True)
        group_top5 = float(sum(ranked_spend[:5]) / total_trailing) if total_trailing else 0.0
        group_supplier_count = int(len(supplier_trailing))

        division_scope = spend_monthly[
            (pd.PeriodIndex(spend_monthly.month, freq="M") >= trailing_start)
            & (pd.PeriodIndex(spend_monthly.month, freq="M") <= period)
        ]
        division_trailing = division_scope.groupby(["division", "supplier"]).credit.sum().to_dict()

        for entity, lots in open_lots.items():
            supplier_rows: dict[tuple[str, str], dict] = {}
            for lot in lots:
                amount = float(lot["outstanding"])
                if amount <= 0.005:
                    continue
                age_days = max((period.ordinal - lot["accrual_month"].ordinal) * 30, 0)
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

                key = (lot["division"], lot["supplier"])
                if key not in supplier_rows:
                    supplier_rows[key] = {
                        "month": month,
                        "entity": entity,
                        "division": lot["division"],
                        "supplier": lot["supplier"],
                        "supplier_name": lot["supplier_name"],
                        "supplier_category": lot["supplier_category"],
                        "supplier_criticality": lot["supplier_criticality"],
                        "single_source": lot["single_source"],
                        "payment_terms_days": lot["terms_days"],
                        **{bucket_name: 0.0 for bucket_name in AP_BUCKETS},
                        "weighted_age_value": 0.0,
                    }
                supplier_rows[key][bucket] += amount
                supplier_rows[key]["weighted_age_value"] += amount * age_days

            for row in supplier_rows.values():
                total = sum(float(row[bucket]) for bucket in AP_BUCKETS)
                overdue = total - float(row["current"])
                supplier_total_spend = float(supplier_trailing.get(row["supplier"], 0.0))
                row["total_ap"] = total
                row["overdue_ap"] = overdue
                row["overdue_pct"] = overdue / total if total else 0.0
                row["weighted_age_days"] = row.pop("weighted_age_value") / total if total else 0.0
                row["trailing_12m_spend"] = float(
                    division_trailing.get((row["division"], row["supplier"]), 0.0)
                )
                row["supplier_spend_share"] = supplier_total_spend / total_trailing if total_trailing else 0.0
                row["group_top5_spend_concentration"] = group_top5
                row["group_supplier_count_trailing12"] = group_supplier_count
                snapshots.append(row)

    return pd.DataFrame(snapshots)


def ap_aging_summary(ap_aging: pd.DataFrame) -> pd.DataFrame:
    if ap_aging.empty:
        return pd.DataFrame(columns=[
            "month", *AP_BUCKETS, "total_ap", "overdue_ap", "overdue_pct", "weighted_age_days",
            "supplier_count", "trailing_12m_supplier_count", "top5_spend_concentration",
            "single_source_ap", "critical_supplier_ap",
        ])
    rows: list[dict] = []
    for month, group in ap_aging.groupby("month"):
        total = float(group.total_ap.sum())
        overdue = float(group.overdue_ap.sum())
        weighted_age = float((group.total_ap * group.weighted_age_days).sum() / total) if total else 0.0
        rows.append({
            "month": month,
            **{bucket: float(group[bucket].sum()) for bucket in AP_BUCKETS},
            "total_ap": total,
            "overdue_ap": overdue,
            "overdue_pct": overdue / total if total else 0.0,
            "weighted_age_days": weighted_age,
            "supplier_count": int(group.supplier.nunique()),
            "trailing_12m_supplier_count": int(group.group_supplier_count_trailing12.max()),
            "top5_spend_concentration": float(group.group_top5_spend_concentration.max()),
            "single_source_ap": float(group.loc[group.single_source.astype(bool), "total_ap"].sum()),
            "critical_supplier_ap": float(group.loc[group.supplier_criticality.ge(4), "total_ap"].sum()),
        })
    return pd.DataFrame(rows)


def supplier_concentration(ap_aging: pd.DataFrame, end_month: str) -> pd.DataFrame:
    if ap_aging.empty:
        return pd.DataFrame()
    latest = ap_aging[ap_aging.month.eq(end_month)].copy()
    if latest.empty:
        return pd.DataFrame()
    out = latest.groupby(
        ["entity", "division", "supplier", "supplier_name", "supplier_category",
         "supplier_criticality", "single_source"],
        as_index=False,
    ).agg(
        total_ap=("total_ap", "sum"),
        overdue_ap=("overdue_ap", "sum"),
        trailing_12m_spend=("trailing_12m_spend", "max"),
        supplier_spend_share=("supplier_spend_share", "max"),
        weighted_age_days=("weighted_age_days", "mean"),
    )
    out["risk_flag"] = np.select(
        [
            out.single_source.astype(bool) & out.supplier_criticality.ge(4),
            out.supplier_spend_share.ge(0.10),
            out.overdue_ap.gt(0),
        ],
        ["Single-source critical", "High concentration", "Payment overdue"],
        default="Normal",
    )
    return out.sort_values(["supplier_spend_share", "total_ap"], ascending=False)


def supplier_master(ap_aging: pd.DataFrame) -> pd.DataFrame:
    if ap_aging.empty:
        return pd.DataFrame()
    columns = ["supplier", "supplier_name", "supplier_category", "supplier_criticality", "single_source"]
    return ap_aging[columns].drop_duplicates("supplier").sort_values("supplier").reset_index(drop=True)


def validate_ap_aging(journal: pd.DataFrame, ap_aging: pd.DataFrame) -> dict:
    gl = _ap_gl_balance(journal)
    if ap_aging.empty:
        schedule = pd.DataFrame(columns=["month", "entity", "schedule_ap"])
        bucket_gap = 0.0
        concentration_out_of_range = 0
    else:
        schedule = ap_aging.groupby(["month", "entity"], as_index=False).total_ap.sum().rename(
            columns={"total_ap": "schedule_ap"}
        )
        bucket_gap = float((ap_aging[AP_BUCKETS].sum(axis=1) - ap_aging.total_ap).abs().max())
        concentration_out_of_range = int((
            (ap_aging.group_top5_spend_concentration < -1e-9)
            | (ap_aging.group_top5_spend_concentration > 1.0 + 1e-9)
        ).sum())
    recon = gl.merge(schedule, on=["month", "entity"], how="outer").fillna(0.0)
    gap = float((recon.gl_ap - recon.schedule_ap).abs().max()) if not recon.empty else 0.0
    negative_count = int((ap_aging.total_ap < -0.005).sum()) if not ap_aging.empty else 0
    checks = {
        "ap_subledger_max_gap": round(gap, 2),
        "ap_aging_bucket_max_gap": round(bucket_gap, 2),
        "ap_negative_supplier_balances": negative_count,
        "supplier_concentration_out_of_range": concentration_out_of_range,
    }
    checks["passed"] = (
        gap <= 0.05
        and bucket_gap <= 0.05
        and negative_count == 0
        and concentration_out_of_range == 0
    )
    return checks
