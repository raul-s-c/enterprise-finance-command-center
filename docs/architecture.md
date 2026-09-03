# Architecture

Enterprise Finance Command Center models a fictional multinational group as a connected finance system rather than a collection of independently generated KPIs.

## Finance layers

1. Macro environment
2. Division-specific operating drivers
3. Operating activity by entity and division
4. Double-entry accounting
5. Legal-entity financial statements
6. Group consolidation and eliminations
7. Management P&L, Working Capital, Cash Flow and CAPEX
8. Rolling forecast and forecast vintages
9. CFO analytics and management commentary
10. Management action execution and benefits realization
11. Macro source lineage and controlled financial sensitivities
12. Transaction-currency document subledger and functional remeasurement

## Company model

Aureon Systems Group operates four divisions with deliberately asymmetric economics.

Software is recurring-revenue and headcount-led. Hardware is unit, material, capacity and inventory-led. Events is project and backlog-led. Spare Parts is SKU, installed-base and inventory-led.

The legal-entity structure is independent from the division structure so the same division can operate across several countries and entities.

## Accounting rule

Every financial event must enter the system through balanced journals. Derived statements are never populated separately. This makes financial reconciliation a release gate.

## Forecast rule

Each monthly close creates a new forecast vintage. Historical vintages will be retained at an analytical grain sufficient to calculate bias and forecast accuracy without keeping unnecessary transaction-level copies.

## Product evolution

The stateful product portfolio engine can launch, mature, place on watchlist and discontinue products according to measurable profitability, growth and working-capital criteria. These decisions alter future transactions rather than simply annotate the dashboard.

## Management action rule

Material adverse signals create persistent action cycles. Each cycle has one controlled execution plan. Approved interventions begin after the approval close and change only explicit operating drivers. Their consequences pass through the normal ledger and forecast chain. Directional trigger improvement is kept non-additive; additive portfolio benefit is measured only from the causal operating and forecast impact fields.

## Macro and sensitivity rule

Official macro observations replace deterministic values only for the same driver and observation month. Every applied value preserves source lineage and fallback status. Sensitivities use the current 12-month Base forecast as an immutable exposure baseline. Each shock is calculated independently, reconciles from entity/division detail to the Group view and is never combined with another shock or posted to the ledger.

## Transaction FX rule

Foreign-currency receivables and payables originate from source journal lines and remain separate from Group translation. Each document is remeasured monthly in the entity's functional currency; the movement is translated to EUR and classified as unrealized until settlement. Transaction FX analytics never use CTA or a balancing plug.
