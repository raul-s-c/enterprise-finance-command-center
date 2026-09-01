# Factory Absorption Accounting

Version 0.6 closes the gap between the Hardware operating schedule and the accounting model.

Before v0.6, factory utilization and under-absorption were management indicators. The legal ledger did not explicitly post the difference between standard fixed production overhead absorbed into product cost and the actual monthly fixed cost of the factory.

Version 0.6 makes that difference an accounting event.

## Cost flow

Physical product standard cost contains:

```text
Variable production cost
+ Standard fixed production overhead
= Standard group manufacturing cost
```

The manufacturing entity transfers product to the commercial entity using cost-plus transfer pricing.

The fixed-cost share contained in the transferred manufacturing cost becomes **absorbed fixed cost**.

Actual monthly factory fixed cost comes from the factory configuration.

```text
Actual Factory Fixed Cost
- Absorbed Fixed Cost
= Factory Absorption Variance
```

A positive variance is under-absorption. A negative variance is over-absorption.

## Journal entries

A new P&L account is introduced:

```text
5450_FACTORY_ABSORPTION_VARIANCE
```

### Under-absorption

```text
Dr 5450_FACTORY_ABSORPTION_VARIANCE
Cr 2100_AP
```

### Over-absorption

```text
Dr 2100_AP
Cr 5450_FACTORY_ABSORPTION_VARIANCE
```

The variance is posted before supplier-payment logic. It therefore affects:

- factory Gross Profit
- tax accrual
- retained earnings
- trade payables
- supplier cash payments
- operating cash flow

The standard manufacturing cost already accrued by the factory plus the absorption variance equals variable manufacturing cost plus actual fixed factory cost.

## Management P&L

Manufacturing entities do not create external sales rows in the commercial operating dataset. Earlier releases therefore omitted their depreciation, interest, tax and factory absorption variance from the management P&L.

Version 0.6 appends dedicated Hardware manufacturing rows for CZ01 and CN01.

Each factory row contains:

```text
Revenue                       0
Marginal Contribution         0
Factory Absorption Variance   +/- variance
Gross Profit                  - variance
Depreciation                  factory depreciation
EBIT                          Gross Profit - Depreciation
Interest                      factory interest
Tax                           factory tax
Net Income                    EBT - Tax
```

Commercial Hardware product rows still contain standard fixed production overhead. The factory row therefore adjusts standard cost to actual fixed factory economics without rewriting product transactions.

## Factory schedule

The Hardware schedule now reads the accounting-engine outputs directly.

For each factory and month it exposes:

- produced units
- capacity units
- utilization
- actual fixed factory cost
- absorbed fixed cost
- absorption variance
- under-absorption
- over-absorption
- fixed-cost absorption percentage
- capacity headroom
- fixed cost per produced unit

The schedule no longer estimates absorbed fixed cost as `utilization x fixed cost`.

## Controls

The release is blocked unless both controls pass:

```text
Actual Fixed Cost
- Absorbed Fixed Cost
- Absorption Variance
= 0
```

and

```text
Factory Schedule Absorption Variance
- 5450 Journal Balance
= 0
```

These controls sit alongside the existing journal, balance-sheet, intercompany, cash-flow, Working Capital, forecast and divisional-schedule controls.
