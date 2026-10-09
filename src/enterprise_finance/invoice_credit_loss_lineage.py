"""Analytical invoice allocation of the posted customer-level ECL policy.

This schedule supports drill-down only. It does not create invoice-level journals
or imply that an invoice-specific allowance was posted to the general ledger.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .provisions import build_credit_loss_schedule
from .working_capital_detail import AR_BUCKETS


EVIDENCE_BASIS = (
    "Analytical allocation of the existing customer-level expected credit-loss policy by invoice aging bucket "
    "and the same customer risk score; not an invoice-specific GL posting."
)


def build_invoice_credit_loss_lineage(
    invoices: pd.DataFrame,
    customer_schedule: pd.DataFrame,
    config: dict,
    end_month: str,
) -> tuple[pd.DataFrame, dict]:
    """Apply the published ECL rates and risk multiplier to each open invoice.

    Invoice-level allowances must tie to the existing customer schedule by
    month/entity/division/customer within EUR 0.05. Any missing customer match,
    duplicate invoice ID, unsupported bucket or non-finite balance fails closed.
    """
    columns = [
        "month", "entity", "division", "customer", "invoice_id", "aging_bucket",
        "open_amount", "risk_score", "risk_multiplier", "credit_loss_allowance",
        "net_ar", "allowance_pct", "evidence_basis",
    ]
    if invoices.empty:
        empty = pd.DataFrame(columns=columns)
        checks = {"ar_invoice_ecl_max_gap": 0.0, "ar_invoice_ecl_unmatched_customers": 0, "ar_invoice_ecl_rows": 0, "passed": customer_schedule.empty}
        return empty, checks

    required = {"month", "entity", "division", "customer", "invoice_id", "aging_bucket", "open_amount", "risk_score"}
    missing = required - set(invoices.columns)
    if missing:
        raise ValueError(f"Missing invoice ECL fields: {sorted(missing)}")
    if invoices.invoice_id.isna().any() or invoices.invoice_id.astype(str).str.strip().eq("").any() or invoices.invoice_id.astype(str).duplicated().any():
        raise ValueError("Invoice ECL requires unique, non-empty invoice IDs")
    if not np.isfinite(invoices[["open_amount", "risk_score"]].to_numpy(dtype=float)).all():
        raise ValueError("Invoice ECL contains non-finite balance or risk values")
    if (invoices.open_amount.astype(float) < -0.005).any():
        raise ValueError("Invoice ECL cannot include negative open AR")
    unsupported = set(invoices.aging_bucket.dropna().astype(str)) - set(AR_BUCKETS)
    if unsupported:
        raise ValueError(f"Unsupported invoice ECL aging buckets: {sorted(unsupported)}")
    if invoices.aging_bucket.isna().any() or invoices[["month", "entity", "division", "customer"]].isna().any().any():
        raise ValueError("Invoice ECL is missing period or customer scope")

    current = invoices.loc[invoices.month.astype(str).eq(str(end_month))].copy()
    keys = ["month", "entity", "division", "customer"]
    policy = customer_schedule.loc[customer_schedule.month.astype(str).eq(str(end_month)), [*keys, "risk_score"]].copy() if not customer_schedule.empty else pd.DataFrame(columns=[*keys, "risk_score"])
    if not policy.empty and policy.duplicated(keys).any():
        raise ValueError("Customer ECL schedule has duplicate policy rows")
    if not policy.empty:
        current = current.merge(policy.rename(columns={"risk_score": "_policy_risk_score"}), on=keys, how="left", validate="many_to_one")
        current["risk_score"] = current["_policy_risk_score"].fillna(current["risk_score"])
        current = current.drop(columns="_policy_risk_score")
    current["total_ar"] = current.open_amount.astype(float).clip(lower=0.0)
    for bucket in AR_BUCKETS:
        current[bucket] = np.where(current.aging_bucket.eq(bucket), current.total_ar, 0.0)
    ecl = build_credit_loss_schedule(current, config)
    ecl["open_amount"] = ecl.gross_ar
    ecl["net_ar"] = ecl.gross_ar - ecl.credit_loss_allowance
    ecl["evidence_basis"] = EVIDENCE_BASIS

    analytical = ecl.groupby(keys, as_index=False).agg(
        analytical_gross=("open_amount", "sum"), analytical_ecl=("credit_loss_allowance", "sum"),
        analytical_net=("net_ar", "sum"),
    )
    existing = customer_schedule.loc[customer_schedule.month.astype(str).eq(str(end_month))].copy() if not customer_schedule.empty else customer_schedule.copy()
    if not existing.empty:
        existing = existing.groupby(keys, as_index=False).agg(
            posted_schedule_gross=("gross_ar", "sum"), posted_schedule_ecl=("credit_loss_allowance", "sum"),
            posted_schedule_net=("net_ar", "sum"),
        )
    else:
        existing = pd.DataFrame(columns=[*keys, "posted_schedule_gross", "posted_schedule_ecl", "posted_schedule_net"])
    recon = analytical.merge(existing, on=keys, how="outer", indicator=True).fillna(0.0)
    gaps = []
    for actual, expected in [
        ("analytical_gross", "posted_schedule_gross"),
        ("analytical_ecl", "posted_schedule_ecl"),
        ("analytical_net", "posted_schedule_net"),
    ]:
        gaps.append(float((recon[actual] - recon[expected]).abs().max()) if not recon.empty else 0.0)
    unmatched = int((recon["_merge"] != "both").sum()) if not recon.empty else 0
    max_gap = max(gaps, default=0.0)
    result = ecl[columns].sort_values(["entity", "division", "customer", "invoice_id"], kind="stable").reset_index(drop=True)
    checks = {
        "ar_invoice_ecl_max_gap": round(max_gap, 2),
        "ar_invoice_ecl_unmatched_customers": unmatched,
        "ar_invoice_ecl_rows": int(len(result)),
        "passed": bool(max_gap <= 0.05 and unmatched == 0),
    }
    return result, checks
