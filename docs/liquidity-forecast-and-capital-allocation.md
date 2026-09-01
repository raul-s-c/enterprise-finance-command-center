# Liquidity Forecast and Capital Allocation Capacity

Version 0.12 extends Treasury from a current-state view into a 12-month forward liquidity model.

The model deliberately reuses the rolling forecast vintages already produced by FP&A. It does not create an independent cash forecast disconnected from the operating forecast.

## Forecast architecture

For each of Base, Upside and Downside scenarios, the financial state advances once per forecast month.

```text
Revenue Forecast
-> Trade Receivables
-> Customer Cash

Physical Cost Forecast
-> Inventory

Operating Cost
-> Accounts Payable
-> Supplier Cash

Software / Events
-> Contract Liabilities
-> Customer Funding

EBIT
-> Tax

Debt
-> Interest
-> Scheduled Amortization

CAPEX Projects
-> CAPEX Cash

All Drivers
-> Operating Cash Flow
-> Ending Cash
-> RCF Requirement
-> Gross / Net Debt
-> Liquidity Headroom
-> Covenant Position
```

Entity / Division forecast rows remain the driver grain for DSO, DIO, DPO and prepayment economics, but the consolidated liquidity state advances exactly once per month and scenario.

## Working Capital forecast

Target balances are derived from the same operational policies used by the actual model.

Trade receivables use divisional DSO and are reduced by expected customer-prepayment ratios for Software and Events.

Inventory is forecast only for Hardware and Spare Parts using DIO.

Accounts Payable uses divisional DPO and forecast operating accruals.

Customer funding is represented as Contract Liabilities rather than negative receivables or revenue acceleration.

## Cash identities

Customer cash follows:

```text
Revenue
+ Opening AR
- Ending AR
+ Ending Contract Liabilities
- Opening Contract Liabilities
= Customer Cash
```

Supplier cash follows:

```text
Operating Accrual
+ Opening AP
- Ending AP
= Supplier Cash
```

The monthly cash roll-forward is:

```text
Opening Cash
+ Operating Cash Flow
- CAPEX
- Scheduled Debt Repayment
+ RCF Draw
= Ending Cash
```

All three identities are hard release controls.

## RCF logic

The Revolving Credit Facility is not drawn unless forecast cash would otherwise fall below the configured group operating minimum.

```text
Required Draw = max(Minimum Cash - Cash Before RCF, 0)
RCF Draw <= Available RCF
Drawn RCF + Undrawn RCF = Facility Limit
```

If the group still falls below minimum cash after fully drawing the facility, the release control reports a liquidity shortfall.

## Liquidity and covenants

For every forward month the model calculates:

- ending cash
- gross debt
- net debt / net cash
- TTM EBITDA
- TTM interest
- Net Debt / EBITDA
- interest coverage
- undrawn RCF
- liquidity headroom
- covenant status

## Strategic liquidity buffer

In addition to minimum operating cash, Treasury protects a strategic liquidity buffer configured in `config/company.yml`.

Current policy:

```text
Strategic Liquidity Buffer = EUR 15m
```

This buffer is not required for ordinary operations. It is deliberately protected when estimating capital-allocation capacity.

## Capital allocation capacity

Version 0.12 does not automatically recommend acquisitions, dividends, buybacks or additional CAPEX.

Instead, it calculates a conservative capacity envelope using the Downside scenario.

```text
Downside Deployable Cash
vs
Downside Minimum Liquidity Headroom
-> Lower Value
-> Downside-Protected Allocation Capacity
```

This is a decision-support metric, not an automated management decision.

## Hard controls

Deployment is blocked if any of the following fail:

```text
Cash roll-forward gap                         = 0
Customer cash identity gap                    = 0
Supplier cash identity gap                    = 0
RCF drawn + undrawn - facility limit          = 0
Negative forecast financial balances          = 0
12 months x 3 scenarios                       = complete
RCF drawn above facility limit                = 0
Liquidity shortfall after available RCF       = 0
Base scenario missing                         = 0
Downside scenario missing                     = 0
```

These controls run in addition to all accounting, Working Capital, provisions, contract-liability, Treasury, Budget and rolling-forecast controls.

## Generated outputs

```text
data/processed/liquidity_forecast.csv
data/processed/liquidity_forecast_summary.csv
data/processed/capital_allocation_capacity.csv
```

The Treasury and Plan & Forecast views expose the forward liquidity scenarios and the downside-protected capital-allocation envelope.
