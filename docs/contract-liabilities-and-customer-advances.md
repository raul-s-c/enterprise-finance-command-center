# Contract Liabilities and Customer Advances

Version 0.10 separates customer cash timing from revenue recognition for Software and Events & Projects.

## Finance principle

Cash collection is not revenue recognition.

A customer may pay before Aureon provides the contracted service. The cash receipt creates a liability until the service is delivered.

```text
Customer advance received
Dr 1000_CASH
Cr 2300_CONTRACT_LIABILITIES
```

Revenue remains recognized by the operating activity and the ordinary sales journal:

```text
Service delivered / revenue recognized
Dr 1100_AR
Cr 4000_EXTERNAL_REVENUE
```

The prepaid balance then settles the related receivable:

```text
Advance applied to delivered service
Dr 2300_CONTRACT_LIABILITIES
Cr 1100_AR
```

Revenue is therefore unchanged by whether the customer pays before or after service delivery.

## Commercial policies

### Software

Software advance rates depend on:

- recurring-revenue share by product family
- quality tier
- customer segment

Base tier shares are:

```text
Essential       35%
Professional    55%
Premium         72%
```

Strategic customers have a higher prepayment tendency and Growth customers a lower one. The final advance share is capped at 85%.

### Events & Projects

Base advance shares are:

```text
Deployment & Integration   35%
Training & Enablement      25%
Customer Experience        40%
Managed Programs           30%
```

## Contract subledger

Every open contract-liability lot contains:

- receipt month
- expected service month
- legal entity
- division
- customer
- product
- product family
- quality tier
- original advance
- remaining contract liability
- months to expected service

The subledger uses the same cent precision as the general ledger.

## Unfulfilled contracts and refunds

An advance cannot remain indefinitely as a stale liability.

The current policy allows a three-month grace period after the expected service month. If the service is still not delivered, the remaining advance is refunded:

```text
Customer advance refund
Dr 2300_CONTRACT_LIABILITIES
Cr 1000_CASH
```

The refund does not touch revenue because no additional service has been recognized.

The grace period is explicit in `config/company.yml` as `refund_grace_months`.

## Working Capital impact

Version 0.10 distinguishes trade Working Capital from customer-funded operating Working Capital.

```text
Trade NWC
= Net Trade Receivables
+ Net Inventory
- Trade Payables

Operating NWC
= Trade NWC
- Contract Liabilities
```

Customer advances therefore improve operating funding without being treated as revenue or profit.

## AR and ECL impact

Customer advances are applied to the intended customer receivable before ordinary cash collections are allocated.

The project then rebuilds customer-level AR aging and recalculates expected credit loss from the remaining exposure. This prevents ECL from being calculated on receivables that have effectively already been funded by customers.

## Financial-statement impact

Contract liabilities affect:

- cash
- trade receivables
- expected credit loss
- Balance Sheet liabilities
- operating Working Capital
- operating cash flow timing

They do not change recognized revenue, Gross Profit or EBIT merely because cash arrives earlier.

## Release controls

Deployment is blocked unless:

```text
Contract liability subledger = 2300_CONTRACT_LIABILITIES
Contract journals are balanced
Contract-aware AR schedule = 1100_AR
AR aging buckets = total AR
No negative contract-liability positions exist
No contract liabilities remain beyond the configured grace period
Customer refund journals are balanced
Legal Balance Sheet balances
Consolidated Balance Sheet balances
Cash Flow reconciles to cash
ECL reconciles after the AR rebuild
```

The same close continues to run all prior accounting, Working Capital, intercompany, factory, Budget and forecast controls.
