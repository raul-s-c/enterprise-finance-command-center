from __future__ import annotations

from collections import defaultdict

import pandas as pd

from .contract_liabilities import (
    CONTRACT_LIABILITY_ACCOUNT,
    _journal_row,
    build_contract_commitments,
)


def _cents(value: float) -> float:
    return round(float(value) + 0.0, 2)


def apply_contract_liability_accounting(
    journal_pre_provision: pd.DataFrame,
    operations: pd.DataFrame,
    config: dict,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Replace Software/Events collection mechanics with cent-precise advances.

    The contract subledger uses the same cent precision as the journal. Customer
    advances are applied to the intended service invoice. If the related service
    is still not delivered after the configured contractual grace period, the
    remaining customer advance is refunded instead of remaining indefinitely as
    a stale contract liability.
    """
    journal = journal_pre_provision.copy()
    remove_collection = journal.journal_type.eq("collection") & journal.division.isin(["Software", "Events"])
    base = journal.loc[~remove_collection].copy().reset_index(drop=True)

    commitments = build_contract_commitments(operations, config).copy()
    if commitments.empty:
        return base, commitments, pd.DataFrame()
    commitments["advance_amount"] = commitments.advance_amount.astype(float).round(2)
    commitments = commitments[commitments.advance_amount.gt(0.005)].copy()

    contract_cfg = config.get("contract_liabilities", {})
    refund_grace_months = int(contract_cfg.get("refund_grace_months", 3))

    months = sorted(operations.month.unique())
    sales = operations[operations.division.isin(["Software", "Events"])].groupby(
        ["month", "entity", "division", "customer", "product"], as_index=False
    ).revenue.sum()
    sales["revenue"] = sales.revenue.astype(float).round(2)

    commitments_by_receipt = {month: group.copy() for month, group in commitments.groupby("month")}
    open_contracts: list[dict] = []
    ar_balance: dict[tuple[str, str], float] = defaultdict(float)
    new_rows: list[dict] = []
    schedule_rows: list[dict] = []

    for month in months:
        period = pd.Period(month, freq="M")
        month_sales = sales[sales.month.eq(month)].copy()
        invoice_available = {
            (str(r.entity), str(r.division), str(r.customer), str(r.product)): _cents(r.revenue)
            for r in month_sales.itertuples(index=False)
        }
        release_by_ed: dict[tuple[str, str], float] = defaultdict(float)

        # Cancel contracts that remain unfulfilled beyond the contractual grace
        # period. The refund reduces both cash and account 2300; it never touches
        # revenue because no service has been recognized for the outstanding lot.
        for lot in open_contracts:
            outstanding = _cents(lot["outstanding"])
            if outstanding <= 0.005:
                continue
            service_period = pd.Period(lot["service_month"], freq="M")
            overdue_months = period.ordinal - service_period.ordinal
            if overdue_months <= refund_grace_months:
                continue
            jid = f"CONTRACT-REFUND-{month}-{lot['entity']}-{lot['customer']}-{lot['product']}"
            new_rows.append(_journal_row(
                month=month,
                entity=lot["entity"],
                division=lot["division"],
                journal_id=jid,
                journal_type="customer_advance_refund",
                account=CONTRACT_LIABILITY_ACCOUNT,
                debit=outstanding,
                customer=lot["customer"],
                product=lot["product"],
                description="Refund of unfulfilled customer advance after contractual grace period",
            ))
            new_rows.append(_journal_row(
                month=month,
                entity=lot["entity"],
                division=lot["division"],
                journal_id=jid,
                journal_type="customer_advance_refund",
                account="1000_CASH",
                credit=outstanding,
                customer=lot["customer"],
                product=lot["product"],
                description="Refund of unfulfilled customer advance after contractual grace period",
                cash_flow_category="customer_collections",
            ))
            lot["outstanding"] = 0.0

        # Apply previously received customer advances to the intended invoice.
        for lot in open_contracts:
            if lot["outstanding"] <= 0.005 or pd.Period(lot["service_month"], freq="M") > period:
                continue
            key = (lot["entity"], lot["division"], lot["customer"], lot["product"])
            available = _cents(invoice_available.get(key, 0.0))
            if available <= 0.005:
                continue
            applied = _cents(min(float(lot["outstanding"]), available))
            if applied <= 0.005:
                continue
            jid = f"CONTRACT-APPLY-{month}-{lot['entity']}-{lot['customer']}-{lot['product']}"
            new_rows.append(_journal_row(
                month=month,
                entity=lot["entity"],
                division=lot["division"],
                journal_id=jid,
                journal_type="contract_liability_application",
                account=CONTRACT_LIABILITY_ACCOUNT,
                debit=applied,
                customer=lot["customer"],
                product=lot["product"],
                description="Customer advance applied to recognized service",
            ))
            new_rows.append(_journal_row(
                month=month,
                entity=lot["entity"],
                division=lot["division"],
                journal_id=jid,
                journal_type="contract_liability_application",
                account="1100_AR",
                credit=applied,
                customer=lot["customer"],
                product=lot["product"],
                description="Customer advance applied to invoice",
            ))
            lot["outstanding"] = _cents(float(lot["outstanding"]) - applied)
            invoice_available[key] = _cents(available - applied)
            release_key = (lot["entity"], lot["division"])
            release_by_ed[release_key] = _cents(release_by_ed[release_key] + applied)

        # Rebuild ordinary collections only for the residual amount not prepaid.
        sales_ed = month_sales.groupby(["entity", "division"], as_index=False).revenue.sum()
        for r in sales_ed.itertuples(index=False):
            entity, division = str(r.entity), str(r.division)
            revenue = _cents(r.revenue)
            release = _cents(release_by_ed.get((entity, division), 0.0))
            residual_billed = _cents(max(revenue - release, 0.0))
            key = (entity, division)
            available_ar = _cents(ar_balance[key] + revenue - release)
            dso = float(config["divisions"][division]["dso"])
            target_end = residual_billed * dso / 30.0
            collection = _cents(min(max(available_ar - target_end, 0.0), available_ar))
            if collection > 0.005:
                jid = f"COLL-CONTRACT-{month}-{entity}-{division.replace(' ', '')}"
                new_rows.append(_journal_row(
                    month=month,
                    entity=entity,
                    division=division,
                    journal_id=jid,
                    journal_type="collection",
                    account="1000_CASH",
                    debit=collection,
                    description="Customer collections after advance application",
                    cash_flow_category="customer_collections",
                ))
                new_rows.append(_journal_row(
                    month=month,
                    entity=entity,
                    division=division,
                    journal_id=jid,
                    journal_type="collection",
                    account="1100_AR",
                    credit=collection,
                    description="Customer collections after advance application",
                ))
            ar_balance[key] = _cents(max(available_ar - collection, 0.0))

        # Receive next-month advances after current service settlement.
        receipt_scope = commitments_by_receipt.get(month)
        if receipt_scope is not None:
            for r in receipt_scope.itertuples(index=False):
                amount = _cents(r.advance_amount)
                if amount <= 0.005:
                    continue
                jid = f"CONTRACT-CASH-{month}-{r.entity}-{r.customer}-{r.product}"
                new_rows.append(_journal_row(
                    month=month,
                    entity=str(r.entity),
                    division=str(r.division),
                    journal_id=jid,
                    journal_type="customer_advance",
                    account="1000_CASH",
                    debit=amount,
                    customer=str(r.customer),
                    product=str(r.product),
                    description=f"Customer advance for service month {r.service_month}",
                    cash_flow_category="customer_collections",
                ))
                new_rows.append(_journal_row(
                    month=month,
                    entity=str(r.entity),
                    division=str(r.division),
                    journal_id=jid,
                    journal_type="customer_advance",
                    account=CONTRACT_LIABILITY_ACCOUNT,
                    credit=amount,
                    customer=str(r.customer),
                    product=str(r.product),
                    description=f"Contract liability for service month {r.service_month}",
                ))
                open_contracts.append({
                    "receipt_month": month,
                    "service_month": str(r.service_month),
                    "entity": str(r.entity),
                    "division": str(r.division),
                    "customer": str(r.customer),
                    "product": str(r.product),
                    "product_family": str(r.product_family),
                    "quality_tier": str(r.quality_tier),
                    "original_amount": amount,
                    "outstanding": amount,
                })

        # Snapshot the exact cent-level legal subledger after the month close.
        for lot in open_contracts:
            outstanding = _cents(lot["outstanding"])
            if outstanding <= 0.005:
                continue
            schedule_rows.append({
                "month": month,
                "receipt_month": lot["receipt_month"],
                "service_month": lot["service_month"],
                "entity": lot["entity"],
                "division": lot["division"],
                "customer": lot["customer"],
                "product": lot["product"],
                "product_family": lot["product_family"],
                "quality_tier": lot["quality_tier"],
                "original_advance": _cents(lot["original_amount"]),
                "contract_liability": outstanding,
                "months_to_service": pd.Period(lot["service_month"], freq="M").ordinal - period.ordinal,
            })

    contract_journal = pd.DataFrame(new_rows, columns=journal.columns)
    adjusted = pd.concat([base, contract_journal], ignore_index=True)
    schedule = pd.DataFrame(schedule_rows)
    return adjusted, commitments, schedule