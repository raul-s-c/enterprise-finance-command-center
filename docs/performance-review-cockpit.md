# Performance Review cockpit

The opening review screen is a guided reading of the published close: **result → cause → management response → control coverage**. It is not a separate financial model. All values follow the selected Group, Entity, Division or Entity/Division review scope.

## Source contracts

| Visual | Published source | Rule |
| --- | --- | --- |
| Financial scorecard | `performance_review` | Actual, frozen Budget and `variance = actual_value - benchmark_value` for Revenue, EBIT and available FY EBIT outlook. Bars share a scale only within one measure. |
| Adverse narrative | `performance_review` | Highest-materiality adverse observations at the exact selected scope. Headlines, explanations, comparisons, IDs and datasets are preserved. |
| Price / volume / mix bridge | Group `performance_review` effects and `management_detail` revenue | Prior-year revenue + published Price + Volume + Mix effects = current revenue. The bridge is shown only for Group and only if the source identity agrees within one cent. A missing or inconsistent source is never filled with a residual bar. |
| Action states | `management_actions` | Active, in-progress, overdue, carried, closed and cancelled counts use the current selected scope and lifecycle statuses. |
| Review coverage | `performance_review` | Source-dataset counts are observations at the selected scope, not sums across overlapping scope levels. Each row opens the underlying observation values and review IDs. |

The one-cent bridge check is a **display gate**, not a relaxation of the engine's accounting controls. The published validation manifest and release pipeline remain authoritative. FY outlook is shown only where the review source publishes it; operating-scope pages do not substitute a Group value. Negative values retain their sign, and unlike measures never share a visual scale.

## Reading and interaction

1. Compare Actual or Outlook with its own Budget in the scorecard. The KPI definition button explains the formula, period and source.
2. Read the highest-materiality adverse signals. Select one to inspect its original review ID, exact Actual, Benchmark and Variance.
3. At Group scope, follow the reconciled price/volume/mix bridge from prior-year to current revenue. Select its source to inspect the three effects.
4. Open the action register for owned commitments, or inspect the status summary. Source coverage opens the exact reviewed observations; Controls leads to the close map.

On short laptop screens, the four decision-critical status counts remain visible and **All statuses** exposes the complete seven-state summary. At narrower widths, panels flow vertically without horizontal scrolling. The main desktop layout remains within one viewport; it does not hide report rows behind a page-level scroll.

## Verification

`tests/performance_review_visual.test.cjs` checks scope isolation, financial signs and the no-plug bridge display gate. `tests/ui/report-layout.spec.cjs` checks source and action drills, desktop and laptop fit, a filtered operating scope, mobile overflow and that the review still contains supporting evidence rather than KPI-only pages.
