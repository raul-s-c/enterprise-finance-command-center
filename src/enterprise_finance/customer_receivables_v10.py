from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd

from .working_capital_detail import AR_BUCKETS, _ar_gl_balance, _payment_terms, _stable_customer_risk


def build_ar_aging_with_contracts(journal: pd.DataFrame, customers: pd.DataFrame, config: dict) -> pd.DataFrame:
    sales = journal[(journal.account.eq("1100_AR")) & journal.journal_type.eq("sale") & journal.debit.gt(0)].copy()
    cash_collections = journal[(journal.account.eq("1100_AR")) & journal.journal_type.eq("collection") & journal.credit.gt(0)].copy()
    applications = journal[(journal.account.eq("1100_AR")) & journal.journal_type.eq("contract_liability_application") & journal.credit.gt(0)].copy()
    if sales.empty:
        return pd.DataFrame(columns=["month", "entity", "division", "customer", "customer_name", "customer_segment", "risk_score", "payment_terms_days", *AR_BUCKETS, "total_ar", "overdue_ar", "overdue_pct", "weighted_age_days"])

    meta = customers[["customer", "customer_name", "segment", "customer_size"]].drop_duplicates("customer").set_index("customer").to_dict("index")
    months = sorted(set(sales.month.unique()) | set(cash_collections.month.unique()) | set(applications.month.unique()))
    open_lots: dict[tuple[str, str], list[dict]] = defaultdict(list)
    snapshots: list[dict] = []

    sales_agg = sales.groupby(["month", "entity", "division", "customer"], as_index=False).debit.sum()
    cash_agg = cash_collections.groupby(["month", "entity", "division"], as_index=False).credit.sum()
    app_agg = applications.groupby(["month", "entity", "division", "customer"], as_index=False).credit.sum()

    for month in months:
        period = pd.Period(month, freq="M")
        for _, row in sales_agg[sales_agg.month.eq(month)].iterrows():
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

        # Apply customer advances to the intended customer's receivable first.
        for _, row in app_agg[app_agg.month.eq(month)].iterrows():
            key = (str(row.entity), str(row.division))
            customer = str(row.customer)
            remaining = float(row.credit)
            candidates = [lot for lot in open_lots[key] if lot["customer"] == customer and lot["outstanding"] > 0.005]
            candidates.sort(key=lambda lot: lot["invoice_month"].ordinal)
            for lot in candidates:
                if remaining <= 0.005:
                    break
                applied = min(remaining, float(lot["outstanding"]))
                lot["outstanding"] -= applied
                remaining -= applied
            if remaining > 0.02:
                raise RuntimeError(f"Contract application exceeded customer AR for {month} {key} {customer}: {remaining:.2f}")

        # Ordinary cash collections retain the risk-aware oldest-receivable allocation.
        for _, row in cash_agg[cash_agg.month.eq(month)].iterrows():
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
                raise RuntimeError(f"Cash collection exceeded open receivables for {month} {key}: {remaining:.2f}")

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


def validate_contract_ar(journal: pd.DataFrame, ar_aging: pd.DataFrame) -> dict:
    gl = _ar_gl_balance(journal)
    if ar_aging.empty:
        schedule = pd.DataFrame(columns=["month", "entity", "division", "schedule_ar"])
        bucket_gap = 0.0
    else:
        schedule = ar_aging.groupby(["month", "entity", "division"], as_index=False).total_ar.sum().rename(columns={"total_ar": "schedule_ar"})
        bucket_gap = float((ar_aging[AR_BUCKETS].sum(axis=1) - ar_aging.total_ar).abs().max())
    recon = gl.merge(schedule, on=["month", "entity", "division"], how="outer").fillna(0.0)
    gap = float((recon.gl_ar - recon.schedule_ar).abs().max()) if not recon.empty else 0.0
    checks = {
        "contract_ar_subledger_max_gap": round(gap, 2),
        "contract_ar_bucket_max_gap": round(bucket_gap, 2),
    }
    checks["passed"] = gap <= 0.05 and bucket_gap <= 0.05
    return checks
