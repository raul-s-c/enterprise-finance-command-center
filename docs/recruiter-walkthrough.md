# Three-minute walkthrough

A guided route through the live application for reviewers who want to see the month-end close and finance leadership skills behind it: from posted journals to statements, cash, forecast, controls and owned actions.

Live application: https://raul-s-c.github.io/enterprise-finance-command-center/

Every number in the dashboard is published by the monthly close pipeline from one synthetic double-entry ledger. The header shows the closed month and whether every release control passed; if the dataset cannot load it says so instead of showing a default.

## Route

| # | Open | What it shows | What to check |
| --- | --- | --- | --- |
| 1 | [Executive](https://raul-s-c.github.io/enterprise-finance-command-center/#view=executive) | Result, why it moved (price / volume / mix), group outlook and the owned management action | Each claim names its evidence; group-only measures say "Group" when an entity filter is applied |
| 2 | [P&L](https://raul-s-c.github.io/enterprise-finance-command-center/#view=pnl) | Income statement actual vs prior year as a cumulative bridge | Select a line to see its calculation, source dataset and entity / division contribution |
| 3 | [Cash Flow](https://raul-s-c.github.io/enterprise-finance-command-center/#view=cash-flow) | Signed operating, investing and financing cash movements | Trace a month to cash-account journals; AR/AP allocations are labelled as analytical, not bank-matched |
| 4 | [Balance Sheet](https://raul-s-c.github.io/enterprise-finance-command-center/#view=balance-sheet) | Financial position with the balance-sheet equation | Liabilities + equity = total assets with a zero balance check and no balancing plug |
| 5 | [Working Capital](https://raul-s-c.github.io/enterprise-finance-command-center/#view=working-capital) | Receivables, inventory and payables with DSO / DIO / DPO | Drill to invoice-level AR, source-accrual AP and SKU inventory evidence that reconcile to the ledger |
| 6 | [Operations & CAPEX](https://raul-s-c.github.io/enterprise-finance-command-center/#view=operations-capex) | Factory utilization and absorption, CAPEX from cash spend through CIP to PPE | Absorption variance is posted to the ledger; project spend ties to approved budget to the cent |
| 7 | [Plan & Outlook](https://raul-s-c.github.io/enterprise-finance-command-center/#view=forecast) | 24-month Base / Upside / Downside forecast with linked P&L, balance sheet and cash | Forecast balance sheet balances; cash comes from the liquidity model, retained earnings from forecast net income |
| 8 | [Close journey](https://raul-s-c.github.io/enterprise-finance-command-center/#view=close-journey) | Eight close stages from drivers to actions, each with its control and evidence | Every control shows the measured result against its published threshold |
| 9 | [Performance review](https://raul-s-c.github.io/enterprise-finance-command-center/#view=performance-review) and [Action execution](https://raul-s-c.github.io/enterprise-finance-command-center/#view=action-execution) | Variance review, owners, due dates and benefit tracking | Overdue actions escalate; benefits are directional and explicitly non-additive |

Use the Entity and Division filters at any point: scoped reports follow the selection, and reports that are fixed at group level say so in the context line.

## Evidence boundaries

The model states what it does not claim:

- Customer collections and supplier payments are allocated to invoices and accruals analytically; they are not bank-matched remittances.
- Depreciation journals are entity-aggregated; project depreciation is derived from approved budget and useful life, and opening-pool depreciation remains a ledger residual.
- Standalone macro sensitivities are not additive.
- The first actual month is a start-up period (no opening inventory, receivables or payables) and sits outside the 12-month operating window.

## Where the controls live

- Release controls: every check and its measured value are published in `web/data/manifest.json` (`validation`) and shown against thresholds in the [Close journey](https://raul-s-c.github.io/enterprise-finance-command-center/#view=close-journey); publication gating is described in [docs/close-publication.md](close-publication.md).
- Accounting design: [docs/finance-model.md](finance-model.md), [docs/factory-absorption-accounting.md](factory-absorption-accounting.md), [docs/capex-cash-transfer.md](capex-cash-transfer.md).
- Lineage: [docs/working-capital-lineage.md](working-capital-lineage.md), [docs/cash-movement-lineage.md](cash-movement-lineage.md).
