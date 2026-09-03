# Macro Driver Lineage and Financial Sensitivities

Version 0.19 replaces the former all-synthetic economic-driver layer with exact-month official overlays and adds a controlled CFO sensitivity matrix. It does not silently interpolate unavailable public observations, mutate the Base forecast or post hypothetical entries to the ledger.

## Official source policy

| Driver | Preferred source | Applied unit |
| --- | --- | --- |
| Inflation | Eurostat HICP annual rate, EA20 | annual decimal rate |
| Industrial activity | Eurostat industrial production, manufacturing, calendar adjusted | 2021=100 |
| Energy | World Bank Commodity Price Data, Energy Index | 2010=100 |
| Policy rate | ECB main refinancing operations | annual decimal rate |
| FX | ECB monthly reference exchange rates | EUR per currency unit |

Every driver is retrieved independently. An official value replaces the calibrated fallback only when it matches the model month. Publication lags therefore remain visible instead of being hidden by forward filling. `macro_lineage.csv` records the close month, observation month, driver, applied value, unit, source, public URL and status.

The processed dataset committed by the production workflow is the monthly source snapshot. Git history therefore preserves revisions to official observations without requiring a separate paid data store.

## Controlled shocks

The sensitivity matrix uses the current 12-month Base forecast as an immutable baseline:

- Price +1%
- Volume +1%
- Industrial production -1%
- Inflation +100 bps
- Wage inflation +100 bps
- Energy index +10%
- Policy rate +100 bps
- EUR strengthening +5%

Price, demand, pass-through, wage, energy and cash-conversion elasticities are deterministic policies. Policy-rate exposure uses closing gross debt. EUR sensitivity is a translation-only view for non-EUR entities and deliberately reports no transaction-cash benefit or loss because transaction FX remeasurement remains outside v0.19.

Each shock reports Revenue, Gross Profit, OPEX benefit, EBIT, interest expense, Net Income, Ending Cash and Net Debt impact. Group Net Leverage and Interest Coverage deltas are derived from the current Base liquidity outlook.

## Interpretation rule

Sensitivity rows answer one-at-a-time questions. They are not probabilities, forecast scenarios or management overlays and must never be summed. Base, Upside and Downside remain the integrated forecast scenarios of record.

## Release controls

The release is blocked unless:

- every model month has one lineage row for each of the eight driver series;
- lineage rows are unique and use only Official or Fallback status;
- all eight controlled shocks are present;
- entity/division detail is unique and reconciles to Group summary;
- EBIT equals Gross Profit impact plus OPEX benefit within EUR 0.02;
- Net Debt impact offsets Ending Cash impact within EUR 0.02;
- shock directions are economically consistent; and
- every Group sensitivity is explicitly non-additive.
