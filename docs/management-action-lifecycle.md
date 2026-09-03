# Management Action Lifecycle and Close History

Version 0.17 turns the monthly action output into a persistent, controlled management register. The v0.16 performance review remains the source of current adverse signals; the lifecycle layer never changes accounting values, forecast values or financial tolerances.

## Reconciliation chain

```text
Prior action register + prior histories
Current reconciled performance review
Current required v0.16 actions
-> stable action-key matching
-> status and ownership preservation
-> carry-forward or evidenced closure
-> age, overdue and escalation calculation
-> monthly action/review snapshot
-> deterministic change log
-> lifecycle integrity controls
```

An action key combines scope level, entity, division, trigger metric and source dataset. Only one active action may exist for a key. The original action ID and opening month remain stable while the trigger persists across closes.

## Status model

- `Open`: required action accepted into the register.
- `In Progress`: active action whose execution has started.
- `Closed`: terminal action with a close month and closure evidence.
- `Cancelled`: terminal action with a cancellation month and decision evidence.

User-maintained owner, priority, due date, status and evidence fields in the prior generated register are preserved when the next close runs. If the reconciled review no longer requires an active action, the engine closes it and records the current review as deterministic closure evidence. A later recurrence starts a new action cycle rather than mutating the closed cycle.

## Aging and escalation

```text
Age months = close month - opened month
Carry-forward months = age months for active actions
Overdue months = close month - due month, when positive
```

Overdue P1 actions escalate to `Executive`. Overdue P2 actions escalate to `Management`, becoming `Executive` after two overdue months. Non-overdue and terminal actions have no escalation.

## Persisted artifacts

- `management_actions.csv`: latest state of every action cycle.
- `management_action_history.csv`: one snapshot per close month and action ID.
- `management_action_changes.csv`: deterministic created, carried-forward and status-change events.
- `performance_review_history.csv`: source review evidence retained across closes.
- `performance_review_summary.csv`: current performance metrics plus lifecycle counts.

The dashboard publishes the latest register, action history and change log. It shows active, in-progress, overdue, carry-forward, closed and cancelled counts, monthly trends and escalated actions.

## Release controls

The build fails when:

- lifecycle columns or core fields are missing;
- action IDs or active action keys are duplicated;
- a current required trigger has no active action;
- an action is orphaned from its current or original review evidence;
- a terminal action lacks dated evidence;
- an overdue action lacks escalation;
- the current monthly snapshot is incomplete;
- action, review or change histories contain duplicate identities;
- a change points to a missing action; or
- summary status counts do not reconcile to the register.

All v0.16 source tie-outs and every earlier accounting, consolidation, Working Capital, Treasury, workforce, FX, liquidity and three-statement control remain active.
