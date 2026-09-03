# Management Action Execution and Benefits Realization

Version 0.18 connects the persistent management action register to future operating drivers and the integrated forecast. It does not post management adjustments, create balancing entries or treat an observed variance improvement as automatically attributable benefit.

## Controlled flow

```text
Reconciled adverse signal
-> persistent action cycle
-> approved execution plan
-> future effective month
-> explicit operating-driver change
-> operating transactions and ledger
-> actual and forecast impact bridges
-> monthly benefit evidence
```

Every action cycle has one plan. The plan preserves action scope and owner and records approval, effective, target and benefit-end months. Intervention profiles can affect price, volume, variable cost or non-people OPEX. Individual rates are conservative, deterministic and capped at five percent.

The effective month must follow the approval month. A three-month ramp prevents an action from claiming its full effect immediately. Benefits can remain in the operating baseline for a defined period after the source trigger closes. Cancelled plans do not affect drivers.

## Financial integrity

Actions change operating drivers before accounting. Revenue, cost, Gross Profit and OPEX consequences therefore enter the existing balanced journal and all downstream statements normally. Forecast effects also feed the liquidity and integrated three-statement forecast.

No action can write directly to a financial statement, cash balance, retained earnings or reconciliation control.

## Two types of evidence

Per-action benefit snapshots compare the source trigger with its current reconciled value. This evidence is directional and non-additive because actions at Group, Entity and Division level can address overlapping economics.

Portfolio impact is additive. The operating engine records the incremental Revenue, Gross Profit, OPEX and EBIT effect once at transaction grain. The forecast bridge aggregates the equivalent incremental fields by month and scenario.

Forecast-process correction and FX-exposure review are governance-only plans. They retain targets and execution evidence but do not create an artificial monetary impact.

## Release controls

Publication fails when:

- an action cycle has no plan or a plan is orphaned;
- plan IDs or action IDs are duplicated;
- approval evidence is missing;
- the effective month does not follow approval;
- an intervention rate is negative or exceeds its cap;
- the current benefit snapshot is missing or duplicated;
- directional evidence is incorrectly marked additive;
- the scenario forecast bridge is missing or duplicated; or
- the actual operating impact schedule is missing.
