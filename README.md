# Enterprise Finance Command Center

Enterprise Finance Command Center is an end-to-end CFO / FP&A portfolio project built around a continuously evolving synthetic multinational company.

The project models economic activity first and derives accounting, financial statements, Working Capital, Treasury, Budget, Forecast, Workforce economics and management analytics from the same system.

Live application: https://raul-s-c.github.io/enterprise-finance-command-center/

## Synthetic group

The fictional company is **Aureon Systems Group** with four deliberately different business models:

- Software — recurring subscriptions and services
- Hardware — manufactured products and factory economics
- Events & Projects — bookings, backlog and project delivery
- Spare Parts — high-SKU aftermarket activity linked to installed base

The group has legal entities in Germany, Spain, Czech Republic, China, the United States and Japan. Brno and Suzhou operate manufacturing sites and supply commercial entities through cost-plus intercompany flows.

## Design principle

```text
Public macro drivers
-> Business drivers
-> Operating events
-> Double-entry ledger
-> Legal-entity financials
-> Intercompany consolidation
-> Actual P&L / Balance Sheet / Cash Flow
-> Working Capital / Asset Quality / Customer Funding / Treasury / CAPEX
-> Workforce Cost Planning
-> Annual Budget / Rolling Forecast
-> Forward Liquidity
-> Integrated Forecast P&L / Balance Sheet / Cash Flow
-> Capital Allocation Capacity / Management Decisions
-> CFO analytics
```

P&L, Balance Sheet and Cash Flow are not independently generated dashboard numbers. They are consequences of connected operating, accounting and financing events.

## Current release: v0.14

Version 0.14 adds **Workforce Cost Planning** and removes a major simplification from earlier releases: OPEX is no longer treated as a single percentage of Revenue.

Workforce is modeled only at:

```text
Month × Legal Entity × Division × Function
```

There are no fake employees or synthetic HR records.

The core Workforce roll-forward is:

```text
Opening FTE
- Attrition
+ Hires
= Ending FTE
```

Target FTE responds to lagged business demand and productivity. The model also includes wage inflation, fully loaded employment cost, recruitment cost and Revenue/FTE.

Actual OPEX is split into:

```text
Personnel Cost
+ Non-People OPEX
= Total OPEX
```

Payroll is paid directly through cash:

```text
Dr 6000_OPEX
Cr 1000_CASH
```

It never creates Trade AP. Supplier payments and DPO therefore continue to represent external suppliers only.

The rolling forecast now projects FTE, hires, attrition, personnel cost and non-people OPEX. The liquidity forecast consumes payroll as a separate cash outflow and the integrated three-statement forecast is rebuilt from that payroll-aware liquidity model.

Release validation completed with:

```text
35 / 35 tests passed
36 rolling actual months
18 rolling operating forecast months
59,681 operating records
601,025 journal lines
validation_passed=True
```

See `docs/workforce-cost-planning.md`.

## Finance scope

The current system includes:

- 236 synthetic product references across a multi-level hierarchy
- six legal entities and two factories
- 36 rolling actual months
- 18 rolling operating forecast months
- double-entry accounting
- legal and consolidated P&L / Balance Sheet / Cash Flow
- Workforce capacity, payroll, hiring, attrition and productivity
- product/customer Workforce-cost allocation for profitability
- intercompany cost-plus manufacturing and eliminations
- legal-entity cash pooling and Treasury IC positions
- debt and maturity schedules
- liquidity headroom and covenant monitoring
- 12-month Base / Upside / Downside liquidity forecast
- downside-protected capital-allocation capacity
- 12-month Base / Upside / Downside integrated three-statement forecast
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
- forecast MAPE, bias, no-lookahead and economic-scale controls
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

Customers receive deterministic partial assortments rather than an artificial customer × SKU Cartesian product.

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

Customer funding is separate from Revenue:

```text
Trade NWC
= Net AR + Net Inventory - Trade AP

Operating NWC
= Trade NWC - Contract Liabilities
```

See `docs/working-capital-schedules.md`, `docs/provisions-and-asset-quality.md`, `docs/supplier-payables-and-concentration.md` and `docs/contract-liabilities-and-customer-advances.md`.

## Treasury and forward liquidity

Germany (`DE01`) is the Treasury hub. Subsidiaries retain configured operating cash minimums; excess liquidity can be swept to HQ and local shortfalls can be funded through reciprocal Treasury intercompany balances.

The model covers:

```text
Cash location
Cash pooling
Gross Debt / Net Debt
Debt maturity
RCF availability
Liquidity headroom
Net leverage
Interest coverage
Covenants
12-month scenario liquidity
Downside-protected allocation capacity
```

The forward cash model derives AR, Inventory, AP and Contract Liabilities from operating drivers before calculating collections, supplier cash, payroll, tax, interest, CAPEX, debt repayment and RCF requirement.

See `docs/treasury-and-liquidity.md` and `docs/liquidity-forecast-and-capital-allocation.md`.

## Integrated three-statement forecast

One operating forecast drives all three statements:

```text
Operating Forecast
-> Revenue / Margin / Workforce OPEX
-> AR / Inventory / AP / Contract Liabilities
-> Customer / Supplier / Payroll Cash
-> Tax / Interest / CAPEX / Debt / RCF
-> Forecast Cash
-> Forecast P&L
-> Forecast Balance Sheet
-> Forecast Cash Flow
```

The Balance Sheet is not forced with a balancing plug. Cash comes from the liquidity model, Working Capital from operating drivers, PPE/CIP from CAPEX, reserves from explicit policies, debt from its roll-forward and retained earnings from forecast Net Income.

Forward monetary state is materialized at cent precision.

See `docs/integrated-three-statement-forecast.md`.

## Divisional operating models

The four divisions intentionally use different economics.

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

The variance is posted to the ledger and affects Gross Profit, AP, tax, retained earnings and cash.

### Spare Parts

```text
Opening Installed Base
+ Hardware Additions
- Estimated Retirements
= Ending Installed Base
```

See `docs/divisional-operating-schedules.md` and `docs/factory-absorption-accounting.md`.

## Budget and rolling Forecast

Budget and Forecast are different finance objects.

Budget is frozen using the information available at its approval vintage; later actuals cannot rewrite it. Rolling forecast vintages preserve FC-1 / FC-3 / FC-6 reconstruction and include historical bias correction without look-ahead.

Planning supports:

```text
YTD Actual vs Budget
FY Budget vs Latest Outlook
FY Budget vs FC-1
FY Budget vs FC-3
FY Budget vs FC-6
Forecast accuracy / bias
```

See `docs/budget-and-fy-planning.md` and `docs/v0.9.1-forecast-hotfix.md`.

## CFO application

The GitHub Pages application includes:

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

Workforce economics are integrated into Business Drivers, OPEX composition and Plan & Forecast rather than presented as a separate HR application.

## Hard release controls

Deployment is blocked if material controls fail. The suite includes:

- journal and trial-balance integrity
- legal and consolidated Balance Sheet equations
- actual and forward cash-flow reconciliation
- intercompany AR/AP and consolidation bridges
- Treasury IC and cash-pool zero-sum controls
- debt schedule to GL reconciliation
- AR, inventory and AP subledger reconciliation
- ECL and inventory-provision reconciliation
- factory absorption schedule to ledger
- contract-liability and refund reconciliation
- Software ARR, Events backlog and Spare Parts installed-base roll-forwards
- Budget no-hindsight and frozen-vintage controls
- forecast no-lookahead and economic-scale plausibility
- RCF and liquidity-shortfall controls
- three-statement identities and scenario coverage
- Workforce FTE roll-forward
- Workforce allocation reconciliation
- Payroll-to-GL reconciliation
- zero payroll rows in Trade AP
- total OPEX to GL reconciliation
- Workforce forecast OPEX identity
- Payroll cash identity

A failed control raises an exception before deployment.

## Key generated outputs

```text
data/processed/management_pnl.csv
data/processed/balance_sheet.csv
data/processed/cash_flow.csv
data/processed/working_capital.csv
data/processed/ar_aging.csv
data/processed/inventory_aging.csv
data/processed/ap_aging.csv
data/processed/contract_liabilities.csv
data/processed/treasury_cash_pool.csv
data/processed/debt_schedule.csv
data/processed/liquidity_forecast.csv
data/processed/forecast_pnl.csv
data/processed/forecast_balance_sheet.csv
data/processed/forecast_cash_flow.csv
data/processed/annual_budget.csv
data/processed/forecast_vintages.csv
data/processed/forecast_accuracy.csv
data/processed/workforce_schedule.csv
data/processed/workforce_summary.csv
data/processed/workforce_forecast.csv
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
4. simulate operating activity and Workforce capacity
5. create the legal ledger and payroll cash entries
6. post factory absorption and asset-quality provisions
7. rebuild customer settlement, advances and contract liabilities
8. reconstruct AR / Inventory / AP schedules
9. build Budget and rolling forecast vintages
10. apply legal-entity cash pooling
11. build debt, maturity, liquidity and covenant schedules
12. build the payroll-aware 12-month scenario liquidity forecast
13. calculate downside-protected capital-allocation capacity
14. build the integrated three-statement forecast
15. run release controls
16. publish compact CFO datasets
17. commit generated outputs
18. deploy GitHub Pages

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
