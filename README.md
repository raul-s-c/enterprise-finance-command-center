# Enterprise Finance Command Center

Enterprise Finance Command Center is an end-to-end CFO analytics project built around a continuously evolving synthetic multinational company.

The project does not generate disconnected dashboard numbers. It models economic activity first, translates that activity into double-entry accounting, consolidates legal entities, derives connected financial statements, creates rolling forecasts and publishes a CFO-oriented analytical application.

The synthetic group is **Aureon Systems Group**. It operates four deliberately different business models:

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
Working-capital schedules / CAPEX / Profitability
        ->
Divisional operating schedules
        ->
Rolling forecast
        ->
Management decisions
        ->
CFO analytics
```

P&L, balance sheet, cash flow, Working Capital and business-driver analytics all originate from the same economic system. They are not independently generated dashboard series.

## Current release: v0.5

Version 0.5 adds business-model-specific operating schedules behind the financial statements.

The current project contains:

- 236 synthetic product references across four asymmetric divisions
- six legal entities
- four management divisions
- 36 rolling actual months
- 18 forecast months
- double-entry accounting
- legal and consolidated statements
- customer-level AR aging
- SKU-level analytical inventory aging
- Working Capital schedule-to-GL reconciliation
- Software ARR and retention schedules
- Events bookings and backlog schedules
- Hardware factory-capacity and absorption schedules
- Spare Parts installed-base and aftermarket schedules
- historical forecast vintages
- product lifecycle decisions
- automated monthly publication through GitHub Actions and GitHub Pages

## Product hierarchy

The commercial catalog uses the following structure:

```text
Division
  -> Product Family
      -> Product Subfamily
          -> Product Type
              -> Quality Tier
                  -> SKU / Generation
```

Each product type normally has Essential, Professional and Premium commercial tiers. Quality tier changes price, cost, expected demand, selling-cost intensity and customer penetration.

The four catalogs are intentionally different:

- Software: Platform, Security, Analytics and Automation
- Hardware: Control Systems, Edge Appliances, Terminals, Network Devices and Sensors & Readers
- Events & Projects: Deployment & Integration, Training & Enablement, Customer Experience and Managed Programs
- Spare Parts: Control Modules, Maintenance Kits, Interface Components, Mechanical Parts, Security Components and Consumables

Customers do not buy every SKU. Each customer receives a deterministic partial assortment based on customer size, segment, division and quality tier. This avoids a fake customer x SKU Cartesian dataset while retaining enough complexity for mix, profitability, inventory and portfolio analysis.

See `docs/product-hierarchy.md`.

## Divisional operating schedules

The four divisions do not share an artificial generic KPI layer.

### Software

The Software schedule separates recurring and services revenue and creates a customer-product recurring-revenue roll-forward:

```text
Opening MRR
+ New MRR
+ Expansion MRR
- Contraction MRR
- Churn MRR
= Ending MRR
```

It calculates MRR, ARR, New ARR, Expansion ARR, Contraction ARR, Churn ARR, NRR, GRR and recurring revenue mix. The complete schedule must reconcile to Software operating revenue.

### Events & Projects

Events is treated as a project business:

```text
Opening Backlog
+ Bookings
- Recognized Revenue
= Ending Backlog
```

The schedule calculates bookings, recognized revenue, ending backlog, book-to-bill, backlog coverage and project units. The backlog roll-forward is a hard release control.

### Hardware

Hardware exposes manufacturing economics for Brno and Suzhou:

- produced units
- available capacity
- utilization
- capacity headroom
- fixed factory cost
- absorbed fixed cost
- under-absorption
- fixed cost per produced unit
- production mix by family and quality tier

Factory utilization is independently recalculated from produced units and capacity. A future accounting release will post explicit absorption and under-absorption entries so this schedule also becomes a direct P&L bridge.

### Spare Parts

Aftermarket demand is linked to the installed base created by historical Hardware sales:

```text
Opening Installed Base
+ Hardware Additions
- Estimated Retirements
= Ending Installed Base
```

The schedule calculates installed base, aftermarket revenue, revenue per installed unit, active SKUs, inventory coverage and inventory health using the reconciled inventory-aging schedule.

See `docs/divisional-operating-schedules.md`.

## Finance engine

The finance engine includes:

- deterministic synthetic economic activity
- public ECB FX integration with fallback data
- customer-product operating activity
- sparse commercial assortments
- double-entry journals
- monthly P&L closing to retained earnings
- legal-entity P&L
- legal-entity balance sheets
- consolidated management P&L
- connected cash flow
- AR, AP and inventory mechanics
- DSO, DPO and DIO
- customer-level AR aging
- inventory aging by entity, division, family and SKU
- cost-plus intercompany manufacturing flows
- reciprocal intercompany AR/AP and settlements
- transfer-pricing consolidation bridge
- unrealized intercompany markup reserve in inventory
- CAPEX project lifecycle from CIP to go-live, PPE and depreciation
- factory capacity and utilization
- debt, interest, income-tax accruals and quarterly payments
- product, family, quality-tier and customer profitability
- price / volume / mix analysis
- deterministic portfolio reviews
- product phase-out and replacement launch events
- rolling forecast vintages
- Base, Upside and Downside scenarios
- forecast accuracy and bias
- procedural CFO commentary
- automated financial release controls

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

A physical-product sale can therefore start with manufacturing in China or Czech Republic, create an intercompany cost-plus invoice, create inventory in a commercial entity, become an external customer sale, create receivables and finally convert to cash.

## Working Capital schedules

Detailed management schedules remain constrained by the legal ledger.

### Accounts Receivable

Sales create customer invoices in `1100_AR`. Collections credit the same account. The AR schedule reconstructs open customer balances and distributes them into:

```text
Current
1-30 days overdue
31-60 days overdue
61-90 days overdue
>90 days overdue
```

Every month/entity/division schedule must reconcile to `1100_AR`.

### Inventory

Closing GL inventory is analytically distributed across the physical SKU hierarchy and classified into:

```text
0-30 days
31-60 days
61-90 days
91-180 days
>180 days
```

The model calculates SKU months of coverage, slow-moving inventory and obsolescence-risk exposure. Every month/entity/division schedule must reconcile to `1200_INVENTORY`.

The current release treats obsolescence as a management risk indicator. It does not yet post an inventory provision to the P&L.

See `docs/working-capital-schedules.md`.

## Product lifecycle

A subset of the catalog is deliberately modeled as legacy generation. Those products have weaker economics and defined NextGen successors.

The portfolio review engine evaluates trailing profitability every six months. Products can move through:

```text
Active
-> Phase-out approved
-> Phase-out effective
-> Replacement approved
-> Replacement launched
```

The successor changes cost structure, demand and strategic role. The financial effects therefore flow through future revenue, margin, Working Capital, factory production and cash rather than being inserted as dashboard annotations.

## Financial controls

Publication is blocked if financial controls fail.

The validation suite currently requires:

- every journal to balance
- total trial balance to equal zero
- every legal balance sheet to balance
- legal intercompany AR and AP to reconcile
- consolidated balance sheet to balance
- cash-flow movement to reconcile to balance-sheet cash
- legal-to-group revenue bridge to reconcile
- legal-to-group EBIT bridge to reconcile
- AR aging schedule to reconcile to `1100_AR`
- AR aging buckets to reconcile to AR schedule total
- inventory schedule to reconcile to `1200_INVENTORY`
- inventory aging buckets to reconcile to inventory schedule total
- Software revenue schedule to reconcile to operating revenue
- Software ARR roll-forward to reconcile
- Events backlog roll-forward to reconcile
- factory utilization to recalculate from production and capacity
- Spare Parts installed-base roll-forward to reconcile
- forecast targets to occur strictly after their forecast vintage
- catalog breadth to remain above the product-complexity threshold
- a sufficiently broad share of the catalog to appear in actual activity

A failed control raises an exception before deployment.

## Macro and external data

The pipeline remains reproducible when an external source is unavailable.

Current preferred live source:

- ECB Data Portal monthly foreign-exchange reference rates

Current deterministic fallback drivers:

- inflation
- industrial activity index
- energy index
- policy interest rate
- FX curves

The source layer is isolated from the finance engine. Eurostat industrial production, Eurostat HICP and World Bank commodity data can replace fallback drivers without changing downstream accounting or reporting logic.

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

`Business Drivers` contains separate Software, Events, Hardware and Spare Parts economics rather than forcing them into one common operating model.

`Working Capital` includes AR aging, overdue-customer concentration, inventory aging, family-level inventory exposure and a SKU inventory watchlist.

`Profitability` includes family economics, quality-tier economics, detailed SKU profitability, catalog structure and customer profitability.

## Repository structure

```text
.github/workflows/       Monthly close, validation and Pages deployment
config/                  Company structure and finance assumptions
data/processed/          Compact generated reporting outputs committed to Git
data/runtime/            Reproducible full transaction detail generated at runtime
docs/                    Architecture, finance model and data contracts
src/enterprise_finance/  Simulation, accounting, reporting, forecasting and schedule engines
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

Compact, auditable outputs committed to Git include:

```text
data/processed/chart_of_accounts.csv
data/processed/macro.csv
data/processed/products.csv
data/processed/customers.csv
data/processed/operational_sample.csv
data/processed/portfolio_events.csv
data/processed/journal_sample.csv
data/processed/legal_pnl.csv
data/processed/management_pnl.csv
data/processed/pnl.csv
data/processed/legal_balance_sheet.csv
data/processed/balance_sheet.csv
data/processed/cash_flow.csv
data/processed/working_capital.csv
data/processed/ar_aging.csv
data/processed/inventory_aging.csv
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
```

Full reproducible detail is generated during every build but intentionally excluded from Git history:

```text
data/runtime/operational.csv.gz
data/runtime/journal.csv.gz
```

This keeps the repository sustainable over years of monthly closes while preserving the ability to regenerate complete transaction and accounting detail from code, configuration, seed and macro inputs.

## Automation

GitHub Actions performs the full close automatically:

1. install the finance engine
2. run tests
3. refresh external macro inputs where available
4. generate the rolling operating history
5. create the accounting ledger
6. consolidate financial statements
7. reconstruct and validate Working Capital schedules
8. build and validate divisional operating schedules
9. build rolling forecast vintages and accuracy outputs
10. generate the CFO analytical dataset
11. commit compact generated outputs
12. publish GitHub Pages

The core project requires no paid database, hosted application server, paid market-data subscription or paid AI API.

## Synthetic data notice

Aureon Systems Group is fictional. Company names, customers, products, transactions and financial results are synthetic. Real public macroeconomic data may be used as external drivers but does not represent the financial performance of any real company.
