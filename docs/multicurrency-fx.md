# Multi-Currency Accounting and FX Translation

Version 0.15 introduces functional-currency books and group translation for the multinational synthetic company.

## Why this layer exists

Earlier releases already maintained legal entities in Germany, Spain, the Czech Republic, China, the United States and Japan and downloaded monthly ECB FX rates. However, operating and accounting amounts were still represented directly in EUR. FX therefore acted as a macro input but not as a formal legal-book and consolidation layer.

Version 0.15 closes that gap.

## Functional currencies

| Entity | Functional currency |
| --- | --- |
| DE01 | EUR |
| ES01 | EUR |
| CZ01 | CZK |
| CN01 | CNY |
| US01 | USD |
| JP01 | JPY |

The existing EUR journal remains the reporting ledger. For every legal journal line, v0.15 creates a functional-currency equivalent using the monthly FX rate applicable to that close.

```text
Reporting EUR amount
/ FX value of one functional-currency unit in EUR
= Functional-currency amount
```

The full functional-currency journal is reproducible in runtime storage. A sample and local trial balances are published as audit outputs.

## FX source

Preferred source:

- ECB Data Portal monthly EXR reference rates

Fallback:

- deterministic synthetic FX curves already used by the macro layer

The pipeline therefore remains autonomous if the ECB endpoint is unavailable.

## Translation to EUR

The local trial balance is translated back to the group reporting currency using accounting-style translation rules.

### Assets and liabilities

Translated using the closing FX rate for each month.

### Share capital

Translated using the historical rate from the opening period retained by the model.

### Retained earnings

The legal local balance is translated as part of the equity roll-forward. The difference created by using closing rates for assets/liabilities and historical-equity treatment is not hidden inside retained earnings.

### Foreign Currency Translation Reserve

The translation difference is reported explicitly as:

```text
3300_FX_TRANSLATION_RESERVE
```

and economically represents CTA / OCI.

The translation equation is:

```text
Translated Assets
- Translated Liabilities
- Translated Equity before CTA
- FX Translation Reserve
= 0
```

CTA is therefore an identified foreign-currency equity reserve, not an unexplained balancing plug.

## Constant-currency management analysis

For the current close, foreign-entity Revenue and EBIT are also translated at the equivalent prior-year FX rate.

This produces:

```text
Reported Revenue
Constant-Currency Revenue
Revenue FX Effect

Reported EBIT
Constant-Currency EBIT
EBIT FX Effect
```

This allows management to distinguish operating performance from currency translation.

## Hard controls

Version 0.15 is blocked unless:

```text
Functional-currency journals balance
EUR -> local -> EUR round-trip is within cent precision
Translated Assets = Liabilities + Equity + CTA
Functional-currency journal exists
FX translation schedule exists
Constant-currency analysis exists
```

## Published outputs

```text
data/processed/functional_currency_journal_sample.csv
data/runtime/functional_currency_journal.csv.gz
data/processed/local_trial_balance.csv
data/processed/fx_translation.csv
data/processed/constant_currency_analysis.csv
```

The dashboard adds an `FX & Translation` view with closing FX, CTA, reported versus constant-currency Revenue and EBIT and translation-reserve trend.

## Deliberate limitation

Version 0.15 models **functional-currency books and group translation**. It does not yet model transaction-level FX remeasurement where an invoice is denominated in a currency different from the legal entity's functional currency.

Examples intentionally deferred:

- a USD customer invoice in a JPY functional-currency entity
- a CNY intercompany payable held by a EUR entity
- realized FX on settlement
- unrealized transaction FX gains/losses at month end

Those are separate from group translation and should be added as a dedicated foreign-currency transaction subledger rather than mixed into CTA.
