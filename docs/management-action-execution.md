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

## Visual execution cockpit

The Action Execution first screen now presents the plan lifecycle and the Base 12-month additive EBIT bridge together. Stage counts and the priority list come from `management_action_plans`; the monthly bars and selected-month Revenue/EBIT values come from `management_action_forecast_bridge`, aggregated at the declared group/fixed report scope. An entity/division selection carried from another report does not silently change this group page. The action list expands to its approved outcome, source-review ID and execution evidence. Both panels retain their complete source tables behind explicit disclosures.

Gross plan cases remain non-additive and are available through **All indicators**. They are not used to build the monthly bridge. The second subpage now compares each directional trigger with its own baseline, then shows the close-to-effective-date recognition gate and actual EBIT history; both complete source tables remain available. Actual impact is recorded only after effective dates. A new close may change the status distribution; the visual never infers a later stage from approval alone.
