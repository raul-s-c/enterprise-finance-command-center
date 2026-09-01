# Enterprise Finance Command Center

Enterprise Finance Command Center is an end-to-end CFO / FP&A portfolio project built around a continuously evolving synthetic multinational company.

The project models economic activity first and derives accounting, financial statements, Working Capital, Treasury, Budget, Forecast and management analytics from the same economic system.

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
Actual P&L / Balance Sheet / Cash Flow
        ->
Working Capital / Asset Quality / Customer Funding / Treasury / CAPEX
        ->
Annual Budget / Rolling Forecast
        ->
Forward Liquidity
        ->
Integrated Forecast P&L / Balance Sheet / Cash Flow
        ->
Capital Allocation Capacity / Management Decisions
        ->
CFO analytics
```

P&L, Balance Sheet and Cash Flow are not independently generated dashboard numbers. They are consequences of connected operating, accounting and financing events.

## Current release: v0.13

Version 0.13 adds an **integrated 12-month three-statement forecast** for Base, Upside and Downside.

The same rolling operating forecast now drives both liquidity and the forward financial statements:

```text
Operating Forecast
-> Revenue / Margin / OPEX
-> AR / Inventory / AP / Contract Liabilities
-> Customer & Supplier Cash
-> Tax / Interest / CAPEX / Debt / RCF
-> Forecast Cash
-> Forecast P&L
-> Forecast Balance Sheet
-> Forecast Cash Flow
```

The Balance Sheet is not forced to balance with a plug. Cash comes from the liquidity model, Working Capital comes from operating drivers, PPE/CIP follows CAPEX, reserves follow explicit policies, debt follows its roll-forward and retained earnings follows forecast Net Income.

Release controls require:

```text
Forecast Assets - Liabilities - Equity = 0
Forecast Cash Flow roll-forward = 0
Forecast EBIT identity = 0
Forecast Net Income identity = 0
Forecast BS Cash - Forecast CF Cash = 0
12 months x 3 scenarios = complete
```

See `docs/integrated-three-statement-forecast.md`.

## Finance scope

The current system includes:

- 236 synthetic product references across a multi-level hierarchy
- six legal entities and two factories
- 36 rolling actual months
- 18 rolling operating forecast months
- 12-month Base / Upside / Downside liquidity forecast
- 12-month Base / Upside / Downside integrated three-statement forecast
- double-entry accounting
- legal and consolidated actual P&L / Balance Sheet / Cash Flow
- intercompany cost-plus manufacturing and eliminations
- legal-entity cash pooling and Treasury IC positions
- debt and maturity schedules
- liquidity headroom and covenant monitoring
- RCF requirement and availability modelling
- downside-protected capital-allocation capacity
- customer-level AR aging and Expected Credit Loss accounting
- SKU-level inventory aging and obsolescence provisions
- supplier-level AP aging, concentration and single-source exposure
- customer advances, contract liabilities, cancellations and refunds
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
- forecast MAPE, bias and economic-scale controls
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

Three trade schedules reconcile to the legal GL:

```text
Customer AR aging   -> 1100_AR
SKU Inventory aging -> 1200_INVENTORY
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

Customer funding is also separate from Revenue:

```text
Trade NWC
= Net AR + Net Inventory - Trade AP

Operating NWC
= Trade NWC - Contract Liabilities
```

See:

- `docs/working-capital-schedules.md`
- `docs/provisions-and-asset-quality.md`
- `docs/supplier-payables-and-concentration.md`
- `docs/contract-liabilities-and-customer-advances.md`

## Treasury and liquidity

Germany (`DE01`) acts as the Treasury hub. Subsidiaries retain configured operating cash minimums; excess liquidity can be swept to HQ and local shortfalls can be funded from HQ through reciprocal Treasury intercompany balances.

The Treasury layer answers:

```text
Where is cash located?
How much cash can be centralized?
Which entities require funding?
What is gross debt and net debt?
When does debt mature?
How much RCF is available?
What is liquidity headroom?
Do leverage and interest-coverage covenants pass?
What does liquidity look like over the next 12 months?
How much capital could be deployed while protecting Downside liquidity?
```

Key controls include:

```text
Group cash before pooling = Group cash after pooling
IC Treasury Receivables = IC Treasury Payables
Debt schedule = 2500_DEBT
Customer cash identity = 0
Supplier cash identity = 0
Forward cash roll-forward = 0
RCF drawn + undrawn = facility limit
Forward liquidity shortfall after RCF = 0
```

See:

- `docs/treasury-and-liquidity.md`
- `docs/liquidity-forecast-and-capital-allocation.md`

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

```text
Actual Factory Fixed Cost
- Standard Fixed Cost Absorbed
= Factory Absorption Variance
```

The variance is posted to the ledger and affects Gross Profit, AP, tax, retained earnings and cash. Operations additionally expose capacity, utilization and production mix.

### Spare Parts

```text
Opening Installed Base
+ Hardware Additions
- Estimated Retirements
= Ending Installed Base
```

Outputs include aftermarket revenue, stock coverage and installed-base economics.

See `docs/divisional-operating-schedules.md` and `docs/factory-absorption-accounting.md`.

## Budget and rolling Forecast

Budget and Forecast are separate finance objects.

Budget 2026, for example, is frozen using an October 2025 approval vintage:

```text
Budget 2026
Vintage: 2025-10
Targets: 2026-01 to 2026-12
```

The planning layer supports:

```text
YTD Actual vs Budget
FY Budget vs Latest Outlook
FY Budget vs FC-1
FY Budget vs FC-3
FY Budget vs FC-6
```

Rolling forecasts are built from monthly Entity / Division totals, de-seasonalized recent run-rate, structural growth, target-month seasonality and capped historical bias correction. A dedicated economic-scale control prevents internally consistent but implausibly small or large forecasts.

The same forecast vintages feed the P&L outlook, liquidity outlook and integrated three-statement forecast. There is one operating forecast, not three disconnected planning systems.

See:

- `docs/budget-and-fy-planning.md`
- `docs/v0.9.1-forecast-hotfix.md`
- `docs/liquidity-forecast-and-capital-allocation.md`
- `docs/integrated-three-statement-forecast.md`

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

The P&L, Balance Sheet and Cash Flow pages now combine actual reporting with the Base forward statement. Plan & Forecast compares the Base, Upside and Downside three-statement consequences.

The application is static and reads compact JSON generated by the finance engine.

## Release controls

Deployment is blocked if material controls fail. The suite includes:

- journal and trial-balance integrity
- legal and consolidated actual Balance Sheet equations
- actual cash-flow reconciliation
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
- customer-advance and refund journal balancing
- contract-aware AR to account 1100
- no stale customer advances beyond the refund grace period
- forecast no-lookahead and economic-scale plausibility
- frozen Budget no-hindsight and 12-month coverage
- liquidity customer/supplier cash identities
- liquidity cash roll-forward
- RCF identity and facility-limit control
- complete Base / Upside / Downside liquidity coverage
- forward liquidity-shortfall detection
- forecast Balance Sheet equation
- forecast Cash Flow roll-forward
- forecast EBIT and Net Income identities
- forecast Balance Sheet / Cash Flow cash link
- complete Base / Upside / Downside three-statement coverage

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
data/processed/liquidity_forecast.csv
data/processed/liquidity_forecast_summary.csv
data/processed/capital_allocation_capacity.csv
data/processed/forecast_pnl.csv
data/processed/forecast_balance_sheet.csv
data/processed/forecast_cash_flow.csv
data/processed/three_statement_forecast_summary.csv
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
4. simulate operating activity
5. create the legal ledger
6. post factory absorption and provisions
7. rebuild customer settlement, advances and contract liabilities
8. reconstruct AR / Inventory / AP schedules
9. build Budget and rolling forecast vintages
10. apply legal-entity cash pooling
11. rebuild actual Balance Sheet and Cash Flow after pooling
12. build debt, maturity, liquidity and covenant schedules
13. build the 12-month scenario liquidity forecast
14. calculate downside-protected capital-allocation capacity
15. build the integrated three-statement forecast
16. run release controls
17. publish compact CFO datasets
18. commit generated outputs
19. deploy GitHub Pages

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
