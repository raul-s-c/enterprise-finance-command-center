# Data Contract

The project separates source-like operating data, accounting data and analytical outputs so each layer has a clear responsibility.

## Macro layer

`macro.csv` contains one row per month with inflation, industrial activity, energy, policy-rate and FX drivers plus one source field per driver. Inflation and industrial production prefer Eurostat, energy prefers the World Bank Pink Sheet and policy rates and FX prefer the ECB Data Portal. Missing exact-month observations retain deterministic fallback values.

`macro_lineage.csv` contains one row per close, observation month and driver. It records the applied value, unit, applied source, preferred official source, public URL and Official/Fallback status.

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

## Management action execution layer

`management_action_plans.csv` contains one approved execution plan per persistent action cycle, including scope, owner, effective date, target date, driver profile and evidence.

`management_action_benefits.csv` preserves one monthly benefit snapshot per plan. Trigger improvement is directional and explicitly non-additive.

`management_action_actual_impact.csv` contains the additive monthly Revenue, Gross Profit, OPEX and EBIT effects recorded by the operating engine after intervention effective dates.

`management_action_forecast_bridge.csv` contains the additive Base, Upside and Downside action impact embedded in the current forecast.

## Financial sensitivity layer

`financial_sensitivity_detail.csv` contains standalone 12-month Base exposure by shock, entity and division. Monetary fields include Revenue, Gross Profit, OPEX benefit, EBIT, interest expense, Net Income, Ending Cash and Net Debt impacts.

`financial_sensitivity_summary.csv` reconciles detail to one Group row per controlled shock and adds Net Leverage and Interest Coverage deltas. Rows are explicitly non-additive and do not replace or mutate forecast scenarios.

## Transaction FX layer

`transaction_fx_documents.csv` contains one foreign-currency monetary document per source journal and AR/AP account. It preserves functional and transaction currency, original amounts, source account, counterparty and payment terms.

`transaction_fx_snapshots.csv` contains the monthly open-to-settled lifecycle, closing carrying values and functional/EUR realized and unrealized FX gain or loss.

`transaction_fx_summary.csv` aggregates open receivables, payables, net exposure and FX P&L by month, entity and transaction currency. Transaction remeasurement is separate from the CTA translation reserve.

## Web contract

`web/data/dashboard.json` is a compact read-only payload for the GitHub Pages application. It contains actuals, management detail, working capital, cash flow, balance sheet, forecast, accuracy, profitability, PVM, intercompany, factories, CAPEX, portfolio events, management commentary, action execution, macro lineage, financial sensitivities, controls and source metadata.

`web/data/manifest.json` describes the latest close and row counts.

## Retention

The front-end and processed actual data retain a rolling 36-month history. The current forecast covers 18 months. Historical forecast vintages are stored at an analytical grain rather than duplicating full transaction-level forecast ledgers.
