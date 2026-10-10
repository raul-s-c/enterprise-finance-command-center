# Cash movement source lineage

## Purpose

The Cash Flow contribution page now explains the latest published close from legal-entity cash-flow totals down to cash-account journals and the available supporting source schedules.

The dashboard publishes `cash_movement_lineage` for the current close only. Earlier periods remain at entity/month cash-flow summary grain; the interface says so explicitly when an earlier month is selected.

## Evidence grain and limits

- Customer collections are allocated from aggregate cash journal IDs to source invoice IDs using the existing risk-aware oldest-receivable policy.
- Supplier payments are allocated from aggregate AP reduction journal IDs to supplier accrual journal IDs using the modeled oldest-accrual policy. Accrual IDs are not supplier invoice numbers.
- CAPEX cash spend ties directly to project SPEND journal IDs. GO_LIVE is a non-cash CIP-to-PPE transfer and is never presented as cash spending.
- Interest, tax, debt, opening cash, and both intercompany cash categories remain at journal grain when no more detailed subledger schedule is published.

The AR and AP invoice/accrual links are analytical allocations, not bank-matched receipts, remittances, or invoice settlements. The dashboard preserves this limitation in each row's allocation basis and in the report note. It does not fabricate remittance IDs, supplier invoices, or bank statements.

## Controls

The close fails if any of these conditions fail:

- Cash-line allocations do not add back to the source cash journal ID within €0.05.
- Detail totals do not reconcile to cash-flow category totals by entity within €0.05.
- A current-close customer collection, supplier payment, or CAPEX spend has no corresponding supported source allocation.
- A movement row has a missing source ID or duplicates a source-line identity.
- A non-cash project GO_LIVE transfer is included as a cash CAPEX event.

No ledger balances, financial statement values, or tolerance levels are changed by this presentation layer.

## Where to explore

Open **Cash & Balance → Cash Flow → Contribution analysis**. Select an entity and the Free cash flow measure. The evidence table shows the line categories, division, counterparty or project, source record, and source journal ID. Click a row to inspect its complete allocation basis and identifiers.
