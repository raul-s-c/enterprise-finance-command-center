# Enterprise Finance Command Center

End-to-end CFO analytics for a continuously evolving synthetic multinational company.

The project models economic activity first, translates it into double-entry accounting, consolidates legal entities, derives connected financial statements, creates rolling forecasts and publishes a CFO-oriented analytical application.

The synthetic group is Aureon Systems Group, with four divisions: Software, Hardware, Events & Projects and Spare Parts.

## Design principle

Macro environment -> Business drivers -> Operating events -> Double-entry ledger -> Consolidation -> P&L / Balance Sheet / Cash Flow -> Working Capital / CAPEX / Profitability -> Rolling forecast -> CFO analytics

Financial statements are outputs of one accounting source and are never generated as disconnected dashboard numbers.

## Current foundation

Version 0.1 includes:

- 36 rolling months of synthetic actuals
- 18-month rolling forecast
- six legal entities across Germany, Spain, Czech Republic, China, the United States and Japan
- four asymmetric business divisions
- deterministic macro and operating drivers
- double-entry accounting journals
- management P&L
- balance sheet and cash movement outputs
- CAPEX and depreciation mechanics
- receivables, payables and supplier/customer cash timing
- accounting validation gates
- automated tests
- scheduled GitHub Actions monthly close
- GitHub Pages CFO application shell

## Target scope

- P&L and management P&L
- Gross Profit and Marginal Contribution
- price / volume / mix
- Working Capital
- Balance Sheet
- Cash Flow and Free Cash Flow
- CAPEX and depreciation
- product and customer profitability
- factories and capacity
- intercompany and transfer pricing
- FX exposure
- forecast accuracy and bias
- product lifecycle and management decisions

## Architecture

The core system follows one direction of causality:

1. Macro environment
2. Business drivers
3. Operating activity
4. Balanced journal entries
5. Legal-entity financials
6. Consolidation
7. Management reporting
8. Rolling forecast
9. CFO analytics

See `docs/architecture.md` for the detailed design.

## Run locally

```bash
python -m pip install -e ".[dev]"
pytest
python -m enterprise_finance.cli build --end-month 2026-08
```

If `--end-month` is omitted, the pipeline closes through the previous completed calendar month.

## Automation

The repository includes a GitHub Actions workflow that runs on pushes, can be triggered manually and is scheduled monthly. The workflow tests the finance engine, generates the rolling dataset, commits refreshed outputs and deploys the web application to GitHub Pages.

The target operating model requires no paid database, paid backend or paid AI service.

## Synthetic data notice

Aureon Systems Group is fictional. Company names, transactions, customers, products and financial results are synthetic. Public macroeconomic data may be used as external drivers in later releases.
