"""Invoice-grain view of the published, risk-aware AR allocation policy.

Cash journal entries are entity/division totals, not bank-matched customer
receipts. Applications generated here are analytical allocations of those
posted totals to invoice IDs; they never create or modify accounting entries.
"""
from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd

from .customer_receivables_v10 import validate_contract_ar
from .working_capital_detail import AR_BUCKETS, _payment_terms, _stable_customer_risk


APPLICATION_COLUMNS = [
    "application_month", "entity", "division", "customer", "invoice_id",
    "source_journal_id", "allocation_type", "applied_amount", "allocation_basis",
]


def build_ar_invoice_lineage(
    journal: pd.DataFrame,
    customers: pd.DataFrame,
    config: dict,
    end_month: str,
    customer_aging: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Rebuild customer-month AR aging at source invoice grain and reconcile it.

    Cash is applied by the same risk-aware oldest-receivable priority used by
    ``build_ar_aging_with_contracts``. Within a customer/month tie, invoice IDs
    are sorted stably. Customer advances follow oldest-invoice order. These are
    modeled allocations of aggregate posted credits, not actual remittance
    advice or bank-matched settlements.
    """
    required = {
        "month", "entity", "division", "account", "journal_id", "journal_type",
        "debit", "credit", "customer", "product",
    }
    missing = required - set(journal.columns)
    if missing:
        raise ValueError(f"Missing AR invoice lineage fields: {sorted(missing)}")
    if not np.isfinite(journal[["debit", "credit"]].to_numpy(dtype=float)).all():
        raise ValueError("Non-finite AR invoice lineage amount")

    ar = journal.loc[journal.account.eq("1100_AR") & journal.month.le(end_month)].copy()
    sales = ar.loc[ar.journal_type.eq("sale") & ar.debit.gt(0)].copy()
    credit_rows = ar.loc[
        ar.journal_type.isin(["collection", "contract_liability_application"])
        & ar.credit.gt(0)
    ]
    existing_controls = validate_contract_ar(journal, customer_aging)
    if sales.empty:
        empty = pd.DataFrame()
        source_ids_missing = credit_rows.journal_id.isna().any() or credit_rows.journal_id.astype(str).str.strip().eq("").any()
        return empty, pd.DataFrame(columns=APPLICATION_COLUMNS), {
            "ar_invoice_aging_max_gap": 0.0,
            "ar_invoice_application_max_gap": round(float(credit_rows.credit.sum()), 2),
            "ar_invoice_unallocated_credit": 0.0,
            "passed": bool(existing_controls["passed"] and customer_aging.empty and credit_rows.empty and not source_ids_missing),
        }
    if (
        sales.journal_id.isna().any()
        or sales.journal_id.astype(str).str.strip().eq("").any()
        or sales.journal_id.astype(str).duplicated().any()
    ):
        raise ValueError("AR sale rows must have unique, non-empty invoice journal IDs")
    if sales[["month", "entity", "division", "customer", "product"]].isna().any().any():
        raise ValueError("AR invoice is missing month, scope, customer or product identity")

    customer_required = {"customer", "customer_name", "segment", "customer_size"}
    if customer_required - set(customers.columns):
        raise ValueError(f"Missing customer master fields: {sorted(customer_required - set(customers.columns))}")
    customer_meta = (
        customers[["customer", "customer_name", "segment", "customer_size"]]
        .drop_duplicates("customer").set_index("customer").to_dict("index")
    )

    if credit_rows.journal_id.isna().any() or credit_rows.journal_id.astype(str).str.strip().eq("").any():
        raise ValueError("AR credit rows must retain non-empty source journal IDs")
    if (
        credit_rows["journal_type"].eq("contract_liability_application")
        & credit_rows.customer.isna()
    ).any():
        raise ValueError("Customer advance application is missing customer identity")
    months = sorted(set(sales.month.astype(str)) | set(credit_rows.month.astype(str)) | {str(end_month)})
    open_lots: dict[tuple[str, str], list[dict]] = defaultdict(list)
    snapshots: list[dict] = []
    applications: list[dict] = []
    unallocated_credit = 0.0

    def apply_to_invoices(
        *, month: str, entity: str, division: str, customer: str | None,
        source_id: str, amount: float, kind: str, period: pd.Period,
    ) -> float:
        nonlocal unallocated_credit
        key = (entity, division)
        remaining = float(amount)
        candidates = [
            lot for lot in open_lots[key]
            if lot["outstanding"] > 0.005 and (customer is None or lot["customer"] == customer)
        ]
        if kind == "cash_collection":
            candidates.sort(key=lambda lot: lot["invoice_id"])
            candidates.sort(key=lambda lot: (
                (period.ordinal - lot["invoice_month"].ordinal) * 30
                - lot["risk_score"] * 12.0
                - lot["terms_days"] * 0.15,
                -lot["risk_score"],
                lot["customer"],
            ), reverse=True)
        else:
            candidates.sort(key=lambda lot: (lot["invoice_month"].ordinal, lot["invoice_id"]))
        for lot in candidates:
            if remaining <= 0.005:
                break
            applied = min(remaining, float(lot["outstanding"]))
            lot["outstanding"] -= applied
            if kind == "cash_collection":
                lot["cash_applied"] += applied
            else:
                lot["advance_applied"] += applied
            applications.append({
                "application_month": month,
                "entity": entity,
                "division": division,
                "customer": lot["customer"],
                "invoice_id": lot["invoice_id"],
                "source_journal_id": source_id,
                "allocation_type": kind,
                "applied_amount": round(applied, 2),
                "allocation_basis": (
                    "Modeled risk-aware oldest receivable; posted entity/division collection total"
                    if kind == "cash_collection"
                    else "Modeled oldest open customer invoice; posted customer advance application"
                ),
            })
            remaining -= applied
        if remaining > 0.02:
            raise RuntimeError(
                f"AR credit exceeds modeled open invoices for {month} {entity}/{division} "
                f"{customer or 'group'} {source_id}: {remaining:.2f}"
            )
        if remaining > 0.005:
            unallocated_credit += remaining
            applications.append({
                "application_month": month,
                "entity": entity,
                "division": division,
                "customer": customer or "",
                "invoice_id": "",
                "source_journal_id": source_id,
                "allocation_type": f"{kind}_unallocated_tolerance",
                "applied_amount": round(remaining, 2),
                "allocation_basis": "Unallocated residual within legacy EUR 0.02 allocation tolerance",
            })
        return remaining

    for month in months:
        period = pd.Period(month, freq="M")
        month_sales = sales.loc[sales.month.astype(str).eq(month)].sort_values(
            ["entity", "division", "customer", "journal_id"], kind="stable"
        )
        for row in month_sales.itertuples(index=False):
            customer = str(row.customer)
            info = customer_meta.get(customer, {})
            segment = str(info.get("segment", "Core"))
            terms = _payment_terms(config, str(row.division))
            open_lots[(str(row.entity), str(row.division))].append({
                "invoice_id": str(row.journal_id),
                "invoice_month": period,
                "month": month,
                "entity": str(row.entity),
                "division": str(row.division),
                "customer": customer,
                "customer_name": str(info.get("customer_name", customer)),
                "customer_segment": segment,
                "risk_score": _stable_customer_risk(customer, segment, float(info.get("customer_size", 1.0))),
                "product": str(row.product),
                "invoice_amount": float(row.debit),
                "outstanding": float(row.debit),
                "cash_applied": 0.0,
                "advance_applied": 0.0,
                "terms_days": terms,
            })

        month_apps = ar.loc[
            ar.month.astype(str).eq(month)
            & ar.journal_type.eq("contract_liability_application")
            & ar.credit.gt(0)
        ]
        if not month_apps.empty:
            app_groups = month_apps.groupby(["entity", "division", "customer"], as_index=False).agg(
                credit=("credit", "sum"), source_ids=("journal_id", lambda values: tuple(sorted(set(map(str, values)))))
            )
            for row in app_groups.itertuples(index=False):
                remaining = float(row.credit)
                ids = list(row.source_ids) or ["UNIDENTIFIED-ADVANCE-APPLICATION"]
                for source_id in ids:
                    if remaining <= 0.005:
                        break
                    source_amount = float(month_apps.loc[
                        month_apps.entity.eq(row.entity)
                        & month_apps.division.eq(row.division)
                        & month_apps.customer.eq(row.customer)
                        & month_apps.journal_id.astype(str).eq(source_id), "credit"
                    ].sum())
                    apply_to_invoices(
                        month=month, entity=str(row.entity), division=str(row.division),
                        customer=str(row.customer), source_id=source_id,
                        amount=min(source_amount, remaining), kind="customer_advance_application", period=period,
                    )
                    remaining -= min(source_amount, remaining)
                if remaining > 0.02:
                    raise RuntimeError(f"Customer advance allocation failed for {month} {row.customer}: {remaining:.2f}")

        month_cash = ar.loc[
            ar.month.astype(str).eq(month) & ar.journal_type.eq("collection") & ar.credit.gt(0)
        ]
        if not month_cash.empty:
            cash_groups = month_cash.groupby(["entity", "division"], as_index=False).agg(
                credit=("credit", "sum"), source_ids=("journal_id", lambda values: tuple(sorted(set(map(str, values)))))
            )
            for row in cash_groups.itertuples(index=False):
                remaining = float(row.credit)
                ids = list(row.source_ids) or ["UNIDENTIFIED-COLLECTION"]
                for source_id in ids:
                    if remaining <= 0.005:
                        break
                    source_amount = float(month_cash.loc[
                        month_cash.entity.eq(row.entity)
                        & month_cash.division.eq(row.division)
                        & month_cash.journal_id.astype(str).eq(source_id), "credit"
                    ].sum())
                    allocation = min(source_amount, remaining)
                    apply_to_invoices(
                        month=month, entity=str(row.entity), division=str(row.division),
                        customer=None, source_id=source_id, amount=allocation,
                        kind="cash_collection", period=period,
                    )
                    remaining -= allocation
                if remaining > 0.02:
                    raise RuntimeError(f"Collection allocation failed for {month} {row.entity}/{row.division}: {remaining:.2f}")

        for lots in open_lots.values():
            for lot in lots:
                amount = float(lot["outstanding"])
                if month != end_month or amount <= 0.005:
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
                snapshots.append({
                    "month": month,
                    "entity": lot["entity"],
                    "division": lot["division"],
                    "customer": lot["customer"],
                    "customer_name": lot["customer_name"],
                    "customer_segment": lot["customer_segment"],
                    "product": lot["product"],
                    "invoice_id": lot["invoice_id"],
                    "invoice_month": str(lot["invoice_month"]),
                    "invoice_amount": round(float(lot["invoice_amount"]), 2),
                    "cash_applied_ltd": round(float(lot["cash_applied"]), 2),
                    "advance_applied_ltd": round(float(lot["advance_applied"]), 2),
                    "open_amount": round(amount, 2),
                    "payment_terms_days": int(lot["terms_days"]),
                    "invoice_age_days": int(age_days),
                    "overdue_days": max(int(overdue_days), 0),
                    "aging_bucket": bucket,
                    "risk_score": round(float(lot["risk_score"]), 2),
                    "evidence_basis": "Synthetic invoice source ID; modeled allocation of posted AR credits, not bank matched",
                })

    invoice_aging = pd.DataFrame(snapshots)
    application_detail = pd.DataFrame(applications, columns=APPLICATION_COLUMNS)
    if not application_detail.empty:
        application_detail = application_detail.sort_values(
            ["application_month", "entity", "division", "source_journal_id", "invoice_id"], kind="stable"
        ).reset_index(drop=True)

    aging_gap = 0.0
    if not customer_aging.empty:
        expected = customer_aging.loc[customer_aging.month.eq(end_month)].groupby(
            ["entity", "division", "customer"], as_index=False
        )[AR_BUCKETS].sum()
        actual = (
            invoice_aging.groupby(["entity", "division", "customer", "aging_bucket"], as_index=False).open_amount.sum()
            .pivot_table(index=["entity", "division", "customer"], columns="aging_bucket", values="open_amount", fill_value=0.0)
            .reset_index()
        ) if not invoice_aging.empty else pd.DataFrame(columns=["entity", "division", "customer"])
        for bucket in AR_BUCKETS:
            if bucket not in actual:
                actual[bucket] = 0.0
        expected = expected[["entity", "division", "customer", *AR_BUCKETS]].rename(columns={b: f"expected_{b}" for b in AR_BUCKETS})
        actual = actual[["entity", "division", "customer", *AR_BUCKETS]].rename(columns={b: f"actual_{b}" for b in AR_BUCKETS})
        recon = expected.merge(actual, on=["entity", "division", "customer"], how="outer").fillna(0.0)
        gaps = [float((recon[f"expected_{b}"] - recon[f"actual_{b}"]).abs().max()) for b in AR_BUCKETS]
        aging_gap = max(gaps, default=0.0)

    invoice_total = float(invoice_aging.open_amount.sum()) if not invoice_aging.empty else 0.0
    aging_total = float(customer_aging.loc[customer_aging.month.eq(end_month), "total_ar"].sum()) if not customer_aging.empty else 0.0
    total_gap = abs(invoice_total - aging_total)
    allocated = application_detail.loc[
        ~application_detail.allocation_type.str.endswith("_unallocated_tolerance")
    ] if not application_detail.empty else application_detail
    source_credit = credit_rows.groupby(["month", "journal_id"], as_index=False).credit.sum()
    applied_by_source = allocated.groupby(["application_month", "source_journal_id"], as_index=False).applied_amount.sum()
    expected_source = source_credit.rename(columns={"month": "application_month", "journal_id": "source_journal_id", "credit": "source_credit"})
    source_recon = expected_source.merge(applied_by_source, on=["application_month", "source_journal_id"], how="outer").fillna(0.0)
    application_gap = float((source_recon.source_credit - source_recon.applied_amount).abs().max()) if not source_recon.empty else 0.0

    checks = {
        "ar_invoice_aging_max_gap": round(max(aging_gap, total_gap), 2),
        "ar_invoice_application_max_gap": round(application_gap, 2),
        "ar_invoice_unallocated_credit": round(unallocated_credit, 2),
        "ar_invoice_rows": int(len(invoice_aging)),
        "ar_invoice_application_rows": int(len(application_detail)),
    }
    checks["passed"] = bool(
        existing_controls["passed"] and aging_gap <= 0.05 and total_gap <= 0.05
        and application_gap <= 0.05 and unallocated_credit <= 0.02
    )
    return invoice_aging, application_detail, checks
