# Working Capital Schedules

Version 0.4 turns Working Capital from a small set of aggregate ratios into finance schedules that reconcile back to the accounting ledger.

The design rule is simple: analytical aging must never become a second, disconnected version of the balance sheet.

## Accounts covered

The current release creates detailed schedules for:

- `1100_AR` Trade Receivables
- `1200_INVENTORY` Inventory

Both schedules are validated against the cumulative GL balance for every month, legal entity and management division.

## Accounts receivable aging

External sales already enter the ledger as customer invoices:

```text
Dr 1100_AR
Cr 4000_EXTERNAL_REVENUE
```

Customer collections reduce the same account:

```text
Dr 1000_CASH
Cr 1100_AR
```

The AR schedule reconstructs the open invoice population from those journal movements. Collections are allocated deterministically across open customer balances using invoice age, contractual payment terms and a stable synthetic customer-risk score.

The result therefore remains exactly constrained by the GL balance while still allowing different customers to pay at different speeds.

### AR aging buckets

```text
Current
1-30 days overdue
31-60 days overdue
61-90 days overdue
>90 days overdue
```

### Customer risk

Every customer receives a stable risk score from 1 to 5. The score is based on customer segment, size and a deterministic customer-specific component. It affects collection priority but does not change the total amount of cash collected by the accounting engine.

This separation is deliberate:

- the ledger determines total receivables and cash collection
- the subledger determines which customers remain open
- the reconciliation control requires both views to agree

The CFO application exposes overdue concentration, high-risk customers and the >90-day bucket.

## Inventory aging

Physical inventory exists for Hardware and Spare Parts. The legal GL balance is created by intercompany inventory receipts and external cost-of-sales consumption.

The detailed analytical inventory schedule allocates that legal inventory balance across the SKU hierarchy using observed product consumption patterns.

The allocation uses:

- recent SKU consumption
- trailing demand
- division
- quality tier
- product generation
- strategic role

Spare Parts intentionally receives higher stock-propensity assumptions than Hardware. Legacy products also retain more inventory exposure than current-generation products.

The schedule does not create additional inventory value. It distributes the balance already present in `1200_INVENTORY` and must reconcile back to that account.

### Inventory aging buckets

```text
0-30 days
31-60 days
61-90 days
91-180 days
>180 days
```

Aging is built from closing inventory value, observed monthly SKU usage and months since last sale. This creates a transparent inventory-coverage interpretation rather than assigning arbitrary dates to synthetic stock.

### Inventory quality flags

Each SKU receives:

- inventory value
- monthly usage
- months of coverage
- months since last sale
- slow-moving value
- obsolescence-risk value
- stock status

Stock status can be:

```text
Healthy
Excess
Slow moving
Obsolescence risk
```

The current release treats obsolescence as a management risk indicator. It does not yet post an accounting provision. A later release can introduce a formal inventory-provision policy with P&L and balance-sheet consequences.

## Reconciliation controls

Publication fails if any of the following controls exceeds EUR 0.05:

- AR schedule vs `1100_AR`
- AR aging buckets vs AR schedule total
- Inventory schedule vs `1200_INVENTORY`
- Inventory aging buckets vs inventory schedule total

These controls are added to the same release gate as journal balance, trial balance, balance-sheet equation, intercompany reconciliation, cash flow and consolidation.

## Generated outputs

```text
data/processed/ar_aging.csv
data/processed/inventory_aging.csv
```

The dashboard dataset also contains:

```text
ar_aging_summary
ar_customer_aging
inventory_aging_summary
inventory_sku_aging
inventory_family_aging
```

## CFO questions enabled

The Working Capital view can now answer questions such as:

- How much AR is overdue?
- Which customers drive the overdue balance?
- How much is more than 90 days overdue?
- Is the overdue balance concentrated in high-risk customers?
- How much inventory is slow moving?
- Which families consume the most inventory?
- Which SKUs have excessive months of coverage?
- How much stock is exposed to obsolescence risk?
- Does the analytical schedule reconcile to the legal GL?

The next logical extensions are AP aging, inventory provisions, collection-risk events and divisional operational schedules such as software ARR/churn and events backlog.
