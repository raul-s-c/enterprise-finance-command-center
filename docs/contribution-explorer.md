# Contribution explorer

Seven source-tied contribution pages are available in P&L, Profitability, Working Capital, Operations & CAPEX, and Cash Flow. Choose a measure, a grouping and (where available) a month. Select a bar to drill into its contributors, then select the leaf to inspect paginated source records. Use Up one level or Reset drill-down to broaden the view. Where the published source supports the active entity or division and matching records exist, **Use report scope** carries that context into the explorer. Unsupported or empty combinations are never offered as a working filter.

Bars use a signed zero baseline and neutral actual-value notation. Amounts are EUR, not EUR millions. Shares are contributor divided by the selected signed total, not absolute magnitude shares. Offsetting balances can produce negative or greater-than-100% shares; a zero denominator is unavailable. Contributors are ranked by absolute amount and paginated without dropping the remaining rows. Missing measures are counted and disclosed, not replaced by zero.

## Source contract and limits

| Explorer | Published source | Grain / coverage |
| --- | --- | --- |
| P&L | management_detail | Monthly entity/division management allocations; not product legal postings |
| Products | entity_product_profitability | Trailing 12 months, entity/division/family/subfamily/type/quality tier/product |
| Receivables | credit_loss_detail | Complete closing external-customer schedule, gross/ECL/net |
| Inventory | inventory_provision_detail | Complete closing legal SKU schedule, gross/provision/net |
| Payables | ap_supplier_aging | Complete closing external-supplier schedule; spend is trailing 12 months |
| CAPEX | capex | Event month/entity/division/project; SPEND and GO_LIVE strictly separated |
| Cash | cash_flow_detail | Monthly legal-entity cash flows; internal transfers are not external revenue |

CAPEX SPEND corresponds to a debit to 1510_CIP and credit to 1000_CASH. GO_LIVE corresponds to a debit to 1500_PPE and credit to 1510_CIP, with no new cash outflow. Those mappings follow the accounting engine; no supplier, funding instrument or product allocation is inferred.

Product lineage exposes revenue, variable production cost, variable selling cost, fixed production cost, marginal contribution, gross profit, OPEX and operating contribution through the complete entity-to-SKU hierarchy. Its entity rows reconcile to the existing group product view. Depreciation, interest, tax and consolidation remain explicitly outside product attribution, so operating contribution is not presented as product EBIT.

The AR and AP schedules reconcile to their respective external legal-ledger control accounts. The inventory schedule reconciles gross legal inventory and its obsolescence provision; the unrealized intercompany markup reserve remains a separate consolidation adjustment and is not allocated to products. Intercompany receivables and payables are also separate, so these three schedules must not be added together and presented as consolidated group NWC. Product operating contribution is not group EBIT.

## Remaining lineage work

Complete end-to-end attribution still requires document identifiers connecting customer invoices and collections, supplier accruals and payments, inventory movements, provisions, consolidation adjustments and CAPEX projects to their source journal postings. The complete closing WC schedules and entity/product operating cross-tab are published without allocating financial or consolidation lines. No accounting output is changed.

## Verification

`node --test tests/*.test.cjs` includes signed contribution arithmetic, zero denominators, missing data, explicit coverage limits, CAPEX event separation, and aggregation reconciliation across every published period, measure and supported dimension. Tests verify source data is unchanged. Browser checks cover all seven pages, drill-down/up/reset, source-record pagination, and desktop/mobile viewport fit.
