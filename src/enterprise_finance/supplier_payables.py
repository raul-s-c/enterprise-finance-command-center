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
    single_source_seed = _stable_bucket(f"single|{supplier}", 100)
    single_source = bool(criticality >= 4 and single_source_seed < 16)
    return {
        "supplier": supplier,
        "supplier_name": supplier_name,
        "supplier_category": category,
        "supplier_criticality": criticality,
        "single_source": single_source,
    }


def _terms_days(config: dict, division: str, category: str) -> int:
    policy = config.get("supplier_management", {})
    category_terms = policy.get("payment_terms_days", {})
    if category in category_terms:
        return int(category_terms[category])
    division_dpo = config.get("divisions", {}).get(division, {}).get("dpo", 45)
    return int(round(float(division_dpo)))


def _ap_gl_balance(journal: pd.DataFrame) -> pd.DataFrame:
    ap = journal[journal.account.eq("2100_AP")].copy()
    if ap.empty:
        return pd.DataFrame(columns=["month", "entity", "division", "gl_ap"])
    ap["movement"] = ap.credit - ap.debit
    monthly = ap.groupby(["month", "entity", "division"], as_index=False).movement.sum()
    months = sorted(monthly.month.unique())
    keys = [tuple(x) for x in monthly[["entity", "division"]].drop_duplicates().itertuples(index=False, name=None)]
    running: dict[tuple[str, str], float] = defaultdict(float)
    rows: list[dict] = []
    for month in months:
        scope = monthly[monthly.month.eq(month)]
        for _, r in scope.iterrows():
            running[(str(r.entity), str(r.division))] += float(r.movement)
        for entity, division in keys:
            value = running[(str(entity), str(division))]
            if abs(value) > 0.005:
                rows.append({"month": month, "entity": str(entity), "division": str(division), "gl_ap": value})
    return pd.DataFrame(rows)


def build_ap_aging(journal: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Reconstruct supplier-level open AP lots from the legal ledger."""
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
        _terms_days(config, str(d), str(c))
        for d, c in zip(accruals.division, accruals.supplier_category)
    ]

    accrual_monthly = accruals.groupby(
        ["month", "entity", "division", "supplier", "supplier_name", "supplier_category", "supplier_criticality", "single_source", "terms_days"],
        as_index=False,
    ).credit.sum()
    spend_monthly = accrual_monthly.groupby(["month", "supplier"], as_index=False).credit.sum()

    reduction_monthly = reductions.groupby(["month", "entity", "division", "journal_type"], as_index=False).debit.sum()
    months = sorted(set(accrual_monthly.month.unique()) | set(reduction_monthly.month.unique()))
    open_lots: dict[tuple[str, str], list[dict]] = defaultdict(list)
    snapshots: list[dict] = []

    for month in months:
        period = pd.Period(month, freq="M")
        for _, r in accrual_monthly[accrual_monthly.month.eq(month)].iterrows():
            open_lots[(str(r.entity), str(r.division))].append({
                "supplier": str(r.supplier),
                "supplier_name": str(r.supplier_name),
                "supplier_category": str(r.supplier_category),
                "supplier_criticality": int(r.supplier_criticality),
                "single_source": bool(r.single_source),
                "accrual_month": period,
                "outstanding": float(r.credit),
                "terms_days": int(r.terms_days),
            })

        month_reductions = reduction_monthly[reduction_monthly.month.eq(month)].copy()
        month_reductions["priority"] = month_reductions.journal_type.eq("factory_absorption_variance").map({True: 0, False: 1})
        for _, r in month_reductions.sort_values(["priority", "entity", "division"]).iterrows():
            key = (str(r.entity), str(r.division))
            remaining = float(r.debit)
            lots = open_lots[key]
            while remaining > 0.005:
                candidates = [lot for lot in lots if lot["outstanding"] > 0.005]
                if not candidates:
                    raise RuntimeError(f"AP reduction exceeded open payables for {month} {key}: {remaining:.2f}")
                is_factory_release = str(r.journal_type) == "factory_absorption_variance"
                preferred = [lot for lot in candidates if lot["supplier_category"] == "Factory Fixed Cost"] if is_factory_release else candidates
                if not preferred:
                    preferred = candidates
                preferred.sort(key=lambda lot: (lot["accrual_month"].ordinal, -lot["supplier_criticality"], lot["supplier"]))
                lot = preferred[0]
                applied = min(remaining, float(lot["outstanding"]))
                lot["outstanding"] -= applied
                remaining -= applied

        trailing_start = period - 11
        trailing_scope = spend_monthly[
            (pd.PeriodIndex(spend_monthly.month, freq="M") >= trailing_start)
            & (pd.PeriodIndex(spend_monthly.month, freq="M") <= period)
        ]
        trailing_spend = trailing_scope.groupby("supplier").credit.sum().to_dict()
        total_trailing_spend = float(sum(trailing_spend.values()))
        sorted_spend = sorted((float(v) for v in trailing_spend.values()), reverse=True)
        group_top5 = float(sum(sorted_spend[:5]) / total_trailing_spend) if total_trailing_spend else 0.0
        trailing_supplier_count = int(len(trailing_spend))

        for (entity, division), lots in open_lots.items():
            supplier_rows: dict[str, dict] = {}
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
                supplier = lot["supplier"]
                if supplier not in supplier_rows:
                    supplier_rows[supplier] = {
                        "month": month,
                        "entity": entity,
                        "division": division,
                        "supplier": supplier,
                        "supplier_name": lot["supplier_name"],
                        "supplier_category": lot["supplier_category"],
                        "supplier_criticality": lot["supplier_criticality"],
                        "single_source": lot["single_source"],
                        "payment_terms_days": lot["terms_days"],
                        **{b: 0.0 for b in AP_BUCKETS},
                        "weighted_age_value": 0.0,
                    }
                supplier_rows[supplier][bucket] += amount
                supplier_rows[supplier]["weighted_age_value"] += amount * age_days

            for row in supplier_rows.values():
                total = sum(float(row[b]) for b in AP_BUCKETS)
                overdue = total - float(row["current"])
                spend = float(trailing_spend.get(row["supplier"], 0.0))
                row["total_ap"] = total
                row["overdue_ap"] = overdue
                row["overdue_pct"] = overdue / total if total else 0.0
                row["weighted_age_days"] = row.pop("weighted_age_value") / total if total else 0.0
                row["trailing_12m_spend"] = spend
                row["supplier_spend_share"] = spend / total_trailing_spend if total_trailing_spend else 0.0
                row["group_top5_spend_concentration"] = group_top5
                row["group_supplier_count_trailing12"] = trailing_supplier_count
                snapshots.append(row)

    return pd.DataFrame(snapshots)


def ap_aging_summary(ap_aging: pd.DataFrame) -> pd.DataFrame:
    if ap_aging.empty:
        return pd.DataFrame(columns=[
            "month", *AP_BUCKETS, "total_ap", "overdue_ap", "overdue_pct", "weighted_age_days",
            "supplier_count", "trailing_12m_supplier_count", "top5_spend_concentration", "single_source_ap", "critical_supplier_ap",
        ])
    rows: list[dict] = []
    for month, grp in ap_aging.groupby("month"):
        total = float(grp.total_ap.sum())
        overdue = float(grp.overdue_ap.sum())
        weighted_age = float((grp.total_ap * grp.weighted_age_days).sum() / total) if total else 0.0
        single_source_ap = float(grp.loc[grp.single_source.astype(bool), "total_ap"].sum())
        critical_ap = float(grp.loc[grp.supplier_criticality.ge(4), "total_ap"].sum())
        row = {
            "month": month,
            **{b: float(grp[b].sum()) for b in AP_BUCKETS},
            "total_ap": total,
            "overdue_ap": overdue,
            "overdue_pct": overdue / total if total else 0.0,
            "weighted_age_days": weighted_age,
            "supplier_count": int(grp.supplier.nunique()),
            "trailing_12m_supplier_count": int(grp.group_supplier_count_trailing12.max()),
            "top5_spend_concentration": float(grp.group_top5_spend_concentration.max()),
            "single_source_ap": single_source_ap,
            "critical_supplier_ap": critical_ap,
        }
        rows.append(row)
    return pd.DataFrame(rows)


def supplier_concentration(ap_aging: pd.DataFrame, end_month: str) -> pd.DataFrame:
    if ap_aging.empty:
        return pd.DataFrame()
    latest = ap_aging[ap_aging.month.eq(end_month)].copy()
    if latest.empty:
        return pd.DataFrame()
    out = latest.groupby(
        ["entity", "division", "supplier", "supplier_name", "supplier_category", "supplier_criticality", "single_source"],
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
    cols = ["supplier", "supplier_name", "supplier_category", "supplier_criticality", "single_source"]
    return ap_aging[cols].drop_duplicates("supplier").sort_values("supplier").reset_index(drop=True)


def validate_ap_aging(journal: pd.DataFrame, ap_aging: pd.DataFrame) -> dict:
    gl = _ap_gl_balance(journal)
    if ap_aging.empty:
        schedule = pd.DataFrame(columns=["month", "entity", "division", "schedule_ap"])
        bucket_gap = 0.0
        concentration_out_of_range = 0
    else:
        schedule = ap_aging.groupby(["month", "entity", "division"], as_index=False).total_ap.sum().rename(columns={"total_ap": "schedule_ap"})
        bucket_gap = float((ap_aging[AP_BUCKETS].sum(axis=1) - ap_aging.total_ap).abs().max())
        concentration_out_of_range = int(((ap_aging.group_top5_spend_concentration < -1e-9) | (ap_aging.group_top5_spend_concentration > 1.0 + 1e-9)).sum())
    recon = gl.merge(schedule, on=["month", "entity", "division"], how="outer").fillna(0.0)
    gap = float((recon.gl_ap - recon.schedule_ap).abs().max()) if not recon.empty else 0.0
    negative_count = int((ap_aging.total_ap < -0.005).sum()) if not ap_aging.empty else 0
    checks = {
        "ap_subledger_max_gap": round(gap, 2),
        "ap_aging_bucket_max_gap": round(bucket_gap, 2),
        "ap_negative_supplier_balances": negative_count,
        "supplier_concentration_out_of_range": concentration_out_of_range,
    }
    checks["passed"] = gap <= 0.05 and bucket_gap <= 0.05 and negative_count == 0 and concentration_out_of_range == 0
    return checks
