# Treasury and Liquidity

Version 0.11 adds a legal-entity Treasury layer to the Enterprise Finance Command Center.

The objective is not to display cash and debt balances as disconnected KPIs. Treasury acts on the same ledger that already contains customer collections, customer advances, supplier payments, CAPEX, tax, interest, debt amortization and intercompany settlements.

## Cash pooling

Aureon Systems Group uses Germany (`DE01`) as the Treasury hub.

Each subsidiary has a configured minimum operating cash balance. A subsidiary with cash above its minimum plus the configured buffer sweeps a percentage of the excess to HQ.

```text
Subsidiary surplus cash
Dr Intercompany Treasury Receivable
Cr Cash

HQ receives the sweep
Dr Cash
Cr Intercompany Treasury Payable
```

If a subsidiary falls below its minimum operating cash level, HQ provides liquidity:

```text
HQ funding
Dr Intercompany Treasury Receivable
Cr Cash

Subsidiary receives liquidity
Dr Cash
Cr Intercompany Treasury Payable
```

Accounts introduced:

```text
1160_IC_TREASURY_RECEIVABLE
2160_IC_TREASURY_PAYABLE
```

The two accounts are legal-entity balances and eliminate in consolidation.

## Treasury policy

The policy is defined in `config/company.yml`.

It contains:

- Treasury hub entity
- minimum cash by legal entity
- default minimum cash
- sweep buffer
- sweep ratio
- revolving credit facility limit
- Net Debt / EBITDA covenant limit
- interest-coverage minimum
- contractual debt maturities by entity

The policy is therefore visible and reviewable rather than embedded as unexplained constants in the dashboard.

## Cash-flow presentation

Cash pooling does not change consolidated cash.

At legal-entity level, cash-pool movements are classified as financing cash flows under:

```text
intercompany_treasury
```

The group sum of those movements must be zero for every month.

## Debt schedule

The debt schedule is reconstructed from account:

```text
2500_DEBT
```

For every legal entity and month the model derives:

- gross debt
- monthly interest expense
- implied annual interest rate
- contractual maturity

The schedule carries debt balances forward even in months without a debt transaction.

## Liquidity and covenants

The group Treasury schedule derives:

```text
EBITDA = EBIT + Depreciation
Net Debt = Gross Debt - Cash
Net Leverage = Net Debt / TTM EBITDA
Interest Coverage = TTM EBITDA / TTM Interest
```

Liquidity headroom is defined as:

```text
Cash above group minimum operating cash
+ Undrawn RCF
= Liquidity Headroom
```

The current model does not automatically draw the RCF. It exposes available liquidity capacity and covenant headroom to management.

## Debt maturity ladder

Outstanding debt at the latest close is grouped by contractual maturity.

This creates a simple refinancing ladder for the CFO without creating hypothetical future refinancing transactions.

## Hard controls

A release is blocked unless all Treasury controls pass:

```text
Cash-pool journals balanced                       = 0 gap
Group cash before pooling - after pooling         = 0 gap
IC Treasury Receivable - IC Treasury Payable      = 0 gap
Legal Balance Sheet equation                      = 0 gap
Consolidated Balance Sheet equation               = 0 gap
Debt schedule - account 2500_DEBT                 = 0 gap
Subsidiaries below configured minimum cash        = 0
Entities with negative closing cash               = 0
```

These controls run in addition to all existing accounting, Working Capital, provisions, customer-funding, intercompany, factory, Budget and Forecast controls.

## Generated outputs

```text
data/processed/treasury_cash_pool.csv
data/processed/treasury_entity_cash.csv
data/processed/debt_schedule.csv
data/processed/debt_maturity_ladder.csv
data/processed/liquidity_covenants.csv
```

The CFO application adds a dedicated **Treasury** view with legal cash positions, pool movements, debt, liquidity headroom, leverage, interest coverage and the maturity ladder.
