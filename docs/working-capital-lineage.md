# Working-capital source lineage

The close publishes `working_capital_postings` (closing-month source movements)
and `working_capital_rollforward` (monthly legal account balances). Each posting
retains its journal ID, account, legal entity, division and available customer,
product and cash-flow metadata. The manifest records both population sizes.

The rollforward uses debit-positive signs: opening + debits - credits = closing.
Payables normally have negative balances. Carry-forward includes months without
activity. Final balances reconcile to the full source journal within the existing
EUR 0.05 working-capital tolerance. Missing identities and non-finite postings
fail publication.

These are legal gross-account movements, not consolidated net working capital.
Provisions, intercompany eliminations and consolidation inventory adjustments
remain separate. Supplier accrual journal IDs are not supplier invoice numbers.
Cash collections in the ledger are not bank-matched invoice settlements. The
published invoice-grain schedule applies aggregate cash credits using the
documented risk-aware oldest-receivable rule; each allocation is labelled as
modeled and is not evidence of a remittance advice or bank match.
The supplier aging derives synthetic suppliers from AP accrual rows. Its source
item detail keeps those journal IDs but does not reinterpret them as supplier
invoice numbers or assert that aggregate payments match individual invoices.
Inventory attribution remains analytical, not a physical warehouse lot register.

Use **Trace ledger** in a working-capital contribution screen to inspect the
selected legal scope's opening, debits, credits and closing balance. **Inspect
journal postings** opens source IDs and all available fields. Legacy artifacts
without the register retain their existing evidence controls.

Version 0.23 publishes `data/processed/ar_invoice_aging.csv`,
`data/processed/ar_invoice_applications.csv` and the lazy-loaded
`web/data/ar_invoice_detail.json`. The close reconciles invoice open balances
by customer and aging bucket to the customer AR schedule, and reconciles each
modeled application to its source AR credit journal. These are analytical
subledger allocations; no GL, cash flow or customer-level schedule is changed.

Version 0.24 publishes `data/processed/ap_item_aging.csv`,
`data/processed/ap_item_applications.csv` and the lazy-loaded
`web/data/ap_item_detail.json`. Source-accrual balances reconcile to supplier
AP by entity, division, supplier and aging bucket. Posted reductions use the
existing oldest-accrual, division-preference and supplier-priority policy.
These are controlled analytical allocations, not actual invoice or remittance
matches.

Remaining work: connect provisions and consolidation adjustments directly to
invoice-level net AR, and model matched customer/vendor settlement only if
remittance, invoice and bank-reference evidence becomes available.
