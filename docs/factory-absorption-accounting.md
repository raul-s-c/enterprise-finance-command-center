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

The Business Drivers report now shows actual fixed cost less absorbed fixed cost equals the posted absorption variance, both in total and by factory. The adjacent ranking uses published source-factory units in external sales. It is a sell-through view, not monthly factory output, and is deliberately not reconciled to produced units. Both underlying source tables remain expandable; the paired report is fixed Group scope.

## Replenishment and practical capacity (v0.29.0)

Factory production is the cost-plus replenishment ordered by commercial entities. Each entity orders `sold units + target ending inventory - opening inventory`, where the target is the division DIO applied to the **trailing three-month average demand** (current month included, no look-ahead). Before v0.29.0 the target used the current month's sales only, so a seasonal drop such as December to January cut orders to almost zero and was followed by a spike (bullwhip): January output fell to roughly 1-3% of a normal month and absorption swung between 5% and 164% of actual fixed cost. Planning on trailing demand keeps the same DIO policy while producing a realistic, smoother output profile; the ledger, intercompany, inventory, payables and cash effects all follow from the posted transfers. The 24-month liquidity and integrated three-statement forecast applies the same policy: forecast ending inventory is the division DIO applied to trailing three-month average physical direct cost, seeded with the latest actual months, so forecast inventory and supplier cash no longer swing with single-month seasonality.

Factory capacity is configured as **practical capacity**: 3,200 units per month in Brno and 4,100 in Suzhou before CAPEX expansions. Peak months run at about 92% utilization and typical months at 65-70%. Capacity drives the utilization and headroom indicators only; absorbed fixed cost is still the fixed-overhead content of transferred standard cost, so capacity does not change the posted absorption variance.

The first actual month remains a start-up period: opening balances contain no inventory, receivables or payables, so that month fills working capital from zero and shows output above practical capacity. It sits outside the 12-month operating window shown in the dashboard and is disclosed here rather than adjusted.
