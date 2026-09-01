# Enterprise Finance Command Center

Enterprise Finance Command Center is an end-to-end CFO / FP&A portfolio project built around a continuously evolving synthetic multinational company.

The project models economic activity first and derives accounting, financial statements, Working Capital, Treasury, operating schedules, Budget, Forecast and management analytics from the same economic system.

Live application: https://raul-s-c.github.io/enterprise-finance-command-center/

## Synthetic group

The fictional company is **Aureon Systems Group** with four deliberately different business models:

- Software — recurring subscriptions and services
- Hardware — manufactured products and factory economics
- Events & Projects — bookings, backlog and project delivery
- Spare Parts — high-SKU aftermarket activity linked to installed base

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
Working Capital / Asset Quality / Customer Funding / Treasury / CAPEX
        ->
Divisional operating schedules
        ->
Annual Budget / Rolling Forecast
        ->
Management decisions
        ->
CFO analytics
```

The project does not independently generate P&L, Balance Sheet and Cash Flow numbers for a dashboard. Those outputs are consequences of the same underlying transactions and accounting events.

## Current release: v0.11

Version 0.11 adds **Treasury & Liquidity** to the existing finance operating system.

The Treasury layer works on the legal ledger after the complete v0.10 close. Subsidiaries retain configured minimum operating cash balances while excess liquidity is concentrated at German HQ through a deterministic cash pool.

```text
Subsidiary surplus sweep
Dr IC Treasury Receivable
Cr Cash

HQ receipt
Dr Cash
Cr IC Treasury Payable
```

If a subsidiary falls below its configured minimum cash, HQ funds the legal entity using the reciprocal entries.

Treasury introduces:

```text
1160_IC_TREASURY_RECEIVABLE
2160_IC_TREASURY_PAYABLE
```

The balances are legal-entity positions and eliminate in consolidation. Cash pooling must never change consolidated cash.

Version 0.11 also adds:

- cash by legal entity after pooling
- minimum operating cash policy
- debt schedule reconciled to `2500_DEBT`
- contractual debt maturities
- debt maturity ladder
- TTM EBITDA
- TTM interest
- Net Debt / EBITDA
- interest coverage
- revolving-credit-facility headroom
- liquidity headroom
- covenant monitoring

See `docs/treasury-and-liquidity.md`.

## Finance scope

The current system includes:

- 236 synthetic product references across a multi-level hierarchy
- six legal entities and two factories
- 36 rolling actual months
- 18 forecast months
- double-entry accounting
- legal and consolidated P&L / Balance Sheet / Cash Flow
- intercompany cost-plus manufacturing and eliminations
- legal-entity cash pooling and Treasury IC positions
- debt and liquidity schedules
- customer-level AR aging
- expected credit loss accounting
- SKU-level inventory aging and obsolescence provisions
- supplier-level AP aging, concentration and single-source exposure
- customer advances and contract liabilities
- contract cancellations and cash refunds
- factory capacity and absorption accounting
- CAPEX from CIP through go-live, PPE and depreciation
- Software ARR / MRR / churn / NRR
- Events bookings / backlog / book-to-bill
- Spare Parts installed-base economics
- product, family, quality-tier and customer profitability
- price / volume / mix analysis
- deterministic product lifecycle decisions
- frozen Annual Budget
- YTD Actual vs Budget
- FY Budget vs Latest Outlook
- FC-1 / FC-3 / FC-6 outlook reconstruction
- Base / Upside / Downside rolling forecasts
- forecast MAPE, bias and scale controls
- automated monthly close and GitHub Pages deployment

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

## Working Capital and customer funding

The project contains three reconciled trade schedules:

```text
Customer AR aging   -> 1100_AR
SKU inventory aging -> 1200_INVENTORY
Supplier AP aging   -> 2100_AP
```

Asset valuation is separated from operating exposure:

```text
Gross Trade Receivables
- Expected Credit Loss Allowance
= Net Trade Receivables

Gross Legal Inventory
- Inventory Provision
- Unrealized Intercompany Markup Reserve
= Net Consolidated Inventory
```

Customer funding is treated separately from revenue:

```text
Trade NWC
= Net AR + Net Inventory - Trade AP

Operating NWC
= Trade NWC - Contract Liabilities
```

This lets the CFO distinguish slow cash conversion from a business model that is partially funded by customer prepayments.

See:

- `docs/working-capital-schedules.md`
- `docs/provisions-and-asset-quality.md`
- `docs/supplier-payables-and-concentration.md`
- `docs/contract-liabilities-and-customer-advances.md`

## Treasury and liquidity

Cash pooling is a legal-entity financing process, not a change to group cash.

The group Treasury view answers:

```text
Where is cash located?
How much can be centralized?
Which entities require liquidity support?
What is gross debt and net debt?
When does debt mature?
How much RCF remains available?
What is the liquidity headroom?
Do leverage and interest-coverage covenants pass?
```

Release controls require:

```text
Group cash before pooling = Group cash after pooling
IC Treasury Receivables = IC Treasury Payables
Debt schedule = 2500_DEBT
Legal Balance Sheets remain balanced
Consolidated Balance Sheet remains balanced
Subsidiaries remain above minimum operating cash
```

See `docs/treasury-and-liquidity.md`.

## Divisional operating schedules

The four divisions deliberately use different operating mathematics.

### Software

```text
Opening MRR
+ New MRR
+ Expansion MRR
- Contraction MRR
- Churn MRR
= Ending MRR
```

Outputs include ARR, NRR, GRR, recurring mix and customer prepayments.

### Events & Projects

```text
Opening Backlog
+ Bookings
- Recognized Revenue
= Ending Backlog
```

Outputs include book-to-bill, backlog coverage and project advances.

### Hardware

Outputs include capacity, utilization, production mix, fixed-cost absorption and under/over-absorption.

```text
Actual Factory Fixed Cost
- Standard Fixed Cost Absorbed
= Factory Absorption Variance
```

The variance is posted to the ledger and affects Gross Profit, AP, tax, retained earnings and cash.

### Spare Parts

```text
Opening Installed Base
+ Hardware Additions
- Estimated Retirements
= Ending Installed Base
```

Outputs include aftermarket revenue, inventory coverage and installed-base economics.

See `docs/divisional-operating-schedules.md` and `docs/factory-absorption-accounting.md`.

## Annual Budget and rolling Forecast

Budget and Forecast are different finance objects.

Budget 2026, for example, is approved from an October 2025 planning vintage and is frozen against hindsight.

```text
Budget 2026
Vintage: 2025-10
Targets: 2026-01 to 2026-12
```

The Plan & Forecast layer provides:

```text
YTD Actual vs Budget
FY Budget vs Latest Outlook
FY Budget vs FC-1
FY Budget vs FC-3
FY Budget vs FC-6
```

Forecasts are based on monthly Entity / Division totals, de-seasonalized recent run-rate, structural growth, target-month seasonality and capped historical bias correction.

A dedicated economic-scale control blocks forecasts that are internally consistent but implausibly small or large relative to the recent business run-rate.

See `docs/budget-and-fy-planning.md` and `docs/v0.9.1-forecast-hotfix.md`.

## CFO application

The GitHub Pages application contains:

- Executive
- Business Drivers
- P&L
- Margin Engine
- Working Capital
- Cash Flow
- Treasury
- Balance Sheet
- Plan & Forecast
- Profitability
- Intercompany
- Operations & CAPEX
- Data Journey

The application is static and reads compact JSON generated by the finance engine.

## Release controls

Deployment is blocked if material controls fail. The suite includes:

- journal and trial-balance integrity
- legal and consolidated Balance Sheet equations
- cash-flow reconciliation
- intercompany AR/AP and consolidation bridges
- Treasury IC receivable/payable reconciliation
- cash-pool zero-sum control
- debt schedule to GL reconciliation
- subsidiary minimum-cash control
- AR, inventory and AP subledger reconciliation
- ECL and inventory-provision reconciliation
- factory absorption schedule to ledger
- Software ARR, Events backlog and Spare Parts installed-base roll-forwards
- contract-liability subledger to account 2300
- customer-advance journal balancing
- contract-aware AR to account 1100
- no stale customer advances beyond the refund grace period
- customer-refund journal balancing
- forecast no-lookahead and economic-scale plausibility
- product-catalog breadth
- frozen Budget no-hindsight and 12-month coverage
- current-year Budget and FY planning bridge presence

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
data/processed/contract_liabilities.csv
data/processed/customer_advances.csv
data/processed/contract_liability_summary.csv
data/processed/treasury_cash_pool.csv
data/processed/treasury_entity_cash.csv
data/processed/debt_schedule.csv
data/processed/debt_maturity_ladder.csv
data/processed/liquidity_covenants.csv
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

GitHub Actions performs the close automatically:

1. install the finance engine
2. run tests
3. refresh macro inputs where available
4. simulate operating activity
5. create the legal ledger
6. post factory absorption and provisions
7. rebuild customer settlement, advances and contract liabilities
8. reconstruct AR / Inventory / AP schedules
9. build Budget and forecast vintages
10. apply legal-entity cash pooling
11. rebuild Balance Sheet and Cash Flow after pooling
12. build debt, maturity, liquidity and covenant schedules
13. run release controls
14. publish compact CFO datasets
15. commit generated outputs
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
