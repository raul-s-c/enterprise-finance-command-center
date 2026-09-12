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
Cash collections in the ledger are not bank-matched invoice settlements.
Inventory attribution remains analytical, not a physical warehouse lot register.

Remaining work: expose the source register in the evidence inspector, add
invoice-level settlement allocations with explicit policy and reconciliation,
and connect provisions and consolidation adjustments to the net balance.
