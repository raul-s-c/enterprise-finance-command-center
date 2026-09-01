# Supplier Payables and Concentration

Version 0.8 completes the operating Working Capital schedules with supplier-level Accounts Payable analysis.

The objective is to separate three different questions:

```text
DPO                    -> How quickly is the company paying suppliers?
AP aging               -> Which supplier balances make up the legal payable?
Supplier concentration -> How dependent is the company on specific external suppliers?
```

These are related but not interchangeable measures.

## Ledger constraint

The supplier schedule is reconstructed from account:

```text
2100_AP
```

Credits to `2100_AP` create supplier accrual lots. Debits reduce those lots.

This includes cash supplier payments and non-cash AP releases such as factory over-absorption. The schedule therefore follows the legal liability rather than creating a parallel purchasing balance.

The hard reconciliation is performed at legal-entity level:

```text
Supplier AP Schedule by Legal Entity
= 2100_AP legal-entity balance
```

Division is retained as an analytical source attribute on each supplier lot, but it is not treated as a separate legal payable subledger. This distinction matters for the manufacturing entities: one factory payment can settle external cost that originated from both Hardware and Spare Parts production even when the payment journal is operationally classified under Hardware.

When a payment is allocated, the engine first prefers open lots from the same posted division. If those are insufficient, it can settle other open supplier lots within the same legal entity. This preserves analytical traceability without violating the accounting structure.

## Supplier derivation

The existing accounting engine does not contain a disconnected vendor master. Version 0.8 therefore derives deterministic supplier counterparts from the actual external accruals already present in the ledger.

Supplier categories map from journal economics:

```text
Factory manufacturing cost       -> Manufacturing Supply
Factory absorption variance      -> Factory Fixed Cost
Variable selling and logistics   -> Logistics & Freight
Service delivery                 -> Delivery Partners
Fixed delivery capacity          -> Delivery Capacity
Operating expenses               -> Corporate Services
```

Within each entity/category the engine assigns a stable supplier ID using the journal context. Rebuilding the same company month produces the same supplier counterpart.

This keeps the schedule reproducible while avoiding an unrelated random supplier table.

## Payment terms

Current policy terms are:

```text
Manufacturing Supply   60 days
Factory Fixed Cost     60 days
Logistics & Freight    45 days
Delivery Partners      30 days
Delivery Capacity      45 days
Corporate Services     30 days
```

The existing legal payment engine remains unchanged. Version 0.8 only reconstructs open supplier lots after those payments have occurred.

## Aging buckets

Open AP is classified into:

```text
Current
1-30 days overdue
31-60 days overdue
61-90 days overdue
>90 days overdue
```

Supplier payments reduce the oldest preferred exposure first. A factory over-absorption release preferentially reduces Factory Fixed Cost exposure before other payable lots.

## Supplier concentration

Concentration is based on trailing-12-month external accrual spend, not only on suppliers that have an open balance at the close date.

The schedule calculates:

- trailing-12-month spend by supplier
- supplier share of external spend
- group Top-5 supplier concentration
- number of suppliers represented in trailing spend
- current open AP by supplier
- overdue AP by supplier
- critical-supplier AP exposure
- single-source AP exposure

The Top-5 concentration denominator includes the complete trailing supplier population, including suppliers whose closing AP balance is zero. The supplier watchlist then combines that historical dependency with current payable exposure.

## Supplier risk flags

The current deterministic risk classification uses transparent rules:

```text
Single-source + high criticality -> Single-source critical
Supplier spend share >= 10%      -> High concentration
Open overdue AP                   -> Payment overdue
Otherwise                         -> Normal
```

The risk flag is a management indicator. It does not change accounting entries or supplier payments.

## CFO interpretation

Examples of useful combinations:

- High DPO + low overdue AP: payment terms are structurally long but controlled.
- High DPO + high overdue AP: cash preservation may be creating supplier pressure.
- Low overdue AP + high Top-5 concentration: operational dependency exists even if payment discipline is healthy.
- High single-source AP + low inventory cover: supply continuity should be reviewed together with inventory policy.

## Release controls

Version 0.8 blocks publication if:

- legal-entity AP schedule differs from `2100_AP`
- AP aging buckets do not equal supplier balance
- any reconstructed supplier balance becomes negative
- concentration ratios fall outside 0-100%

These checks extend the existing journal, Balance Sheet, cash-flow, AR, inventory, provisions, factory absorption, intercompany, divisional-schedule and forecast controls.

## Generated outputs

```text
data/processed/ap_aging.csv
data/processed/ap_aging_summary.csv
data/processed/supplier_concentration.csv
data/processed/suppliers.csv
```

The CFO application exposes these outputs inside the Working Capital view rather than creating a disconnected procurement application.
