# Data Contract

The project separates source-like operating data, accounting data and analytical outputs so each layer has a clear responsibility.

## Macro layer

`macro.csv` contains one row per month with inflation, industrial activity, energy, policy-rate and FX drivers. FX prefers ECB monthly reference rates and falls back to deterministic synthetic curves when live data is unavailable.

## Master data

`products.csv` contains the product portfolio and lifecycle attributes.

`customers.csv` contains customer, legal-entity, segment and division attributes.

`chart_of_accounts.csv` defines the accounting structure used by the ledger.

## Operating layer

`operational.csv` is the core commercial and operating fact table. Its granularity is intentionally asymmetric by division. It contains the dimensions and drivers required to create revenue, variable cost, fixed production cost, selling cost, gross profit and operating expenses.

`portfolio_events.csv` records rule-based product lifecycle decisions such as phase-out approval and replacement launch.

## Accounting layer

`journal.csv.gz` is the complete double-entry ledger for the rolling history. The compressed format limits repository growth while preserving the full accounting audit trail.

`journal_sample.csv` exposes a small readable subset for inspection in GitHub.

`legal_pnl.csv` contains legal-entity P&L derived from journals.

`legal_balance_sheet.csv` contains legal-entity balance-sheet positions derived from journals.

`cash_flow.csv` contains entity cash-flow classifications derived from movements in the cash account and journal type.

## Consolidation and management layer

`management_pnl.csv` contains the management P&L by month, entity and division.

`pnl.csv` contains the consolidated monthly management P&L.

`balance_sheet.csv` contains the consolidated balance sheet including the unrealized intercompany markup reserve.

`working_capital.csv` contains receivables, inventory, payables, NWC, DSO, DIO and DPO.

`intercompany.csv` contains manufacturing transfers between factories and commercial entities.

`consolidation_bridge.csv` reconciles legal-entity totals to consolidated management results.

## Operational finance analytics

`factory.csv` contains factory capacity, production and utilization.

`capex.csv` contains the investment project portfolio.

`product_profitability.csv` and `customer_profitability.csv` provide trailing-12-month profitability views.

`price_volume_mix.csv` decomposes year-over-year revenue change into price, volume and mix.

## Forecast layer

`forecast_vintages.csv` stores historical rolling forecast vintages.

`forecast.csv` contains the latest Base, Upside and Downside forward forecast.

`forecast_accuracy.csv` compares closed forecast vintages with actual operating performance and calculates error, absolute percentage error and bias.

## Web contract

`web/data/dashboard.json` is a compact read-only payload for the GitHub Pages application. It contains actuals, management detail, working capital, cash flow, balance sheet, forecast, accuracy, profitability, PVM, intercompany, factories, CAPEX, portfolio events, management commentary, controls and source metadata.

`web/data/manifest.json` describes the latest close and row counts.

## Retention

The front-end and processed actual data retain a rolling 36-month history. The current forecast covers 18 months. Historical forecast vintages are stored at an analytical grain rather than duplicating full transaction-level forecast ledgers.
