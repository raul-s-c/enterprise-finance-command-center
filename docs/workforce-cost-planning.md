# Workforce Cost Planning

Version 0.14 replaces the previous percentage-of-revenue OPEX simplification with an aggregated Workforce capacity and cost model.

The objective is financial planning, not a synthetic HR application. No employees, names, personal records or fake org charts are generated.

## Grain

Workforce is modeled at:

```text
Month
× Legal Entity
× Division
× Function
```

Functions vary by business model. Examples include R&D, Sales and Customer Success in Software; Product Management and Supply Chain & Commercial Operations in Hardware; Project Delivery and Program Management in Events; and Service Operations and Planning in Spare Parts.

## Headcount roll-forward

Every function follows the identity:

```text
Opening FTE
- Attrition
+ Hires
= Ending FTE
```

Target FTE is driven by lagged business demand and Revenue/FTE productivity rather than current-month Revenue alone. Hiring closes only part of the capacity gap each month, while excess capacity is primarily reduced through natural attrition instead of automatic layoffs.

The model includes:

- annual attrition
- hiring-gap closure rate
- productivity improvement
- minimum FTE by Entity/Division
- entity salary levels
- function-specific cost multipliers
- fully loaded employment cost
- wage inflation
- recruitment cost per hire

All assumptions are explicit in `config/company.yml`.

## Actual OPEX economics

Operating expense is separated into two economic components:

```text
Personnel Cost
+ Non-People OPEX
= Total OPEX
```

Personnel cost includes payroll and recruitment cost. Non-people OPEX remains linked to external operating activity.

Workforce cost is allocated to product/customer operating rows only for profitability analysis. This allocation does not imply that an individual employee belongs to a specific transaction.

## Accounting treatment

Payroll does not create Trade Payables.

```text
Dr 6000_OPEX
Cr 1000_CASH
```

External non-people OPEX continues through supplier accruals:

```text
Dr 6000_OPEX
Cr 2100_AP
```

Supplier payments are rebuilt from actual `2100_AP` accruals after payroll is removed from Trade AP.

This means:

- payroll affects P&L immediately
- payroll affects operating cash immediately
- payroll does not inflate AP
- payroll does not distort DPO
- supplier aging remains a supplier schedule rather than an employee-payment schedule

After the OPEX split, monthly P&L closing entries are rebuilt at cent precision so retained earnings and legal Balance Sheets remain exact.

## Workforce-driven rolling forecast

The rolling forecast preserves the established Revenue/margin/bias framework but replaces percentage-of-Revenue OPEX with an explicit Workforce roll-forward.

For every vintage, Entity, Division and scenario the model projects:

```text
Current FTE
-> Attrition
-> Target FTE from forecast demand and productivity
-> Hires
-> Ending FTE
-> Average FTE
-> Payroll / loaded cost
-> Recruitment cost
-> Personnel Cost

Forecast Revenue
-> Non-People OPEX

Personnel Cost + Non-People OPEX
= Forecast OPEX
```

The resulting fields include:

- `workforce_target_fte`
- `workforce_fte_forecast`
- `workforce_hires_forecast`
- `workforce_attrition_forecast`
- `personnel_cost_forecast`
- `non_people_opex_forecast`
- `opex_forecast`

## Liquidity and three-statement integration

The liquidity forecast treats payroll as a separate cash outflow:

```text
Customer Cash
- Supplier Cash
- Payroll Cash
- Interest
- Tax
= Operating Cash Flow
```

Supplier cash therefore excludes personnel cost.

The payroll-aware liquidity model is the monetary source for the integrated forecast P&L, Balance Sheet and Cash Flow. Forward monetary states are materialized at cent precision and become the exact opening states of the following month.

Version 0.14 intentionally builds the three-statement forecast **after** payroll-aware liquidity, rather than running the older v0.13 liquidity model first and patching it later.

## Hard controls

The release is blocked unless:

```text
Opening FTE - Attrition + Hires - Ending FTE = 0
Allocated Personnel Cost - Workforce Schedule Personnel Cost = 0
Payroll journal - Workforce Personnel Cost = 0
Payroll rows posted to Trade AP = 0
Total OPEX GL - Operating OPEX = 0
Forecast OPEX - Personnel - Non-People OPEX = 0
Payroll cash identity = 0
Legal Balance Sheets = balanced
Consolidated Balance Sheet = balanced
Forward cash roll-forward = 0
Forecast Assets - Liabilities - Equity = 0
```

The full release validation also retains every previous control for intercompany, Working Capital, provisions, customer advances, factory absorption, Budget, forecast scale, Treasury and liquidity.

## Published outputs

```text
data/processed/workforce_schedule.csv
data/processed/workforce_summary.csv
data/processed/workforce_forecast.csv
```

The dashboard exposes Workforce economics in Business Drivers, OPEX composition in P&L and the forward FTE/cost plan in Plan & Forecast.
