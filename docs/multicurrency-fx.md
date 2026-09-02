# Multi-Currency Accounting and FX Translation

Version 0.15 introduces a functional-currency mirror and group translation layer for the multinational synthetic company.

## Why this layer exists

Earlier releases already maintained legal entities in Germany, Spain, the Czech Republic, China, the United States and Japan and downloaded monthly ECB FX rates. However, operating and accounting amounts were still represented directly in EUR. FX therefore acted as a macro input but not as a formal legal-book and consolidation layer.

Version 0.15 closes the translation gap while keeping the existing EUR economic ledger as the authoritative reporting ledger.

## Functional currencies

| Entity | Functional currency |
| --- | --- |
| DE01 | EUR |
| ES01 | EUR |
| CZ01 | CZK |
| CN01 | CNY |
| US01 | USD |
| JP01 | JPY |

For every legal journal line, v0.15 creates a functional-currency equivalent using the monthly FX rate applicable to that close.

```text
Reporting EUR amount
/ FX value of one functional-currency unit in EUR
= Functional-currency amount
```

Line-level conversion can create minor local-currency rounding differences. Those differences are resolved within the same journal entry, assigned to the largest line on the opposite side and exposed as a rounding adjustment. They do not create a P&L, retained-earnings or CTA plug.

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

Translated using the historical rate applicable when the capital movement arose. In the current model this is the opening-period rate because share capital is issued at opening and no later capital increases are simulated yet.

### Retained earnings

Retained earnings are **not** retranslated wholesale at each closing rate. Monthly movements into retained earnings are accumulated in EUR using the FX rate applicable when the underlying monthly profit arose. This preserves historical equity and isolates translation movements correctly.

### Foreign Currency Translation Reserve

The remaining translation difference is reported explicitly as:

```text
3300_FX_TRANSLATION_RESERVE
```

and economically represents CTA / OCI.

The translation equation is:

```text
Translated Assets
- Translated Liabilities
- Historical Translated Equity before CTA
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

This allows management to distinguish operating performance from the translation effect implied by changing reporting rates.

## Hard controls

Version 0.15 is blocked unless:

```text
Functional-currency journals balance after local rounding
EUR -> local -> EUR round-trip remains within disclosed rounding materiality
Translated Assets = Liabilities + Historical Equity + CTA
Functional-currency journal exists
FX translation schedule exists
Constant-currency analysis exists
```

The validation output also exposes the largest EUR-equivalent local-currency rounding adjustment rather than hiding it inside a general tolerance.

## Published outputs

```text
data/processed/functional_currency_journal_sample.csv
data/runtime/functional_currency_journal.csv.gz
data/processed/local_trial_balance.csv
data/processed/fx_translation.csv
data/processed/constant_currency_analysis.csv
```

The dashboard adds an `FX & Translation` view with closing FX, historical equity translation, CTA, reported versus constant-currency Revenue and EBIT and translation-reserve trend.

## Deliberate limitation

Version 0.15 models a **functional-currency mirror and group translation layer** over the existing EUR economic ledger. It does not yet model transaction-level FX remeasurement where an invoice is denominated in a currency different from the legal entity's functional currency.

Examples intentionally deferred:

- a USD customer invoice in a JPY functional-currency entity
- a CNY intercompany payable held by a EUR entity
- realized FX on settlement
- unrealized transaction FX gains/losses at month end

Those effects are separate from group translation and should be added as a dedicated foreign-currency transaction subledger rather than mixed into CTA.
