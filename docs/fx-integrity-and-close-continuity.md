# FX Integrity and Close Continuity

## Contract boundary

The current generator emits one intercompany sale/purchase pair per issue month, seller, buyer and division. That tuple is the immutable contract key. Exactly one receivable journal line and one reciprocal payable journal line must exist, with positive finite EUR amounts agreeing within the existing EUR 0.02 tolerance. Additional invoices at that granularity require extending the key with a shared invoice identifier; ambiguous pairs fail instead of being silently aggregated.

The contract uses the seller's functional currency and a deterministic one- or two-month payment term shared by both legs. Source journal IDs, contract currency, amount and settlement month are retained in `intercompany_fx_contracts.csv`. Foreign-currency documents carry explicit `source_journal_id` and `contract_id` fields. Same-functional-currency legs are retained in the contract register but excluded from FX exposure.

This is a correction to v0.20's independent counterparty-currency assumptions. Existing analytical FX files are regenerated, not appended to the former policy. No GL, cash settlement, CTA or historical earnings adjustment is posted. Actual cash matching and integrated transaction-FX postings remain future work.

## Reconciliation gates

- Contract register to both original journal legs, including currency, amount and dates.
- Document population and every source field to the original journal and contract policy.
- Complete document-month lifecycle, status, amounts, metadata and P&L to documents and FX rates.
- Summary key coverage, open-document counts, receivables, payables, net exposure and all P&L measures to snapshots.
- Existing carrying-value, cumulative functional P&L and summary arithmetic controls remain active.
- Missing, duplicate, orphaned, non-finite or malformed data fails validation.

Tests deliberately corrupt summaries by EUR 1,000,000 while retaining internal arithmetic, change contract currency and dates, remove source legs and snapshots, introduce orphan keys, and change counts and exposures. No financial tolerance is relaxed.

## Monthly continuity

`tests/test_close_continuity_v21.py` runs real August and September 2026 offline builds using the complete v0.21 wrapper in a temporary directory. The production-standard 36-month actual window retains the history needed for frozen budgets and prior-year comparatives. The test preserves the August action and review snapshots exactly, retains historical action IDs, checks unique monthly snapshots, advances the 18-month forecast and requires passing release controls and matching dashboard/manifest versions.

The forecast and operating simulation are recalculated per build, as before. This test does not certify immutable historical financial statements or matched bank settlement. The existing lifecycle tests separately exercise recurrence, dated closure, overdue escalation and same-month idempotency.

## Dashboard scope and mobile charts

Executive Revenue, margins, EBIT and action lifecycle follow the selected entity/division. Cash flow, Working Capital, financial position, commentary and close priorities remain group measures and are labelled explicitly. No synthetic division-level cash allocation is introduced.

All chart bars remain available. Below the mobile breakpoint, at most five evenly spaced date labels are shown, including the first and last observation. Each bar has an accessible date/value label. Desktop labels remain unchanged.

Regression commands:

```sh
python -m pytest -m 'not integration'
python -m pytest -m integration
node --test tests/dashboard_scope.test.cjs
```
