# CAPEX cash and asset transfer

Published `capex` events have two distinct accounting meanings:

| Event | Entry | Cash effect |
| --- | --- | --- |
| `SPEND` | Debit 1510_CIP, credit 1000_CASH | Cash outflow |
| `GO_LIVE` | Debit 1500_PPE, credit 1510_CIP | None |

The project portfolio's Spend column sums only `SPEND` events. Previously it added `GO_LIVE` amounts too, incorrectly presenting noncash asset transfers as additional investment spending. Live status now follows the recorded `GO_LIVE` event, not merely a scheduled date.

The report shows cumulative cash spend, noncash transfers to PPE, and remaining construction in progress. Its visible project-event roll-forward checks `SPEND - GO_LIVE - remaining CIP = 0`; this is an event-level explanation, not a substitute for the engine's GL and cash-flow controls. Original project rows remain available in the report.

The paired factory panel replaces a sparse capacity table with the capacity-weighted utilization formula, site-level production/capacity bars and published capacity additions. It does not equate factory output with sales.
