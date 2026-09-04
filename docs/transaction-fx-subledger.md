# Transaction FX Subledger

Version 0.20 adds document-level foreign-currency exposure to the existing functional-currency and Group translation model. It keeps transaction FX separate from CTA: CTA translates legal financial statements, while transaction FX remeasures a monetary receivable or payable denominated in a currency other than the entity's functional currency.

## Document population

The engine sources receivables and payables from actual journal lines in accounts `1100_AR`, `2100_AP`, `1150_IC_AR` and `2150_IC_AP`. Since v0.21, reciprocal intercompany contracts use the seller's functional currency on both legal legs, with a shared deterministic settlement month. Both source legs are retained in `intercompany_fx_contracts.csv`; only foreign-currency legs enter the FX document population. A stable deterministic policy selects external cross-currency contracts and assigns one of the supported currencies. No standalone balance is invented.

Each document records its source journal, issue and settlement month, entity, division, counterparty, source account, functional currency, transaction currency, original EUR and functional amount, transaction amount and payment term.

## Monthly remeasurement

Open documents are remeasured using the exact monthly rates already present in `macro.csv`:

```text
carrying functional amount = transaction amount × transaction FX to EUR / functional FX to EUR
```

The change from the prior functional carrying amount is a gain for receivables when positive and a gain for payables when negative. Each monthly functional gain or loss is translated to EUR using that month's functional-currency rate. Open movements are reported as unrealized; the settlement-month movement is realized.

## Outputs

- `transaction_fx_documents.csv`: one immutable row per source document.
- `transaction_fx_snapshots.csv`: one row per document and lifecycle month.
- `transaction_fx_summary.csv`: monthly exposure and P&L by entity and transaction currency.

## Release controls

The release fails on duplicate documents or snapshots, same-currency documents, missing valuation identity, lifecycle P&L differences or summary P&L differences. Since v0.21 it also checks complete key coverage, metadata, every summary measure, finite values, document source amounts, reciprocal contract source legs and all lifecycle snapshots. A coordinated change to both summary P&L components cannot evade detail-to-summary reconciliation. Transaction FX does not alter CTA and does not use balancing plugs.

Settlement months remain synthetic contract-policy dates, not a claim of matched bank settlement. This analytical layer is not posted into historical financial statements. The v0.21 contract-policy correction rebuilds analytical FX history and changes its population and totals; prior financial statement artifacts remain unchanged.

