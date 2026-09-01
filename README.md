# Enterprise Finance Command Center

Enterprise Finance Command Center is an end-to-end CFO analytics project built around a continuously evolving synthetic multinational company.

The project does not generate disconnected dashboard numbers. It models economic activity first, translates that activity into double-entry accounting, consolidates legal entities, derives connected financial statements, creates rolling forecasts and publishes a CFO-oriented analytical application.

The synthetic group is **Aureon Systems Group**. It operates four deliberately different business models:

- Software: recurring subscriptions and services
- Hardware: manufactured units sold through commercial entities
- Events & Projects: project-based revenue with irregular demand
- Spare Parts: high-SKU aftermarket activity with inventory intensity

The group has six legal entities across Germany, Spain, Czech Republic, China, the United States and Japan. Brno and Suzhou operate manufacturing sites and supply commercial entities through cost-plus intercompany flows.

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
Working-capital and asset-quality schedules
        ->
Divisional operating schedules / CAPEX / Profitability
        ->
Rolling forecast
        ->
Management decisions
        ->
CFO analytics
```

P&L, balance sheet, cash flow, Working Capital, asset quality and business-driver analytics all originate from the same economic system. They are not independently generated dashboard series.

## Current release: v0.7

Version 0.7 converts receivables credit risk and inventory obsolescence risk into explicit accounting reserves while preserving the gross operational aging schedules.

The current project contains:

- 236 synthetic product references across four asymmetric divisions
- six legal entities and four management divisions
- 36 rolling actual months
- 18 forecast months
- double-entry accounting
- legal and consolidated financial statements
- customer-level AR aging
- SKU-level inventory aging
- expected credit loss accounting
- inventory obsolescence provision accounting
- gross-to-net asset presentation
- Working Capital schedule-to-GL reconciliation
- Software ARR and retention schedules
- Events bookings and backlog schedules
- Hardware factory-capacity, production-mix and absorption accounting
- Spare Parts installed-base and aftermarket schedules
- historical forecast vintages and accuracy analysis
- deterministic product lifecycle decisions
- automated monthly publication through GitHub Actions and GitHub Pages

## Product hierarchy

```text
Division
  -> Product Family
      -> Product Subfamily
          -> Product Type
              -> Quality Tier
                  -> SKU / Generation
```

Each product type normally has Essential, Professional and Premium tiers. Quality tier changes price, cost, expected demand, selling-cost intensity and customer penetration.

The catalogs are intentionally different:

- Software: Platform, Security, Analytics and Automation
- Hardware: Control Systems, Edge Appliances, Terminals, Network Devices and Sensors & Readers
- Events & Projects: Deployment & Integration, Training & Enablement, Customer Experience and Managed Programs
- Spare Parts: Control Modules, Maintenance Kits, Interface Components, Mechanical Parts, Security Components and Consumables

Customers receive deterministic partial assortments rather than an artificial customer x SKU Cartesian dataset.

See `docs/product-hierarchy.md`.

## Asset quality and provisions

Version 0.7 keeps operating exposure and accounting valuation separate but reconciled.

### Trade receivables

```text
Gross Trade Receivables
- Credit Loss Allowance
= Net Trade Receivables
```

The gross AR schedule is reconstructed from invoices and collections and remains reconciled to `1100_AR`.

The expected-credit-loss model applies aging rates to each customer exposure and scales them with the stable customer risk score.

Base rates:

```text
Current            0.2%
1-30 overdue       1.0%
31-60 overdue      4.0%
61-90 overdue     12.0%
>90 overdue       45.0%
```

Accounts:

```text
1190_CREDIT_LOSS_ALLOWANCE
6050_CREDIT_LOSS_EXPENSE
```

An increase in the allowance reduces EBIT through OPEX. A release reverses the expense.

### Inventory

```text
Gross Legal Inventory
- Inventory Provision
- Unrealized Intercompany Markup Reserve
= Net Consolidated Inventory
```

The inventory aging schedule remains reconciled to `1200_INVENTORY`.

Base provision rates:

```text
0-30 days          0.0%
31-60 days         0.5%
61-90 days         2.0%
91-180 days       12.0%
>180 days         55.0%
```

Legacy, Spare Parts and Premium inventory receive transparent risk multipliers.

Accounts:

```text
1290_INVENTORY_PROVISION
5460_INVENTORY_OBSOLESCENCE
```

Inventory provision movement is presented in Gross Profit.

Provision entries are non-cash. In the current synthetic tax model they are deliberately treated as non-deductible rather than inventing country-specific tax rules.

See `docs/provisions-and-asset-quality.md`.

## Divisional operating schedules

The four divisions deliberately do not share one generic operating KPI framework.

### Software

```text
Opening MRR
+ New MRR
+ Expansion MRR
- Contraction MRR
- Churn MRR
= Ending MRR
```

The schedule calculates MRR, ARR, New ARR, Expansion ARR, Contraction ARR, Churn ARR, NRR, GRR, recurring revenue mix and services revenue. It reconciles to Software operating revenue.

### Events & Projects

```text
Opening Backlog
+ Bookings
- Recognized Revenue
= Ending Backlog
```

The schedule calculates bookings, recognized revenue, ending backlog, book-to-bill, backlog coverage and project units.

### Hardware

Hardware exposes manufacturing economics for Brno and Suzhou:

- produced units
- capacity and utilization
- capacity headroom
- actual fixed factory cost
- standard fixed cost absorbed into production
- factory absorption variance
- under-absorption and over-absorption
- fixed-cost absorption percentage
- fixed cost per produced unit
- production mix by family and quality tier

Factory absorption is accounting, not only a KPI:

```text
Actual Factory Fixed Cost
- Standard Fixed Cost Absorbed
= Factory Absorption Variance
```

Account:

```text
5450_FACTORY_ABSORPTION_VARIANCE
```

The variance affects Gross Profit, tax, retained earnings, AP, supplier cash payments and operating cash flow.

See `docs/factory-absorption-accounting.md`.

### Spare Parts

```text
Opening Installed Base
+ Hardware Additions
- Estimated Retirements
= Ending Installed Base
```

The schedule calculates installed base, aftermarket revenue, revenue per installed unit, active SKUs, inventory coverage and inventory health.

See `docs/divisional-operating-schedules.md`.

## Finance engine

The finance engine includes:

- deterministic synthetic economic activity
- public ECB FX integration with deterministic fallback data
- customer-product operating activity
- double-entry journals
- monthly P&L closing to retained earnings
- legal-entity P&L and balance sheets
- consolidated management P&L
- connected cash flow
- AR, AP and inventory mechanics
- DSO, DPO and DIO
- reconciled AR and inventory aging
- expected credit loss allowance
- inventory obsolescence provision
- cost-plus intercompany manufacturing flows
- reciprocal intercompany AR/AP and settlements
- transfer-pricing consolidation bridge
- unrealized intercompany markup reserve in inventory
- CAPEX lifecycle from CIP to go-live, PPE and depreciation
- factory capacity, utilization and absorption accounting
- debt, interest, income-tax accruals and quarterly payments
- product, family, quality-tier and customer profitability
- price / volume / mix analysis
- deterministic portfolio reviews and replacement launches
- rolling forecast vintages
- Base, Upside and Downside scenarios
- forecast accuracy and bias
- procedural CFO commentary
- automated release controls

## Synthetic company structure

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
  Brno Smart Manufacturing

CN01 China
  Suzhou Manufacturing Hub

US01 United States
  Software
  Hardware Sales
  Events

JP01 Japan
  Software
  Hardware Sales
  Spare Parts
```

A physical-product sale can start in a factory, create a cost-plus intercompany invoice, become inventory in a commercial entity, convert to an external sale and receivable, and finally convert to cash.

## Working Capital schedules

Gross receivables are classified into:

```text
Current
1-30 days overdue
31-60 days overdue
61-90 days overdue
>90 days overdue
```

Gross inventory is classified into:

```text
0-30 days
31-60 days
61-90 days
91-180 days
>180 days
```

The CFO view presents both operational gross exposure and accounting net carrying values. Provision entries do not alter customer collections, inventory movements or supplier-payment behavior.

See `docs/working-capital-schedules.md`.

## Product lifecycle

A subset of the catalog is modeled as legacy generation. The portfolio review engine evaluates trailing profitability every six months.

```text
Active
-> Phase-out approved
-> Phase-out effective
-> Replacement approved
-> Replacement launched
```

The consequences flow into future revenue, margin, Working Capital, factory production and cash rather than being inserted as dashboard annotations.

## Financial controls

Publication is blocked if financial controls fail. The suite requires, among other checks:

- every journal to balance
- total trial balance to equal zero
- every legal balance sheet to balance
- consolidated balance sheet to balance
- legal intercompany AR and AP to reconcile
- cash-flow movement to reconcile to cash
- legal-to-group revenue and EBIT bridges to reconcile
- AR aging and buckets to reconcile to `1100_AR`
- inventory aging and buckets to reconcile to `1200_INVENTORY`
- credit loss allowance to reconcile to `1190_CREDIT_LOSS_ALLOWANCE`
- inventory provision to reconcile to `1290_INVENTORY_PROVISION`
- neither provision to exceed its gross asset
- Software revenue and ARR roll-forward to reconcile
- Events backlog roll-forward to reconcile
- factory utilization to recalculate from production and capacity
- factory absorption schedule to reconcile to `5450_FACTORY_ABSORPTION_VARIANCE`
- actual fixed cost - absorbed fixed cost - absorption variance to equal zero
- Spare Parts installed-base roll-forward to reconcile
- forecast targets to occur strictly after their vintage
- catalog and sold-product breadth thresholds to pass

A failed control raises an exception before deployment.

## Macro and external data

Current preferred live source:

- ECB Data Portal monthly foreign-exchange reference rates

Current deterministic fallback drivers:

- inflation
- industrial activity index
- energy index
- policy interest rate
- FX curves

The source layer is isolated so Eurostat and World Bank data can progressively replace fallback drivers without changing downstream accounting contracts.

## Rolling forecasting

Every close creates a forecast vintage. Historical vintages remain available for accuracy analysis.

The forecast engine:

1. uses only information observable at the vintage date
2. estimates a driver-based baseline from recent actuals
3. applies divisional growth and seasonality
4. calculates historical entity/division bias from realized prior forecasts
5. applies a capped bias correction
6. generates Base, Upside and Downside scenarios
7. stores the vintage for later MAPE and bias evaluation

This enables Actual vs FC-1, FC-3, FC-6 and forecast-bias analysis as monthly closes accumulate.

## CFO application

The GitHub Pages application contains:

- Executive
- Business Drivers
- P&L
- Margin Engine
- Working Capital
- Cash Flow
- Balance Sheet
- Forecast
- Profitability
- Intercompany
- Operations & CAPEX
- Data Journey

`Working Capital` now shows Gross AR -> ECL -> Net AR and Gross Inventory -> Provision -> Net Inventory, while retaining detailed customer and SKU aging.

`Balance Sheet` shows gross-to-net asset bridges and keeps legal provisions separate from the consolidation-only unrealized intercompany markup reserve.

`P&L` identifies factory absorption, inventory-provision movement and expected-credit-loss movement explicitly.

## Repository structure

```text
.github/workflows/       Monthly close, validation and Pages deployment
config/                  Company structure and finance policies
data/processed/          Compact generated reporting outputs committed to Git
data/runtime/            Reproducible transaction and journal detail generated at runtime
docs/                    Architecture and finance documentation
src/enterprise_finance/  Simulation, accounting, reporting, forecasting and schedule engines
tests/                   Financial and technical release controls
web/                     Static CFO application
```

## Run locally

```bash
python -m pip install -e ".[dev]"
pytest
python -m enterprise_finance.cli build --end-month 2026-08
```

To force deterministic fallback macro data:

```bash
python -m enterprise_finance.cli build --end-month 2026-08 --offline-macro
```

If `--end-month` is omitted, the pipeline closes the previous completed calendar month.

## Main generated outputs

```text
data/processed/chart_of_accounts.csv
data/processed/macro.csv
data/processed/products.csv
data/processed/customers.csv
data/processed/operational_sample.csv
data/processed/journal_sample.csv
data/processed/provision_journal.csv
data/processed/legal_pnl.csv
data/processed/management_pnl.csv
data/processed/pnl.csv
data/processed/legal_balance_sheet.csv
data/processed/balance_sheet.csv
data/processed/cash_flow.csv
data/processed/working_capital.csv
data/processed/ar_aging.csv
data/processed/credit_loss_allowance.csv
data/processed/inventory_aging.csv
data/processed/inventory_provision.csv
data/processed/provision_summary.csv
data/processed/software_subscription_summary.csv
data/processed/events_backlog.csv
data/processed/hardware_factory_economics.csv
data/processed/hardware_production_mix.csv
data/processed/spare_parts_economics.csv
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
web/data/manifest.json
```

Full reproducible detail is generated during every build but intentionally excluded from Git history:

```text
data/runtime/operational.csv.gz
data/runtime/journal.csv.gz
```

## Automation

GitHub Actions performs the full close automatically:

1. install the finance engine
2. run tests
3. refresh external macro inputs where available
4. generate rolling operating history
5. create the accounting ledger
6. post factory absorption accounting
7. reconstruct Working Capital schedules
8. calculate and post asset-quality provisions
9. rebuild legal and consolidated financial statements
10. build divisional operating schedules
11. build rolling forecast vintages and accuracy outputs
12. run all release controls
13. generate the CFO analytical dataset
14. commit compact generated outputs
15. publish GitHub Pages

The core project requires no paid database, hosted application server, paid market-data subscription or paid AI API.

## Synthetic data notice

Aureon Systems Group is fictional. Company names, customers, products, transactions and financial results are synthetic. Real public macroeconomic data may be used as external drivers but does not represent the financial performance of any real company.
