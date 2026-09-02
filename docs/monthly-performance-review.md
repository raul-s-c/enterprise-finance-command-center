# Monthly Performance Review and Management Actions

Version 0.16 converts the reconciled monthly close into a controlled CFO review. It does not generate free-form AI commentary and it does not create an independent set of finance numbers.

## Review chain

```text
Reconciled close datasets
-> Actual versus benchmark observations
-> Favorability and materiality assessment
-> Deterministic management explanation
-> Owned P1 / P2 action where required
-> Release controls
```

## Evidence sources

The review reads only existing controlled outputs:

- `budget_performance.csv` for monthly Revenue, Gross Profit, OPEX and EBIT versus Budget
- `price_volume_mix.csv` for prior-year commercial drivers
- `constant_currency_analysis.csv` for reported versus prior-year FX translation
- `working_capital.csv` for monthly cash-conversion movement
- `cash_flow.csv` for Free Cash Flow
- `workforce_summary.csv` for FTE, personnel cost and revenue productivity
- `fy_plan_bridge.csv` for full-year Revenue and EBIT outlook versus Budget
- `forecast_accuracy.csv` for one-month Revenue MAPE

Each review row contains the close month, scope, metric, comparison, unit, actual value, benchmark, variance, materiality, favorability, severity, source dataset and source key. Stable review IDs connect every management action back to its evidence.

## Scope model

Monthly P&L and FX observations are available at four levels:

```text
Group
Entity
Division
Entity x Division
```

Price / Volume / Mix is available for Group and Division. Working Capital, Cash Flow, workforce productivity, FY outlook and forecast discipline are group-level controls because their source schedules are consolidated at that level.

Dashboard filters select the matching scope rather than summing already-calculated percentages or narratives.

## Materiality and actions

Severity is deterministic:

- Critical: absolute variance at or above 15% of its benchmark
- High: absolute variance at or above 5%
- Medium: absolute variance at or above 3%
- Low: below 3%

Group-level High and Critical adverse observations require actions. Entity and Division observations require an action only when they are both High/Critical and exceed 1% of monthly group Revenue, preventing immaterial local percentages from flooding the register. A full-year EBIT gap above 3% also requires an action because of its forward significance.

Every required action includes:

- P1 or P2 priority
- accountable owner role
- due month
- Open / In progress / Closed status
- specific management action
- expected outcome
- source-linked trigger metric and value

## Release controls

The v0.16 build fails when:

- a review or action schema is incomplete
- a review ID or action ID is duplicated
- the review is not for the current close month
- a source-derived actual, benchmark or variance drifts by more than one cent
- a material adverse observation is missing its required action
- an action points to a missing review
- priority, status, owner, action text or due month is invalid
- the current-month review summary is missing

These controls extend all accounting, consolidation, Working Capital, Treasury, workforce, FX, liquidity and three-statement controls from earlier releases.
