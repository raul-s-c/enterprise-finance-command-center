"""Source-accrual-grain view of the published supplier payable schedule.

Accrual journal IDs are not supplier invoice numbers. Reductions are posted at
entity/division or journal-type grain and are allocated analytically to those
source accruals with the same priority as the existing supplier aging policy.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .supplier_payables import (
    AP_BUCKETS,
    _supplier_for_row,
    _terms_days,
    validate_ap_aging,
)


APPLICATION_COLUMNS = [
    "application_month", "entity", "posted_division", "supplier", "supplier_name",
    "accrual_journal_id", "reduction_journal_id", "reduction_type", "applied_amount",
    "allocation_basis",
]


def build_ap_item_lineage(
    journal: pd.DataFrame,
    config: dict,
    end_month: str,
    supplier_aging: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Reconstruct closing AP by source accrual journal and reconcile it.

    Aggregate AP reductions follow the existing policy: factory absorption
    variance reductions first; otherwise prefer the posted division, fall back
    to the legal entity; apply to the oldest accrual, then supplier criticality,
    supplier ID and division. Within a supplier/month tie, source journal IDs
    are sorted lexically. This is an analytical allocation, not vendor-remittance
    or invoice-level settlement evidence.
    """
    end_month = str(end_month)
    required = {
        "month", "entity", "division", "account", "journal_id", "journal_type",
        "debit", "credit", "product", "customer",
    }
    missing = required - set(journal.columns)
    if missing:
        raise ValueError(f"Missing AP source-item fields: {sorted(missing)}")
    if not pd.notna(journal[["debit", "credit"]]).all().all():
        raise ValueError("Missing AP source-item amount")
    if not np.isfinite(journal[["debit", "credit"]].to_numpy(dtype=float)).all():
        raise ValueError("Non-finite AP source-item amount")

    ap = journal.loc[journal.account.eq("2100_AP") & journal.month.le(end_month)].copy()
    accruals = ap.loc[ap.credit.gt(0.005)].copy()
    reductions = ap.loc[ap.debit.gt(0.005)].copy()
    controls = validate_ap_aging(journal, supplier_aging)

    def valid_ids(frame: pd.DataFrame) -> bool:
        return bool(
            not frame.journal_id.isna().any()
            and not frame.journal_id.astype(str).str.strip().eq("").any()
            and frame.journal_id.astype(str).is_unique
        )

    if accruals.empty:
        empty_items = pd.DataFrame()
        empty_apps = pd.DataFrame(columns=APPLICATION_COLUMNS)
        residual = float(reductions.debit.sum())
        return empty_items, empty_apps, {
            "ap_item_aging_max_gap": 0.0,
            "ap_item_application_max_gap": round(residual, 2),
            "ap_item_unallocated_reduction": round(residual, 2),
            "ap_item_rows": 0,
            "ap_item_application_rows": 0,
            "passed": bool(controls["passed"] and supplier_aging.empty and reductions.empty),
        }

    if not valid_ids(accruals):
        raise ValueError("AP accrual source rows must have unique, non-empty journal IDs")
    if not valid_ids(reductions):
        raise ValueError("AP reduction source rows must have unique, non-empty journal IDs")
    if accruals[["month", "entity", "division", "journal_type"]].isna().any().any():
        raise ValueError("AP accrual source row is missing period or scope")
    if reductions[["month", "entity", "division", "journal_type"]].isna().any().any():
        raise ValueError("AP reduction source row is missing period or scope")

    supplier_metadata = accruals.apply(_supplier_for_row, axis=1, result_type="expand")
    accruals = pd.concat([accruals.reset_index(drop=True), supplier_metadata.reset_index(drop=True)], axis=1)
    accruals["terms_days"] = [
        _terms_days(config, str(division), str(category))
        for division, category in zip(accruals.division, accruals.supplier_category)
    ]
    months = sorted(set(accruals.month.astype(str)) | set(reductions.month.astype(str)) | {str(end_month)})
    open_items: dict[str, list[dict]] = {}
    applications: list[dict] = []
    unallocated_reduction = 0.0

    reduction_rows = reductions.groupby(
        ["month", "entity", "division", "journal_type", "journal_id"], as_index=False
    ).debit.sum()
    reduction_groups = reductions.groupby(
        ["month", "entity", "division", "journal_type"], as_index=False
    ).debit.sum()

    def apply_reduction(month: str, entity: str, posted_division: str, reduction_type: str,
                        reduction_id: str, amount: float, period: pd.Period) -> None:
        nonlocal unallocated_reduction
        remaining = float(amount)
        items = open_items.setdefault(entity, [])
        while remaining > 0.005:
            candidates = [item for item in items if item["open_amount"] > 0.005]
            if not candidates:
                raise RuntimeError(
                    f"AP reduction exceeds modeled open accruals for {month} {entity} "
                    f"{reduction_type} {reduction_id}: {remaining:.2f}"
                )
            if reduction_type == "factory_absorption_variance":
                preferred = [item for item in candidates if item["supplier_category"] == "Factory Fixed Cost"]
                if not preferred:
                    preferred = [item for item in candidates if item["division"] == posted_division]
            else:
                preferred = [item for item in candidates if item["division"] == posted_division]
            if not preferred:
                preferred = candidates
            preferred.sort(key=lambda item: (
                item["accrual_month"].ordinal,
                -item["supplier_criticality"],
                item["supplier"],
                item["division"],
                item["accrual_journal_id"],
            ))
            item = preferred[0]
            applied = min(remaining, float(item["open_amount"]))
            item["open_amount"] -= applied
            item["reductions_applied_ltd"] += applied
            applications.append({
                "application_month": month,
                "entity": entity,
                "posted_division": posted_division,
                "supplier": item["supplier"],
                "supplier_name": item["supplier_name"],
                "accrual_journal_id": item["accrual_journal_id"],
                "reduction_journal_id": reduction_id,
                "reduction_type": reduction_type,
                "applied_amount": round(applied, 2),
                "allocation_basis": (
                    "Modeled allocation of an aggregate entity/division reduction; "
                    "oldest accrual and supplier criticality, not vendor remittance"
                ),
            })
            remaining -= applied
        if remaining > 0.02:
            raise RuntimeError(f"AP reduction allocation residual {remaining:.2f} for {reduction_id}")
        if remaining > 0.005:
            unallocated_reduction += remaining

    for month in months:
        period = pd.Period(month, freq="M")
        month_accruals = accruals.loc[accruals.month.astype(str).eq(month)].sort_values(
            ["entity", "division", "supplier", "journal_id"], kind="stable"
        )
        for row in month_accruals.itertuples(index=False):
            item = {
                "accrual_journal_id": str(row.journal_id),
                "accrual_month": period,
                "entity": str(row.entity),
                "division": str(row.division),
                "supplier": str(row.supplier),
                "supplier_name": str(row.supplier_name),
                "supplier_category": str(row.supplier_category),
                "supplier_criticality": int(row.supplier_criticality),
                "single_source": bool(row.single_source),
                "accrual_type": str(row.journal_type),
                "accrual_amount": float(row.credit),
                "open_amount": float(row.credit),
                "reductions_applied_ltd": 0.0,
                "terms_days": int(row.terms_days),
            }
            open_items.setdefault(str(row.entity), []).append(item)
        month_groups = reduction_groups.loc[reduction_groups.month.astype(str).eq(month)].copy()
        if month_groups.empty:
            continue
        month_groups["priority"] = month_groups.journal_type.eq("factory_absorption_variance").map({True: 0, False: 1})
        month_groups = month_groups.sort_values(["priority", "entity", "division"], kind="stable")
        for group in month_groups.itertuples(index=False):
            sources = reduction_rows.loc[
                reduction_rows.month.astype(str).eq(month)
                & reduction_rows.entity.eq(group.entity)
                & reduction_rows.division.eq(group.division)
                & reduction_rows.journal_type.eq(group.journal_type)
            ].sort_values("journal_id", kind="stable")
            group_remaining = float(group.debit)
            for source in sources.itertuples(index=False):
                if group_remaining <= 0.005:
                    break
                source_amount = min(float(source.debit), group_remaining)
                apply_reduction(
                    month, str(group.entity), str(group.division), str(group.journal_type),
                    str(source.journal_id), source_amount, period,
                )
                group_remaining -= source_amount
            if group_remaining > 0.02:
                raise RuntimeError(
                    f"AP reduction source allocation failed for {month} {group.entity}/{group.division}: "
                    f"{group_remaining:.2f}"
                )

    item_rows: list[dict] = []
    closing_period = pd.Period(end_month, freq="M")
    for items in open_items.values():
        for item in items:
            amount = float(item["open_amount"])
            if amount <= 0.005:
                continue
            age_days = max((closing_period.ordinal - item["accrual_month"].ordinal) * 30, 0)
            overdue_days = age_days - item["terms_days"]
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
            item_rows.append({
                "month": end_month,
                "entity": item["entity"],
                "division": item["division"],
                "supplier": item["supplier"],
                "supplier_name": item["supplier_name"],
                "supplier_category": item["supplier_category"],
                "supplier_criticality": item["supplier_criticality"],
                "single_source": item["single_source"],
                "source_item_id": item["accrual_journal_id"],
                "accrual_journal_id": item["accrual_journal_id"],
                "accrual_type": item["accrual_type"],
                "accrual_month": str(item["accrual_month"]),
                "accrual_amount": round(item["accrual_amount"], 2),
                "reductions_applied_ltd": round(item["reductions_applied_ltd"], 2),
                "open_amount": round(amount, 2),
                "payment_terms_days": item["terms_days"],
                "age_days": int(age_days),
                "overdue_days": max(int(overdue_days), 0),
                "aging_bucket": bucket,
                "evidence_basis": (
                    "Synthetic source accrual journal ID; reductions modeled from aggregate AP postings, "
                    "not supplier invoice or remittance evidence"
                ),
            })

    item_aging = pd.DataFrame(item_rows)
    application_detail = pd.DataFrame(applications, columns=APPLICATION_COLUMNS)
    if not application_detail.empty:
        application_detail = application_detail.sort_values(
            ["application_month", "entity", "reduction_journal_id", "accrual_journal_id"], kind="stable"
        ).reset_index(drop=True)

    expected = supplier_aging.loc[supplier_aging.month.eq(end_month)].groupby(
        ["entity", "division", "supplier"], as_index=False
    )[AP_BUCKETS].sum() if not supplier_aging.empty else pd.DataFrame(columns=["entity", "division", "supplier", *AP_BUCKETS])
    if not item_aging.empty:
        actual = item_aging.pivot_table(
            index=["entity", "division", "supplier"], columns="aging_bucket",
            values="open_amount", aggfunc="sum", fill_value=0.0,
        ).reset_index()
    else:
        actual = pd.DataFrame(columns=["entity", "division", "supplier", *AP_BUCKETS])
    for bucket in AP_BUCKETS:
        if bucket not in actual:
            actual[bucket] = 0.0
    expected = expected.rename(columns={bucket: f"expected_{bucket}" for bucket in AP_BUCKETS})
    actual = actual[["entity", "division", "supplier", *AP_BUCKETS]].rename(
        columns={bucket: f"actual_{bucket}" for bucket in AP_BUCKETS}
    )
    recon = expected.merge(actual, on=["entity", "division", "supplier"], how="outer").fillna(0.0)
    bucket_gap = max(
        (float((recon[f"expected_{bucket}"] - recon[f"actual_{bucket}"]).abs().max()) for bucket in AP_BUCKETS),
        default=0.0,
    )
    item_total = float(item_aging.open_amount.sum()) if not item_aging.empty else 0.0
    supplier_total = float(supplier_aging.loc[supplier_aging.month.eq(end_month), "total_ap"].sum()) if not supplier_aging.empty else 0.0
    aging_gap = max(bucket_gap, abs(item_total - supplier_total))

    reduction_sources = reductions.groupby(["month", "journal_id"], as_index=False).debit.sum()
    applied_sources = application_detail.groupby(
        ["application_month", "reduction_journal_id"], as_index=False
    ).applied_amount.sum() if not application_detail.empty else pd.DataFrame(columns=["application_month", "reduction_journal_id", "applied_amount"])
    source_recon = reduction_sources.rename(columns={
        "month": "application_month", "journal_id": "reduction_journal_id", "debit": "source_debit",
    }).merge(applied_sources, on=["application_month", "reduction_journal_id"], how="outer").fillna(0.0)
    application_gap = float((source_recon.source_debit - source_recon.applied_amount).abs().max()) if not source_recon.empty else 0.0
    checks = {
        "ap_item_aging_max_gap": round(aging_gap, 2),
        "ap_item_application_max_gap": round(application_gap, 2),
        "ap_item_unallocated_reduction": round(unallocated_reduction, 2),
        "ap_item_rows": int(len(item_aging)),
        "ap_item_application_rows": int(len(application_detail)),
        "passed": bool(
            controls["passed"] and bucket_gap <= 0.05 and abs(item_total - supplier_total) <= 0.05
            and application_gap <= 0.05 and unallocated_reduction <= 0.05
        ),
    }
    return item_aging, application_detail, checks
