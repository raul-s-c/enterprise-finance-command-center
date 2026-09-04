# Interactive reporting workspace

The dashboard is a code-native HTML/CSS/SVG reporting application over the existing version 0.21.0 finance dataset. No financial engine, balances, tolerances or generated outputs are changed by this redesign. It does not require Power BI hosting or a paid visualization dependency.

## Navigation and context

- Seventeen report modules are grouped into Overview, Financials, Planning, Operations and Data.
- Each existing indicator group, report panel and explanatory note is available as a named subpage. The Subpage selector lists the complete catalog; Previous/Next traverses it without vertical page scrolling.
- Tables use row search, row pagination and column pagination with the first identifier column retained. Selecting a row opens its complete field detail, including truncated cell text.
- Entity, division, report, subpage and Executive metric are encoded in the URL. Reload and browser Back/Forward preserve that context.
- Consolidated measures are explicitly separate from selected operating scope. Existing source/subtitle scope rules remain in force; this UI does not invent division-level cash allocations.
- On narrow screens the module selector replaces the navigation rail. The Executive preview uses six months instead of twelve; the historical subpage retains the underlying history. Group KPIs and division detail remain accessible in their own subpages.

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

Concept-to-implementation adaptations are deliberate: illustrative concept numbers are replaced with real published figures; all existing source panel names are retained instead of the concept's abbreviated tabs; a full subpage selector provides access to the much larger existing catalog; mobile uses a module selector and dedicated detail pages. No mockup image is shipped as UI.

## Verification

Run `node --test tests/*.test.cjs`. Tests cover calendar matching, source aggregation, missing/non-finite observations, cost polarity, zero denominators, pagination coverage, escaping, signed SVG baselines, scenario notation, FTE units and presentation bridge reconciliation across every published entity/division selection.

Browser QA additionally covers module/subpage navigation, viewport fit, table row and column pagination, search, row/month details, entity/division filters, metric switching, URL reload and browser history. A fixed viewport must never be accepted on the basis of `overflow: hidden` alone: check that the content and visible tables actually fit their allocated areas.

The existing published JSON contains compact/watchlist datasets, not every runtime transaction. Pagination exposes all rows provided to each existing report, not data absent from its source. FX remains an analytical subledger, not bank reconciliation. Full compliance certification, authenticated workflow editing and new accounting postings are outside this UI release.
