# Enterprise Finance Command Center

Enterprise Finance Command Center is an end-to-end CFO analytics project built around a continuously evolving synthetic multinational company.

The project does not generate disconnected dashboard numbers. It models economic activity first, translates that activity into double-entry accounting, consolidates legal entities, derives connected financial statements, creates rolling forecasts and publishes a CFO-oriented analytical application.

The synthetic group is Aureon Systems Group. It operates four deliberately different business models:

- Software: recurring subscriptions and services
- Hardware: manufactured units sold through commercial entities
- Events & Projects: project-based revenue with irregular demand
- Spare Parts: high-SKU aftermarket activity with inventory intensity

The group has six legal entities across Germany, Spain, Czech Republic, China, the United States and Japan. Two entities operate manufacturing sites and supply commercial entities through cost-plus intercompany flows.

Live application: https://raul-s-c.github.io/enterprise-finance-command-center/

## Core design principle

```text
Macro environment
        ->
Business drivers
        ->
Operating events
        ->
Double-entry ledger
        ->
Legal-entity financials
        ->
Intercompany consolidation
        ->
P&L / Balance Sheet / Cash Flow
        ->
Working Capital / CAPEX / Profitability
        ->
Rolling forecast
        ->
Management decisions
        ->
CFO analytics
```

P&L, balance sheet, cash flow and working capital are outputs of the same economic and accounting system. They are not generated independently.

## Current release: v0.2

The current finance engine includes:

- 36 rolling months of synthetic actuals
- 18-month rolling forecast
- historical forecast vintages
- Base, Upside and Downside scenarios
- entity/division forecast bias correction using only observable historical errors
- product and customer master data
- asymmetric granularity by division
- customer-product operating activity
- double-entry journals
- monthly P&L closing to retained earnings
- legal entity P&L and balance sheets
- consolidated management P&L
- connected cash flow
- AR, AP and inventory working-capital mechanics
- DSO, DPO and DIO
- cost-plus intercompany manufacturing flows
- reciprocal intercompany AR/AP and settlements
- transfer-pricing consolidation bridge
- unrealized intercompany markup reserve in inventory
- CAPEX project lifecycle from CIP to go-live, PPE and depreciation
- factory capacity and utilization
- debt, interest, income-tax accruals and quarterly payments
- product and customer profitability
- price / volume / mix analysis
- deterministic portfolio reviews
- product phase-out and replacement launch events
- procedural CFO commentary
- automated financial validation controls
- static CFO web application deployed through GitHub Pages

## Synthetic company structure

Legal entity and management structures are intentionally separate.

```text
Aureon Systems Group

DE01 Germany
  HQ
  Software
  Hardware Sales

ES01 Spain
  Hardware Sales
  Events
  Spare Parts

CZ01 Czech Republic
  Hardware Factory

CN01 China
  Hardware Factory / Sourcing

US01 United States
  Software
  Hardware Sales
  Events

JP01 Japan
  Software
  Hardware Sales
  Spare Parts
```

A sale can therefore start with manufacturing in China or Czech Republic, create an intercompany cost-plus invoice, create inventory in a commercial entity, become an external customer sale, create receivables and finally convert to cash.

## Financial controls

Publication is blocked if core accounting controls fail.

The current validation suite requires:

- every journal to balance
- total trial balance to equal zero
- every legal balance sheet to balance
- legal intercompany AR and AP to reconcile
- consolidated balance sheet to balance
- cash-flow movement to reconcile to balance-sheet cash
- legal-to-group revenue bridge to reconcile
- legal-to-group EBIT bridge to reconcile
- forecast targets to occur strictly after their forecast vintage

A failed control raises an exception before deployment.

## Macro and external data

The pipeline is designed so the synthetic company remains reproducible even when an external source is temporarily unavailable.

Current preferred live source:

- ECB Data Portal monthly foreign-exchange reference rates

Current deterministic fallback drivers:

- inflation
- industrial activity index
- energy index
- policy interest rate
- FX curves

The source layer is isolated from the finance engine, allowing Eurostat industrial production, Eurostat HICP and World Bank commodity data to replace fallback drivers without changing downstream accounting or reporting logic.

## Rolling forecasting

Every close creates a forecast vintage. Historical vintages remain available for accuracy analysis.

The forecast engine:

1. uses only information available at the vintage date
2. estimates a driver-based baseline from recent actuals
3. applies divisional growth and seasonality
4. calculates historical entity/division bias from already-realized prior forecasts
5. applies a capped bias correction
6. generates Base, Upside and Downside scenarios
7. stores the forecast vintage for later MAPE and bias evaluation

This allows analysis such as Actual vs FC-1, FC-3, FC-6 and forecast-bias evolution as the project accumulates monthly closes.

## Product lifecycle

Products are not permanently static.

At scheduled portfolio reviews, the engine evaluates trailing profitability against divisional rules. Persistently weak products can be approved for phase-out. The economic activity then stops after a defined delay and, where configured, a replacement product launches later.

The resulting financial effects flow naturally through revenue, margin, inventory, working capital, factories and cash rather than being inserted directly into the dashboard.

## Repository structure

```text
.github/workflows/       Monthly close, validation and Pages deployment
config/                  Company structure and finance assumptions
data/processed/          Generated financial and operating outputs
docs/                    Architecture, finance model and data contracts
src/enterprise_finance/  Simulation, accounting, reporting and forecasting engine
tests/                   Financial and technical controls
web/                     Static CFO application
```

## Run locally

```bash
python -m pip install -e ".[dev]"
pytest
python -m enterprise_finance.cli build --end-month 2026-07
```

To force deterministic fallback macro data:

```bash
python -m enterprise_finance.cli build --end-month 2026-07 --offline-macro
```

If `--end-month` is omitted, the pipeline closes the previous completed calendar month.

## Main generated outputs

```text
data/processed/chart_of_accounts.csv
data/processed/macro.csv
data/processed/products.csv
data/processed/customers.csv
data/processed/operational.csv
data/processed/portfolio_events.csv
data/processed/journal.csv.gz
data/processed/journal_sample.csv
data/processed/legal_pnl.csv
data/processed/management_pnl.csv
data/processed/pnl.csv
data/processed/legal_balance_sheet.csv
data/processed/balance_sheet.csv
data/processed/cash_flow.csv
data/processed/working_capital.csv
data/processed/intercompany.csv
data/processed/factory.csv
data/processed/capex.csv
data/processed/product_profitability.csv
data/processed/customer_profitability.csv
data/processed/price_volume_mix.csv
data/processed/consolidation_bridge.csv
data/processed/forecast_vintages.csv
data/processed/forecast.csv
data/processed/forecast_accuracy.csv
data/processed/validation.json
web/data/dashboard.json
```

The full ledger is stored as compressed CSV to prevent unnecessary repository growth while preserving auditability. A readable sample is also published.

## Automation

GitHub Actions performs the full close automatically:

1. install the finance engine
2. run tests
3. refresh external macro inputs where available
4. simulate the rolling actual period
5. create the accounting ledger
6. consolidate and validate financial statements
7. build rolling forecast vintages and accuracy outputs
8. generate the CFO analytical dataset
9. commit updated generated outputs
10. publish GitHub Pages

The core project requires no paid database, hosted application server, paid market-data subscription or paid AI API.

## Synthetic data notice

Aureon Systems Group is fictional. Company names, customers, products, transactions and financial results are synthetic. Real public macroeconomic data may be used as external drivers but does not represent the financial performance of any real company.
