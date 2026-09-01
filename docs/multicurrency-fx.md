# Native Operating FX, Translation and Constant Currency

Version 0.15 introduces genuine FX sensitivity into the multinational operating model and adds functional-currency translation analytics.

## Why this layer exists

Earlier releases already maintained legal entities in Germany, Spain, the Czech Republic, China, the United States and Japan and downloaded monthly ECB FX rates. However, operating amounts were generated directly in EUR. FX could therefore be displayed as a macro driver without changing reported Revenue or cost in a genuinely local-currency way.

Version 0.15 changes that operating assumption.

The pre-FX operating model is retained as a **constant-currency economic base**. A fixed calibration FX converts that base into stable local-currency price and cost levels. Those native amounts are then translated each month using the current ECB/fallback FX rate.

```text
Constant-currency economic base
/ fixed calibration FX
= Native functional-currency economics

Native functional-currency economics
x monthly closing/reporting FX
= Reported EUR economics
```

As a result, volume and local economics can remain unchanged while reported EUR performance moves because FX moved.

## Functional currencies

| Entity | Functional currency |
| --- | --- |
| DE01 | EUR |
| ES01 | EUR |
| CZ01 | CZK |
| CN01 | CNY |
| US01 | USD |
| JP01 | JPY |

The calibration rates are explicit in `config/fx-policy.yml`. They are structural anchors, not monthly reporting rates.

## Operating FX origination

### Commercial Revenue

Revenue originates in the functional currency of the selling entity.

US commercial activity therefore originates in USD and Japanese commercial activity in JPY. Germany and Spain remain EUR-native.

### Commercial selling cost and OPEX

Variable selling cost and non-people operating cost originate in the commercial entity currency.

Workforce capacity is driven by constant-currency business demand so an FX movement cannot create artificial hiring or attrition. Workforce monetary cost, however, originates in the entity functional currency and is translated into reported EUR.

This deliberately separates:

```text
Underlying productivity / FTE decision
from
Reported EUR payroll translation
```

### Manufacturing cost

For Hardware and Spare Parts, manufacturing cost originates in the source-factory currency rather than the selling-entity currency.

```text
CZ01 factory -> CZK manufacturing cost
CN01 factory -> CNY manufacturing cost
```

Commercial Revenue and factory manufacturing cost can therefore carry different FX exposures within the same product sale.

## ECB and fallback FX

Preferred source:

- ECB Data Portal monthly EXR reference rates

Fallback:

- deterministic synthetic FX curves already used by the macro layer

The pipeline remains autonomous if the ECB endpoint is unavailable.

## Functional-currency reporting mirror

The existing double-entry reporting journal remains the authoritative EUR accounting ledger in v0.15. For translation analysis, every legal journal line is also expressed in the legal entity's functional currency using the monthly FX rate.

```text
Reporting EUR journal amount
/ monthly FX-to-EUR
= Functional-currency reporting view
```

Line-level conversion can create local-currency cent rounding. The functional-currency view is rebalanced inside the same journal entry and the local rounding adjustment is explicitly exposed. It does not create a P&L, retained-earnings or CTA plug.

This layer provides local trial balances and translation analytics. It should not yet be described as a fully native monetary-item subledger because transaction-currency remeasurement remains outside v0.15.

## Translation to EUR and CTA

The functional-currency trial-balance view is translated using accounting-style group-translation rules.

### Assets and liabilities

Closing rate.

### Share capital

Historical rate applicable when the capital movement arose.

### Retained earnings

Accumulated using historical monthly profit rates rather than wholesale retranslation at every close.

### Foreign Currency Translation Reserve

The remaining translation difference is reported explicitly as:

```text
3300_FX_TRANSLATION_RESERVE
```

representing CTA / OCI.

```text
Translated Assets
- Translated Liabilities
- Historical Translated Equity before CTA
- FX Translation Reserve
= 0
```

CTA is therefore an identified translation reserve, not an unexplained balancing plug.

## Constant-currency management analysis

Current Revenue and EBIT can be translated at the equivalent prior-year rate:

```text
Reported Revenue
Constant-Currency Revenue
Revenue FX Effect

Reported EBIT
Constant-Currency EBIT
EBIT FX Effect
```

Because the underlying operating flows now originate from stable functional-currency economics, this bridge represents a real reporting-currency effect rather than a cosmetic conversion of an EUR-only business model.

## Hard controls

Version 0.15 will be blocked unless:

```text
Native local Revenue x monthly FX = Reported EUR Revenue
EUR entities remain unchanged by FX translation
FX shocks change foreign reported EUR but not local business economics
Workforce FTE / hires / attrition are invariant to pure FX shocks
Reported foreign Workforce cost moves with FX
Physical manufacturing cost follows source-factory currency
Reported OPEX = translated payroll + translated non-people OPEX
Functional-currency journal views remain balanced
EUR -> local -> EUR reporting round-trip stays within disclosed cent rounding
Translated Assets = Liabilities + Historical Equity + CTA
Constant-currency analysis exists
```

## Published outputs

Planned/current v0.15 outputs include:

```text
data/processed/functional_currency_journal_sample.csv
data/runtime/functional_currency_journal.csv.gz
data/processed/local_trial_balance.csv
data/processed/fx_translation.csv
data/processed/constant_currency_analysis.csv
```

The dashboard adds `FX & Translation` with current FX rates, CTA/OCI, reported versus constant-currency Revenue/EBIT and translation-reserve history.

## Deliberate limitations

Version 0.15 does **not** yet model transaction-currency remeasurement for monetary items denominated in a currency different from the legal entity functional currency.

Examples deferred to a dedicated subledger:

- USD customer invoice inside a JPY functional-currency entity
- CNY intercompany payable held by an EUR entity
- realized FX on settlement
- unrealized FX gains/losses on monetary items at month end

It also does not claim that every historical Balance Sheet item was originally posted from a native functional-currency monetary subledger. v0.15 makes the operating business genuinely FX-sensitive and provides group-translation analytics; transaction remeasurement and fully native monetary balance origination are a separate accounting problem and will be implemented separately rather than hidden inside CTA.
