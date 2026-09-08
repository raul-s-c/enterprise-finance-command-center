# Contribution explorer

Seven source-tied contribution pages are available in P&L, Profitability, Working Capital, Operations & CAPEX, and Cash Flow. Choose a measure, a grouping and (where available) a month. Select a bar to drill into its contributors, then select the leaf to inspect paginated source records. Use Up one level or Reset drill-down to broaden the view. Where the published source supports the active entity or division and matching records exist, **Use report scope** carries that context into the explorer. Unsupported or empty combinations are never offered as a working filter.

Bars use a signed zero baseline and neutral actual-value notation. Amounts are EUR, not EUR millions. Shares are contributor divided by the selected signed total, not absolute magnitude shares. Offsetting balances can produce negative or greater-than-100% shares; a zero denominator is unavailable. Contributors are ranked by absolute amount and paginated without dropping the remaining rows. Missing measures are counted and disclosed, not replaced by zero.

## Source contract and limits

| Explorer | Published source | Grain / coverage |
| --- | --- | --- |
| P&L | management_detail | Monthly entity/division management allocations; not product legal postings |
| Products | entity_product_profitability | Trailing 12 months, entity/division/family/subfamily/type/quality tier/product |
| Receivables | ar_customer_aging | Closing customer watchlist, not complete group gross AR |
| Inventory | inventory_sku_aging | Closing analytical SKU watchlist, before provisions/consolidation |
| Payables | ap_supplier_aging | Closing supplier watchlist; spend is trailing 12 months |
| CAPEX | capex | Event month/entity/division/project; SPEND and GO_LIVE strictly separated |
| Cash | cash_flow_detail | Monthly legal-entity cash flows; internal transfers are not external revenue |

CAPEX SPEND corresponds to a debit to 1510_CIP and credit to 1000_CASH. GO_LIVE corresponds to a debit to 1500_PPE and credit to 1510_CIP, with no new cash outflow. Those mappings follow the accounting engine; no supplier, funding instrument or product allocation is inferred.

Product lineage exposes revenue, variable production cost, variable selling cost, fixed production cost, marginal contribution, gross profit, OPEX and operating contribution through the complete entity-to-SKU hierarchy. Its entity rows reconcile to the existing group product view. Depreciation, interest, tax and consolidation remain explicitly outside product attribution, so operating contribution is not presented as product EBIT.

These pages reconcile to their own selected published records. They do not claim that a watchlist reconciles to the whole consolidated balance sheet, or that management product economics equal group EBIT. The WC schedules cannot be added together to derive a group NWC from these partial extracts.

## Remaining lineage work

Complete end-to-end attribution still requires publishing full reconciled AR, AP and inventory schedules, provisions and consolidation adjustments, plus transaction identifiers connecting source postings, counterparties and CAPEX projects. The entity/product operating cross-tab is now published and reconciled without allocating financial or consolidation lines. No accounting output is changed.

## Verification

`node --test tests/*.test.cjs` includes signed contribution arithmetic, zero denominators, missing data, explicit coverage limits, CAPEX event separation, and aggregation reconciliation across every published period, measure and supported dimension. Tests verify source data is unchanged. Browser checks cover all seven pages, drill-down/up/reset, source-record pagination, and desktop/mobile viewport fit.
