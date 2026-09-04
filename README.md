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
Workforce capacity and cost
        ->
Operating events
        ->
Double-entry legal ledger
        ->
Functional-currency books / Legal-entity financials
        ->
Intercompany consolidation / EUR translation / CTA
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
Capital Allocation Capacity
        ->
Monthly Performance Review / Management Actions
        ->
CFO analytics
```

P&L, Balance Sheet and Cash Flow are not independently generated dashboard numbers. They are consequences of connected operating, accounting and financing events.

## Current release: v0.21

Version 0.21 adds **FX Integrity & Close Continuity**. Transaction FX summaries now reconcile every measure and key to document snapshots; lifecycle snapshots reconcile to source documents and official/fallback rates; documents reconcile to the authoritative journal. Missing, duplicate, orphaned and non-finite data block release.

Intercompany contracts now retain both reciprocal journal references with one seller-functional contract currency and one deterministic settlement month. The seller's domestic-currency leg stays in the contract register, not the foreign-currency exposure population. The v0.20 analytical population is rebuilt under this corrected policy; transaction FX totals are therefore not directly comparable across the policy change. Historical GL statements are unchanged.

Executive explicitly distinguishes filtered operating measures from consolidated group measures. Mobile charts retain all observations with at most five visible date labels. CI runs frontend regression tests and two consecutive offline closes through the complete v0.21 wrapper in an isolated 36-month actual / 18-month forecast fixture.

See `docs/v0.21-status.md` and `docs/fx-integrity-and-close-continuity.md`.

### Transaction FX foundation

Version 0.20 adds **Transaction FX Exposure & Remeasurement** to the connected finance model.

Foreign-currency monetary documents are sourced from actual external and intercompany AR/AP journal lines. Each document preserves its source journal, issue and settlement month, legal entity, division, counterparty, source account, functional currency, transaction currency, original amounts and payment terms.

Open documents are remeasured monthly in functional currency using the same official/fallback FX lineage as the rest of the model. Realized and unrealized FX P&L are kept separate from CTA, with exposure, ageing and lifecycle visible by entity, division and transaction currency. The subledger is an analytical accounting layer sourced from the authoritative journal; it does not post balancing adjustments back into historical statements.

Release controls require:

```text
Review actual / benchmark / variance = source data
Review IDs and action IDs = unique
Every required P1/P2 action = present
Every action = valid review evidence + owner + due month
Every terminal action = dated closure or cancellation evidence
Every overdue action = management or executive escalation
Current required signals = one active action key each
Action and review histories = unique monthly snapshots
Every action cycle = one controlled execution plan
Approval month < effective month
Intervention rates = non-negative and capped
Directional trigger benefits = explicitly non-additive
Operating and forecast impact = additive causal bridge
Every macro driver-month = applied value + source + status
Official observations = exact-month overlays only
Missing official observations = deterministic fallback
Sensitivity detail = group summary
Sensitivity EBIT = Gross Profit impact + OPEX benefit
Sensitivity Net Debt impact = inverse of Ending Cash impact
Sensitivity direction = economically controlled
Standalone sensitivities = explicitly non-additive
Transaction FX documents = unique source journals + AR/AP accounts
Functional currency != transaction currency
Transaction FX snapshots = unique document-month lifecycle
Carrying value = transaction amount × closing transaction FX
Lifecycle FX P&L = functional carrying-value movement
Summary FX P&L = realized FX + unrealized FX
Review summary = current close month
All accounting, workforce, FX and three-statement controls = passed
```

The v0.15 workforce, multi-currency and integrated forecast capabilities remain fully active underneath the review layer. The Balance Sheet still has no balancing plug: cash comes from liquidity, Working Capital from operating drivers, PPE/CIP from CAPEX, debt from its roll-forward and retained earnings from forecast Net Income.

See:

- `docs/monthly-performance-review.md`
- `docs/management-action-lifecycle.md`
- `docs/management-action-execution.md`
- `docs/macro-driver-lineage-and-sensitivities.md`
- `docs/transaction-fx-subledger.md`
- `docs/workforce-cost-planning.md`
- `docs/multicurrency-fx.md`
- `docs/integrated-three-statement-forecast.md`

## Finance scope

The current system includes:

- 236 synthetic product references across a multi-level hierarchy
- six legal entities and two factories
- 36 rolling actual months
- 18 rolling operating forecast months
- 12-month Base / Upside / Downside liquidity forecast
- 12-month Base / Upside / Downside integrated three-statement forecast
- Month x Entity x Division x Function workforce roll-forward
- driver-based FTE, attrition, hiring, payroll and recruitment-cost forecast
- functional-currency journals and local trial balances for all six entities
- document-level transaction FX exposure, ageing and realized/unrealized remeasurement
- EUR group translation with historical equity rates and explicit CTA / OCI
- reported versus constant-currency Revenue and EBIT
- source-tied monthly performance review across group and operating scopes
- deterministic variance explanations and owned P1/P2 management actions
- persistent management action lifecycle, monthly snapshots and change history
- approved action execution plans and effective dates
- causal operating and forecast action-impact bridges
- directional, non-additive per-action benefit tracking
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
- FX & Translation
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
- workforce FTE roll-forward and non-negative capacity
- workforce personnel-cost allocation to operating records
- payroll journal and direct-cash settlement integrity
- workforce-driven forecast OPEX identity
- workforce-aware liquidity payroll cash identity
- functional-currency journal balance and EUR round-trip control
- translated Balance Sheet equation including historical equity and CTA
- functional-currency, translation and constant-currency output completeness
- performance-review source value and variance tie-out
- unique review/action IDs and current-month completeness
- required-action coverage and valid action ownership
- no orphan management actions
- unique active action keys and complete current-trigger coverage
- terminal action evidence and overdue escalation
- action, review and change-history integrity
- one execution plan per action cycle with dated evidence
- execution-plan scope, rates and effective-date integrity
- complete benefit snapshots and additive forecast bridge coverage
- complete macro lineage and sensitivity detail-to-summary reconciliation

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
data/processed/workforce_schedule.csv
data/processed/workforce_summary.csv
data/processed/workforce_forecast.csv
data/processed/functional_currency_journal_sample.csv
data/processed/local_trial_balance.csv
data/processed/fx_translation.csv
data/processed/constant_currency_analysis.csv
data/processed/monthly_performance_review.csv
data/processed/management_actions.csv
data/processed/management_action_history.csv
data/processed/management_action_changes.csv
data/processed/performance_review_history.csv
data/processed/performance_review_summary.csv
data/processed/management_action_plans.csv
data/processed/management_action_benefits.csv
data/processed/management_action_actual_impact.csv
data/processed/management_action_forecast_bridge.csv
data/processed/macro_lineage.csv
data/processed/financial_sensitivity_detail.csv
data/processed/financial_sensitivity_summary.csv
data/processed/transaction_fx_documents.csv
data/processed/transaction_fx_snapshots.csv
data/processed/transaction_fx_summary.csv
data/processed/intercompany_fx_contracts.csv
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
4. simulate operating demand and build the workforce roll-forward
5. allocate payroll and non-people OPEX to operating activity
6. create the legal ledger with payroll settled directly through cash
7. post factory absorption and provisions
8. rebuild customer settlement, advances and contract liabilities
9. reconstruct AR / Inventory / AP schedules
10. build Budget and workforce-driven rolling forecast vintages
11. apply legal-entity cash pooling
12. rebuild actual Balance Sheet and Cash Flow after pooling
13. build debt, maturity, liquidity and covenant schedules
14. build the payroll-aware 12-month scenario liquidity forecast
15. calculate downside-protected capital-allocation capacity
16. build the integrated three-statement forecast
17. create functional-currency journal mirrors and local trial balances
18. translate foreign entities to EUR and calculate CTA / OCI
19. calculate reported and constant-currency Revenue and EBIT
20. build the source-tied monthly performance review
21. create owned management actions for material adverse signals
22. reconcile actions with the prior close and append controlled history
23. calculate age, overdue status, carry-forward and escalation
24. create or carry forward one controlled execution plan per action cycle
25. apply approved interventions only from their effective month
26. measure non-additive trigger improvement and additive operating/forecast impact
27. assemble workforce, FX, review, lifecycle, execution and core finance dashboard datasets
28. run release controls
29. publish compact CFO datasets
30. commit generated outputs
31. deploy GitHub Pages

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
