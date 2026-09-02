# Workforce Cost Planning

Version 0.14 replaces a revenue-percentage OPEX shortcut with a driver-based workforce model connected to actual accounting, forecast P&L and forward cash.

## Planning grain

Workforce is modeled at:

```text
Month x Entity x Division x Function
```

The model deliberately avoids employee-level synthetic records. It provides the capacity and cost detail needed for finance planning without manufacturing personal data that adds no CFO insight.

## Workforce roll-forward

Each monthly population follows:

```text
Opening FTE
- Attrition
+ Hires
= Ending FTE
```

Average FTE drives monthly payroll cost. Hiring responds to lagged operating demand and configured productivity, attrition and vacancy-closure assumptions. Recruitment cost is calculated separately from recurring payroll.

## Cost allocation

Personnel cost is allocated from the workforce schedule to operating records within the same Entity and Division. The allocation uses observed operating activity and reconciles explicitly back to the workforce schedule.

Total OPEX is therefore:

```text
Personnel cost
+ Non-people OPEX
= Total OPEX
```

This identity is used consistently in actual profitability, rolling forecast, forward liquidity and the integrated three-statement forecast.

## Accounting and cash treatment

Payroll is not a supplier purchase and does not pass through Trade AP.

```text
Dr 6000_OPEX
Cr 1000_CASH
```

Recruitment and other external operating services retain their normal supplier settlement behavior. The liquidity model therefore separates payroll cash from supplier cash and exposes an explicit payroll cash identity.

## Forecast integration

For every Base, Upside and Downside forecast month, operating demand determines target FTE. Attrition and hiring bridge opening FTE to forecast ending FTE; forecast average FTE determines personnel cost. Non-people OPEX is projected separately.

The same cent-precise OPEX block feeds:

- forecast EBIT
- payroll cash
- supplier cash
- forecast tax
- forecast retained earnings
- forecast Balance Sheet and Cash Flow

## Hard controls

Deployment is blocked unless:

```text
Opening FTE - Attrition + Hires - Ending FTE = 0
Workforce values remain non-negative
Allocated personnel cost = Workforce schedule personnel cost
Payroll journal = Allocated personnel cost
Payroll creates no Trade AP
Forecast OPEX = Personnel cost + Non-people OPEX
Forecast payroll cash = Forecast personnel cost
```

## Published outputs

```text
data/processed/workforce_schedule.csv
data/processed/workforce_summary.csv
data/processed/workforce_forecast.csv
```

The dashboard exposes current workforce economics in Business Drivers, personnel versus non-people OPEX in P&L and the 12-month workforce plan in Plan & Forecast.
