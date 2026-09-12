# Readable, adaptive financial reports

## Presentation contract

- A KPI band supports an analytical or evidence panel; it is not a standalone report destination.
- Wide statement workspaces show trend, bridge, contribution and the evidence inspector together.
- At widths up to 1500 CSS pixels, statement and contribution workspaces provide explicit analysis-focus controls. The selected focus survives resize and filter rerenders.
- A statement KPI opens calculation and source evidence in the existing accessible modal on compact screens. It does not place a permanent inspector over the charts.
- Compact mobile screens retain every KPI in a horizontal band and allow natural report scrolling. Desktop overflow is contained within the report, not hidden by a fixed-height panel.
- Mobile trend charts preserve every observation on a readable horizontal canvas, initially positioned at the latest months. The focusable region supports keyboard scrolling; it is not a reduced-data thumbnail.
- Definitions accompany evidence in a disclosure rather than a sparse standalone page.
- Gross-to-net carrying values show signed deductions and published closing balances. Review coverage uses actual observation counts, never synthetic display metrics.

## Ownership

`visual-foundation.css` is the final presentation contract over legacy report styles. `visual-layout.js` owns contribution focus controls; `StatementWorkspace.mount` owns statement focus and evidence interactions. Neither changes source data, calculations, reconciliation tolerances or release gates.

## Design reference

The existing `docs/design/premium-finance-experience.png` remains the visual reference. No replacement concept, navigation module or raster UI was introduced.

| Comparison | Implementation |
| --- | --- |
| Palette | White surfaces, navy typography, blue selection, restrained semantic colors |
| Hierarchy | Larger headline values and readable secondary labels |
| Composition | KPI context above analysis; evidence alongside it on wide screens |
| Narrow screens | Intentional deviation: focus controls and modal evidence instead of squeezing every panel into one row |
| Financial content | Real source values and explicit deductions; no mockup figures copied into the report |
| Navigation | Existing report routes retained; redundant indicator-only and definition-only destinations consolidated |

## Verification

Run `node --test tests/*.test.cjs`. Composition regressions cover KPI/evidence pairing, full-screen boundaries and attached definitions. Gross-to-net tests preserve the signed adjustment and published net value.

`npm ci --ignore-scripts`, `npx playwright install chromium`, then `npm run test:ui` run the automated browser regressions. GitHub's runner has no desktop in-app browser, so its independent `visual` job uses Chromium through Playwright. It traverses every report and subpage, rejects standalone KPI destinations and document overflow, and exercises live resizing and the evidence modal. Screenshots and failure traces are retained as workflow artifacts. Publication requires this job as well as both financial validation jobs. These are rendered layout/interaction assertions, not golden-image pixel-diff tests.

Browser QA must separately exercise wide desktop, laptop, intermediate widths and mobile. Resize while a non-default analysis focus is selected; verify the focus remains selected. Open a KPI calculation, close it, select a division and confirm that the report updates. Inspect both chart labels and controls: a clean console alone is not visual approval.

This change does not certify universal pixel-perfect fidelity or exhaustive entity/product/filter coverage. Source-data controls remain independent of presentation QA.

### September 2026 implementation checks

- Traversed all 18 report destinations and their desktop subpages using the in-app browser. No document-level horizontal overflow or browser console errors were observed during that traversal.
- Exercised Margin at 1784×991, 1366×768, 1280×720 and 1024×768, plus a 390×844 mobile viewport. Verified that the selected bridge survives a live resize from 1280 to 1024 pixels.
- Verified the compact KPI evidence modal, its close control, and the source calculation content.
- The frontend suite contains 48 passing tests, including preservation of all twelve observations in a compact trend chart.
- These checks are not an exhaustive cross-product of every viewport, filter and record selection. Some technical appendix pages deliberately remain text or tables.
