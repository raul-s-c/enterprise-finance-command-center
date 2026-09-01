# Provisions and Asset Quality

Version 0.7 converts two management-risk schedules into accounting estimates:

- expected credit losses on trade receivables
- obsolescence provisions on physical inventory

The objective is to keep operational aging and accounting valuation connected without making them the same dataset.

## Design principle

Gross subledgers remain unchanged:

```text
Customer invoices / collections -> Gross AR -> AR aging
Inventory receipts / consumption -> Gross Inventory -> Inventory aging
```

Accounting valuation is then layered on top:

```text
Gross AR
- Credit Loss Allowance
= Net Trade Receivables

Gross Inventory
- Inventory Provision
- Consolidation-only Unrealized IC Markup Reserve
= Net Consolidated Inventory
```

The AR aging schedule must continue to reconcile to `1100_AR` and the inventory aging schedule must continue to reconcile to `1200_INVENTORY`.

## Expected credit loss policy

The model uses deterministic aging rates as a synthetic simplified expected-credit-loss policy.

Base rates:

```text
Current            0.2%
1-30 overdue       1.0%
31-60 overdue      4.0%
61-90 overdue     12.0%
>90 overdue       45.0%
```

Each customer also has the stable risk score already used in the AR aging model. Risk score 1-5 scales the base provision rate between 0.70x and 1.35x.

For each customer:

```text
Allowance = sum(Aging Bucket x Bucket Rate x Customer Risk Multiplier)
```

The allowance is capped at gross AR.

### Accounts

```text
1190_CREDIT_LOSS_ALLOWANCE
6050_CREDIT_LOSS_EXPENSE
```

Increase in allowance:

```text
Dr 6050_CREDIT_LOSS_EXPENSE
Cr 1190_CREDIT_LOSS_ALLOWANCE
```

Release:

```text
Dr 1190_CREDIT_LOSS_ALLOWANCE
Cr 6050_CREDIT_LOSS_EXPENSE
```

The expense is presented in OPEX rather than Gross Profit.

## Inventory provision policy

Inventory aging introduced in v0.4 is the source for the provision calculation.

Base rates:

```text
0-30 days          0.0%
31-60 days         0.5%
61-90 days         2.0%
91-180 days       12.0%
>180 days         55.0%
```

Risk multipliers make the valuation more economically specific:

- Legacy generation: 1.25x
- Spare Parts: 0.85x because long-tail stock has legitimate aftermarket demand
- Premium tier: 1.10x because higher unit values create greater stock exposure

The final provision is capped at gross inventory.

### Accounts

```text
1290_INVENTORY_PROVISION
5460_INVENTORY_OBSOLESCENCE
```

Increase in provision:

```text
Dr 5460_INVENTORY_OBSOLESCENCE
Cr 1290_INVENTORY_PROVISION
```

Release:

```text
Dr 1290_INVENTORY_PROVISION
Cr 5460_INVENTORY_OBSOLESCENCE
```

Inventory provision expense is presented in Gross Profit because it is directly linked to the carrying value of inventory held for sale.

## Retained earnings

The original accounting engine closes its P&L monthly before the v0.7 supplemental valuation layer runs.

Version 0.7 therefore creates explicit supplemental closing entries for the two new P&L accounts so every provision movement is transferred to `3200_RETAINED_EARNINGS` in the same month.

This prevents open historical P&L balances and keeps the balance sheet equation intact.

## Tax treatment

The project does not attempt to model country-specific deductibility rules for book provisions.

Version 0.7 therefore treats both provision types as non-deductible accounting adjustments in the current synthetic tax model.

Consequences:

- provision expense affects EBIT and retained earnings
- it does not create an invented tax benefit
- provision entries have no direct cash-flow line

This assumption is deliberately conservative and documented rather than hidden inside the tax engine.

## Cash and Working Capital

Provision journals never post to cash.

Expected credit loss expense is also excluded from the DPO operating-spend denominator because it is not supplier expenditure.

The Working Capital view distinguishes:

```text
Gross Trade Receivables
Credit Loss Allowance
Net Trade Receivables

Gross Inventory
Inventory Provision
Net Inventory

Gross Net Working Capital
Provision-adjusted Net Working Capital
```

DSO and DIO use the net accounting carrying values in the current CFO view, while the detailed aging schedules preserve the gross operational exposure.

## Consolidation

Credit loss allowance is summed across legal entities.

For inventory, two different adjustments remain visible:

```text
Gross Legal Inventory
- Inventory Provision
- Unrealized Intercompany Markup Reserve
= Net Consolidated Inventory
```

The inventory provision is a legal-book valuation adjustment. The unrealized markup reserve is a consolidation adjustment. They are deliberately kept separate.

## Release controls

Version 0.7 blocks publication if:

- credit loss allowance schedule does not reconcile to account `1190_CREDIT_LOSS_ALLOWANCE`
- inventory provision schedule does not reconcile to account `1290_INVENTORY_PROVISION`
- either allowance exceeds its gross asset
- any journal is unbalanced
- any legal or consolidated balance sheet stops balancing
- cash changes because of a provision journal
- previous Working Capital, factory absorption, intercompany or forecast controls fail

## Dashboard

The Working Capital view now presents gross exposure, allowance/provision and net carrying value separately.

It also shows:

- largest customer ECL exposures
- customer risk and allowance percentage
- largest SKU inventory provisions
- provision percentages
- original operational aging watchlists

The Balance Sheet presents the gross-to-net asset bridges, while the P&L identifies the current-month inventory-provision and credit-loss movements separately from factory absorption.
