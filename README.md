# Enterprise Finance Command Center

Enterprise Finance Command Center is an end-to-end CFO / FP&A portfolio project built around a continuously evolving synthetic multinational company.

The project does not generate disconnected dashboard numbers. It models economic activity first, translates that activity into double-entry accounting, consolidates legal entities, derives connected financial statements, builds management schedules, creates Budget and rolling Forecast versions, and publishes a CFO-oriented analytical application.

Live application: https://raul-s-c.github.io/enterprise-finance-command-center/

## Synthetic group

The fictional company is **Aureon Systems Group**.

It combines four deliberately different business models:

- Software: recurring subscriptions and services
- Hardware: manufactured products sold through commercial entities
- Events & Projects: project-based revenue and backlog
- Spare Parts: high-SKU aftermarket activity linked to installed base

The group has legal entities in Germany, Spain, Czech Republic, China, the United States and Japan. Brno and Suzhou operate manufacturing sites and supply commercial entities through cost-plus intercompany flows.

## Core architecture

```text
Public macro drivers
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
Working Capital / Asset Quality / CAPEX
        ->
Divisional operating schedules
        ->
Annual Budget / Rolling Forecast
        ->
Management decisions
        ->
CFO analytics
```

P&L, Balance Sheet, Cash Flow, Working Capital, provisions, factory economics, Budget and Forecast all originate from the same economic system.

## Current release: v0.9

Version 0.9 adds a frozen Annual Budget and full-year planning layer.

The current system includes:

- 236 synthetic product references
- 19 division/family combinations
- four business models
- six legal entities
- two factories
- 36 rolling actual months
- 18 forecast months
- double-entry accounting
- legal and consolidated financial statements
- Annual Budget with prior-year approval vintage
- YTD Actual vs Budget
- FY Budget vs Latest Outlook
- FC-1 / FC-3 / FC-6 full-year outlook reconstruction
- customer-level AR aging
- expected credit loss accounting
- SKU-level inventory aging
- inventory obsolescence provisions
- supplier-level AP aging
- supplier concentration and single-source exposure
- Software ARR / MRR / churn / NRR
- Events bookings / backlog / book-to-bill
- Hardware capacity / utilization / absorption accounting
- Spare Parts installed-base economics
- CAPEX projects from CIP through go-live and depreciation
- product and customer profitability
- price / volume / mix analysis
- product lifecycle decisions
- automated GitHub Actions close and GitHub Pages deployment

## Product hierarchy

```text
Division
  -> Product Family
      -> Product Subfamily
          -> Product Type
              -> Quality Tier
                  -> SKU / Generation
```

Commercial tiers are typically Essential, Professional and Premium. Customers receive deterministic partial assortments rather than an artificial customer x SKU Cartesian product.

See `docs/product-hierarchy.md`.

## Working Capital and asset quality

The project contains three reconciled operating schedules:

```text
Customer AR aging   -> 1100_AR
SKU inventory aging -> 1200_INVENTORY
Supplier AP aging   -> 2100_AP
```

### Trade receivables

```text
Gross Trade Receivables
- Credit Loss Allowance
= Net Trade Receivables
```

The ECL model uses customer risk and aging buckets.

### Inventory

```text
Gross Legal Inventory
- Inventory Provision
- Unrealized Intercompany Markup Reserve
= Net Consolidated Inventory
```

Inventory provision depends on age, product generation, quality tier and business model.

### Accounts Payable

Supplier lots are reconstructed from the legal AP ledger. The schedule adds:

- AP aging
- payment terms
- supplier criticality
- trailing-12-month supplier spend
- Top-5 concentration
- single-source exposure
- overdue supplier exposure

See:

- `docs/working-capital-schedules.md`
- `docs/provisions-and-asset-quality.md`
- `docs/supplier-payables-and-concentration.md`

## Factory absorption accounting

Brno and Suzhou use explicit absorption accounting.

```text
Actual Factory Fixed Cost
- Standard Fixed Cost Absorbed
= Factory Absorption Variance
```

Account:

```text
5450_FACTORY_ABSORPTION_VARIANCE
```

The variance flows through Gross Profit, AP, cash, tax and retained earnings.

See `docs/factory-absorption-accounting.md`.

## Divisional operating schedules

The divisions do not share an artificial generic KPI framework.

### Software

```text
Opening MRR
+ New MRR
+ Expansion MRR
- Contraction MRR
- Churn MRR
= Ending MRR
```

Outputs include ARR, NRR, GRR and recurring-revenue mix.

### Events & Projects

```text
Opening Backlog
+ Bookings
- Recognized Revenue
= Ending Backlog
```

Outputs include backlog, book-to-bill and project volume.

### Hardware

Outputs include capacity, utilization, production mix, absorbed fixed cost and under/over-absorption.

### Spare Parts

```text
Opening Installed Base
+ Hardware Additions
- Estimated Retirements
= Ending Installed Base
```

Outputs include aftermarket revenue, inventory coverage and installed-base economics.

See `docs/divisional-operating-schedules.md`.

## Annual Budget and FY planning

The Annual Budget is intentionally separate from the rolling Forecast.

Budget 2026, for example, is approved using an October 2025 planning vintage.

```text
Budget 2026
Vintage: 2025-10
Targets: 2026-01 to 2026-12
```

No actual information after the budget vintage may change the frozen plan.

Commercial combinations use:

```text
Trailing observable revenue run-rate
x structural growth
x management stretch
x monthly phasing
= Revenue Budget
```

Factories and other zero-revenue cost centers use a separate cost-based planning model.

The Plan & Forecast layer provides:

```text
YTD Actual vs Budget
FY Budget vs Latest Outlook
FY Budget vs FC-1
FY Budget vs FC-3
FY Budget vs FC-6
```

FY outlook combines closed actual months with the remaining months from the selected forecast vintage. Depreciation is included before calculating forecast EBIT.

See `docs/budget-and-fy-planning.md`.

## Rolling forecasting

Every monthly close creates a forecast vintage.

The forecast engine:

1. uses only information observable at the vintage date
2. builds an entity/division baseline from recent actuals
3. applies structural growth and seasonality
4. calculates historical forecast bias
5. applies capped bias correction
6. generates Base, Upside and Downside scenarios
7. preserves historical vintages for accuracy analysis

This supports FC-1, FC-3, FC-6, MAPE and bias analysis.

## CFO application

The GitHub Pages application contains:

- Executive
- Business Drivers
- P&L
- Margin Engine
- Working Capital
- Cash Flow
- Balance Sheet
- Plan & Forecast
- Profitability
- Intercompany
- Operations & CAPEX
- Data Journey

The application is static and reads compact JSON generated by the finance engine.

## Release controls

Deployment is blocked if material controls fail.

The suite includes:

- journal balance
- trial balance
- legal Balance Sheet equation
- consolidated Balance Sheet equation
- cash-flow reconciliation
- intercompany AR/AP reconciliation
- consolidation revenue and EBIT bridges
- AR aging to GL
- inventory aging to GL
- AP aging to GL
- ECL allowance to contra-asset account
- inventory provision to contra-asset account
- factory absorption schedule to ledger
- Software ARR roll-forward
- Events backlog roll-forward
- Spare Parts installed-base roll-forward
- forecast no-lookahead
- product-catalog breadth
- frozen Budget no-hindsight
- 12-month Budget coverage
- Budget duplicate detection
- current-year Budget presence
- FY plan bridge presence

A failed control raises an exception before deployment.

## Main generated outputs

```text
data/processed/legal_pnl.csv
data/processed/management_pnl.csv
data/processed/balance_sheet.csv
data/processed/cash_flow.csv
data/processed/working_capital.csv
data/processed/ar_aging.csv
data/processed/credit_loss_allowance.csv
data/processed/inventory_aging.csv
data/processed/inventory_provision.csv
data/processed/ap_aging.csv
data/processed/supplier_concentration.csv
data/processed/software_subscription_summary.csv
data/processed/events_backlog.csv
data/processed/hardware_factory_economics.csv
data/processed/spare_parts_economics.csv
data/processed/annual_budget.csv
data/processed/budget_performance.csv
data/processed/fy_plan_bridge.csv
data/processed/forecast_vintages.csv
data/processed/forecast_accuracy.csv
data/processed/validation.json
web/data/dashboard.json
web/data/manifest.json
```

Full reproducible operating and journal detail is generated at runtime and intentionally excluded from Git history.

## Automation

GitHub Actions performs the complete close automatically:

1. install the finance engine
2. run tests
3. refresh macro inputs where available
4. generate operating history
5. create the ledger
6. post factory absorption
7. reconstruct Working Capital schedules
8. calculate asset-quality provisions
9. consolidate financial statements
10. build divisional schedules
11. build the frozen Annual Budget where applicable
12. build forecast vintages and FY outlooks
13. run release controls
14. generate the CFO dataset
15. commit compact outputs
16. deploy GitHub Pages

No paid database, application server, LLM API or paid market-data subscription is required.

## Run locally

```bash
python -m pip install -e ".[dev]"
pytest
python -m enterprise_finance.cli build --end-month 2026-08
```

To disable live macro retrieval:

```bash
python -m enterprise_finance.cli build --end-month 2026-08 --offline-macro
```

## Synthetic data notice

Aureon Systems Group is fictional. Company names, customers, suppliers, products, transactions and financial results are synthetic. Real public macroeconomic data may be used as external drivers but does not represent the financial performance of any real company.
