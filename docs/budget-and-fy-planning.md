# Annual Budget and FY Planning

Version 0.9 adds a frozen Annual Budget and full-year planning bridge to the Enterprise Finance Command Center.

The purpose is to separate three different management views:

```text
Annual Budget      -> What management committed to before the year started
Latest Forecast    -> What management expects now
Actuals            -> What has already happened
```

The Budget is not a renamed forecast. It is a separate planning object with a fixed approval vintage.

## Budget vintage

The current policy finalizes the Annual Budget in October of the prior year.

Example:

```text
Budget 2026
Approval vintage: 2025-10
Target months: 2026-01 through 2026-12
```

Only information available through the budget vintage may influence the plan.

Rebuilding Budget 2026 after August 2026 must therefore produce exactly the same values as rebuilding it with all data after October 2025 removed.

This is a hard release control.

## Commercial planning model

Commercial entity/division combinations use a driver-based plan.

The baseline is the trailing operating history observable at the budget vintage.

```text
Trailing revenue run-rate
x annual division growth
x budget growth stretch
x monthly phasing
= Revenue Budget
```

Current growth stretch above the structural division growth assumption:

```text
Software      +1.5 percentage points
Hardware      +1.0 percentage point
Events        +0.5 percentage points
Spare Parts   +1.0 percentage point
```

The plan also applies explicit management challenges to margins and operating leverage:

```text
Marginal Contribution margin  +0.3 percentage points
Gross Margin                   +0.4 percentage points
OPEX ratio                     -0.2 percentage points
```

Depreciation is planned from the historical carrying-cost run-rate.

## Manufacturing and zero-revenue cost centers

Brno and Suzhou do not book external commercial revenue in the management P&L.

They therefore cannot be budgeted using revenue ratios.

Version 0.9 uses a separate cost-center model:

```text
Historical factory absorption variance
Historical OPEX
Historical depreciation
-> cost-center Annual Budget
```

Negative Gross Profit caused by under-absorption receives a management challenge rather than being perpetuated at 100% of its historical adverse run-rate.

This prevents the Annual Budget from accidentally excluding manufacturing economics.

## Monthly phasing

Commercial Annual Budget revenue is phased across the 12 target months using deterministic seasonality.

The 12 monthly values always sum back to the annual target.

Cost-center budgets use stable monthly run-rates because their economics are capacity- and asset-driven rather than customer-seasonality-driven.

## YTD performance

For every close, the system produces:

```text
YTD Actual
YTD Budget
YTD Variance
```

for:

- Revenue
- Marginal Contribution
- Gross Profit
- OPEX
- Depreciation
- EBIT

The comparison is available by entity and division and can also be consolidated to Group.

## Full-year outlook

The Latest FY Outlook is not a 12-month forward forecast.

It is a calendar-year estimate:

```text
Closed Actual months
+ remaining months from Latest Forecast vintage
= Latest FY Outlook
```

The same calculation is reconstructed for prior forecast vintages:

```text
FC-1
FC-3
FC-6
```

This allows management to see how the expected full-year result has moved as the year progressed.

## Depreciation in FY EBIT

The commercial rolling forecast already contains Revenue, Gross Profit and OPEX.

Version 0.9 adds a depreciation run-rate for the remaining forecast months before calculating FY EBIT.

For manufacturing/cost-center combinations that do not exist in the commercial forecast, the remaining FY P&L uses the last three months observable at each forecast vintage.

This keeps factory economics inside the full-year outlook without introducing future actual information.

## CFO questions answered

The Plan & Forecast view is designed to answer:

- Are we ahead or behind Budget YTD?
- Is the variance revenue-driven or margin/EBIT-driven?
- Do we still expect to deliver the Annual Budget?
- How much has the FY outlook moved since FC-1, FC-3 and FC-6?
- Which divisions explain the FY Budget gap?
- Is the current forecast deterioration new or persistent?
- Did management set an unrealistically aggressive or conservative plan?

## Hard controls

Publication is blocked if:

- a Budget uses source data after its approval vintage
- an entity/division budget does not contain exactly 12 months
- duplicate budget rows exist
- rebuilding the frozen Budget from vintage-truncated data changes any planned financial metric
- the current-year Budget is missing
- the FY planning bridge is missing

The frozen-budget reconstruction tolerance is EUR 0.02.

## Generated outputs

```text
data/processed/annual_budget.csv
data/processed/budget_performance.csv
data/processed/fy_plan_bridge.csv
```

The GitHub Pages application exposes these outputs in the `Plan & Forecast` view together with the rolling forecast scenarios and historical forecast-accuracy analysis.
