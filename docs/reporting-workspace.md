# Interactive reporting workspace

The dashboard is a code-native HTML/CSS/SVG reporting application over the existing version 0.21.0 finance dataset. No financial engine, balances, tolerances or generated outputs are changed by this redesign. It does not require Power BI hosting or a paid visualization dependency.

## Guided close journey

`Close Journey` is the teaching layer of the application. It presents the full finance operating model as eight connected stages: drivers, transactions, double-entry ledger, legal close, consolidation and FX, financial statements, forecast and review, and actions and benefits. Selecting a stage explains what happens, names its inputs and outputs, shows three published release controls, and links directly to three existing reports that prove the result. The competency map makes the contribution of Accounting, Controlling, Treasury, Consolidation, FP&A and Governance explicit, so a visitor can understand both the process and the ownership model without prior knowledge of the project.

## Navigation and context

- Six primary decision areas group all eighteen report views: Executive; Performance; Cash & Balance; Plan & Outlook; Operations; and Close & Controls. The active area's reports appear as contextual tabs beside the title, so the main rail remains stable and immediately understandable.
- Each existing indicator group, report panel and explanatory note is available as a named subpage. The Subpage selector lists the complete catalog; Previous/Next traverses it without vertical page scrolling.
- Tables use row search, row pagination and column pagination with the first identifier column retained. Selecting a row opens its complete field detail, including truncated cell text.
- Entity, division, report, subpage and Executive metric are encoded in the URL. Reload and browser Back/Forward preserve that context.
- Consolidated measures are explicitly separate from selected operating scope. Existing source/subtitle scope rules remain in force; this UI does not invent division-level cash allocations.
- On narrow screens paired Area and Report selectors replace the navigation rail, the KPI band becomes horizontally scrollable and the evidence inspector opens only on request. The complete twelve-month Executive comparison remains visible; group KPIs and division detail remain accessible in their own subpages.

## Contextual interaction

See [Contribution explorer](contribution-explorer.md) for signed attribution charts, source-record drill-down, CAPEX movement direction, and explicit coverage limits for partial WC schedules.

`web/report-context.js` defines the dimensions and published source for each report subpage. Entity and division choices depend on the current page and on one another. Unsupported controls are hidden; consolidated and fixed-scope reports explicitly explain their scope while retaining the operating selection for the next applicable page. An unavailable selection is broadened to All with a visible notice, never silently changed to another entity.

Operating choices exclude inactive scaffold combinations in the latest close, not legitimate zero KPIs or losses. Other choices require matching published records. Missing records are explained with a route back to Executive rather than presented as a loading failure. This does not manufacture observations absent from compact source datasets.

KPI cards are grouped into scope-specific subpages so software, factory, workforce and group indicators do not imply that the same filters apply to all of them. Business-driver subpages remain navigable regardless of the previous selection.

Every table column can be sorted ascending or descending, including compact currency and percentage values. Row details offer **Explore this scope** when the row identifies an available operating entity/division; this opens Executive with that scope and preserves browser-history navigation. Sorting and navigation do not modify published data.

## KPI calculation help

Every KPI card includes a keyboard-accessible information button. Its dialog separates Calculation, Scope, Period, Source and Display into short pages, including on mobile. Close or Escape returns focus to the opening control. `web/kpi-definitions.js` is reviewed presentation metadata, not a second accounting engine. Unknown indicators receive an explicit unavailable definition; tests reject missing definitions for the rendered catalog across all entity/division selections.

Definitions distinguish monthly flows, trailing/YTD flows and point-in-time forecast balances, as well as filtered operating measures and consolidated group measures. Legacy zero/missing-value display behavior is disclosed rather than silently described as a valid observation. Existing summary/watchlist limits remain documented; Events KPI aggregation uses the complete available selected detail before applying the table's display limit. Empty Events/workforce selections no longer substitute group totals.

Subpage URL indices are normalized to finite nonnegative integers. Keyboard focus survives metric/subpage controls, table/list pagination and disabled pagination boundaries. Rows support both Enter and Space for full detail.

## Reporting notation

The custom visuals are **IBCS-inspired**, not certified IBCS software or official Zebra BI components. Design references are [IBCS Standards](https://www.ibcs.com/standards/) and [Zebra BI Charts](https://zebrabi.com/power-bi-custom-visuals/charts/).

- AC: solid charcoal; PY: gray; PL: outlined; FC: hatched. Legends identify the notation used in each chart.
- Actual magnitudes use neutral colors. Green/red communicate favorable/unfavorable **variance**, not simply positive/negative balances.
- Costs are presented as positive expenses in the P&L matrix; lower expenses are favorable. Absolute delta is AC minus PY; percentage delta divides by the absolute PY value. A zero or absent denominator is unavailable, not 0%.
- Calendar comparisons match the exact month one year earlier, even if observations are missing.
- Vertical charts retain a true signed zero baseline. FTE uses headcount units, not currency.
- P&L subtotals start at zero; expense steps reduce the preceding balance. The presentation bridge must tie naturally to source EBIT within the unchanged EUR 0.02 tolerance.

## Design system

White report canvas; pale-gray navigation and context strip; Segoe UI with tabular figures; charcoal actuals, gray comparatives, blue navigation, green/red variance; thin rules and square-edged controls. The Executive report combines a message, a flat KPI band, monthly comparison/variance charts and a clickable division matrix. The P&L provides a comparable statement matrix and bridge. The existing report catalog uses the same typographic and pagination system.

Executive Overview is an enterprise control tower rather than a landing-page index. Its one-screen decision surface contains five selectable KPIs, Actual/PY revenue history, EBIT contribution, a source-tied free-cash-flow driver tree, current management priorities and a 36-month event timeline. Selecting a KPI opens a persistent evidence inspector with its calculation, published source, active scope, period, lineage and direct routes to explanation, contribution and data trace. The inspector remains usable at 720-pixel desktop height and becomes an overlay at narrower widths.

Contribution analysis is also a dedicated one-screen workspace. It combines the reconciled total and formula, signed ranking, source-to-financial-line flow, selected-item inspector and searchable evidence table. Drill-down, Up and Reset preserve the published hierarchy. Contribution pages are intentionally never paired with another report section: this avoids cramped tables and guarantees that every control remains visible without a hidden vertical continuation.

Eleven core finance and operating modules now open with dedicated one-screen cockpits. P&L combines five selectable measures, Revenue/EBIT history, a source-tied bridge, division contribution and an evidence inspector. Cash Flow connects operating, investing and financing movements to free cash flow, exposes legal-entity contribution and drills directly into the detailed report. Balance Sheet connects the accounting equation, asset composition and funding structure to the same calculation/source/control inspector.

Plan & Forecast links the 12-month Revenue, EBIT, Free Cash Flow and ending-cash outlook to scenario range, forecast accuracy and the forecast balance check. Treasury makes the cash + undrawn RCF - operating minimum liquidity equation explicit, adds the downside headroom outlook and exposes the post-pooling legal-entity cash position. Macro & Sensitivities links official/fallback lineage to standalone EBIT and cash exposure without treating shocks as additive. Business Drivers connects ARR, backlog, factory capacity, aftermarket revenue and workforce to the accounting outputs. Profitability traces Revenue through Marginal Contribution, Gross Profit, allocated OPEX and Operating Contribution, with published product-family and customer contribution. Intercompany shows manufacturing cost plus transfer-pricing markup, consolidation elimination, unrealized inventory-profit reserve and reciprocal cash-pool flows. Operations & CAPEX separates cash SPEND from the non-cash CIP-to-PPE GO_LIVE transfer, connects project spend to capacity, and shows factory utilization, headroom and absorption evidence. FX & Translation keeps constant-currency performance, transaction remeasurement and CTA/OCI in distinct accounting paths.

These cockpits do not replace the original report pages: every matrix, schedule, portfolio event and context page remains available immediately after the cockpit. Filters appear only where the published data supports the requested grain. On mobile, KPI cards use a horizontal strip and analytical regions follow a deliberate chart, explanation, contribution and evidence sequence.

The application is organized as a six-area management book rather than an index of isolated tables. Executive provides **Overview**, **Drivers**, **Outlook** and **Actions** screens: each combines the decision message, KPIs, trend, attribution, management response and company timeline needed to understand the close. The remaining reports pair related source sections into multi-visual screens while the Subpage selector retains every original section and its traceability. On narrow screens an explicit region switch replaces the two-column composition, so neither panel becomes an undiscoverable hidden continuation.

The pale navigation rail is a persistent map of six decision areas. Contextual report tabs always remain within the selected area; reports with more than four composed screens expose four stable landmarks plus the complete named Subpage selector. Direct URLs to every report remain compatible. No financial observations are duplicated or invented by this composition layer. Gross-margin variance is labelled in percentage points, while value measures retain percentage change versus prior year.

Concept-to-implementation adaptations are deliberate: illustrative concept numbers are replaced with real published figures; all existing source panel names are retained instead of the concept's abbreviated tabs; a full subpage selector provides access to the much larger existing catalog; mobile uses a module selector and dedicated detail pages. No mockup image is shipped as UI.

The implementation references used to review hierarchy and density are stored in `docs/design/enterprise-control-tower.png`, `docs/design/contribution-analysis.png`, `docs/design/premium-finance-experience.png`, and `docs/design/close-journey.png`. The references establish the light enterprise shell, global utility bar, compact finance controls, formula tiles, contribution ranking, flow view, inspector, underlying-record grid, and guided close narrative. They are design evidence only; the application itself remains code-native HTML, CSS and SVG.

## Verification

Run `node --test tests/*.test.cjs`. Tests cover calendar matching, source aggregation, missing/non-finite observations, cost polarity, zero denominators, pagination coverage, escaping, signed SVG baselines, scenario notation, FTE units, all eleven premium cockpit structures, linked forecast and liquidity equations, macro non-additivity, driver-to-statement lineage, intercompany elimination, FX accounting separation, CAPEX cash/non-cash treatment, profitability lineage and presentation bridge reconciliation across every published entity/division selection.

Browser QA additionally covers module/subpage navigation, viewport fit, table row and column pagination, search, row/month details, entity/division filters, metric switching, URL reload and browser history. A fixed viewport must never be accepted on the basis of `overflow: hidden` alone: check that the content and visible tables actually fit their allocated areas.

The existing published JSON contains compact/watchlist datasets, not every runtime transaction. Pagination exposes all rows provided to each existing report, not data absent from its source. FX remains an analytical subledger, not bank reconciliation. Full compliance certification, authenticated workflow editing and new accounting postings are outside this UI release.
