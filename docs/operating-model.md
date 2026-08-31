# Operating Model

The repository is designed to run without a paid backend.

## Monthly close

GitHub Actions runs on the second day of each month. The workflow closes through the previous completed calendar month.

The sequence is:

1. Install the Python package.
2. Run the automated test suite.
3. Refresh available public macro inputs.
4. Simulate the rolling operating history.
5. Build the double-entry ledger.
6. Derive legal and consolidated financial statements.
7. Recalculate working capital, CAPEX, factories and profitability.
8. Score historical forecast vintages.
9. Create the new rolling forecast vintage.
10. Run financial and forecasting controls.
11. Write compact analytical outputs.
12. Commit the refreshed data if it changed.
13. Publish the static CFO application through GitHub Pages.

## Determinism

A stable seed makes the synthetic enterprise reproducible. A rerun for the same close month produces the same synthetic operating history unless an approved live macro source contributes revised public data.

## Failure behaviour

The finance engine raises an exception when reconciliation controls fail. GitHub Actions therefore stops before publication. The previous valid Pages deployment remains available.

## Repository growth

The complete ledger is compressed as `journal.csv.gz` and only a small readable sample is stored uncompressed. Forecast vintages are retained at management analytical grain. This keeps the project sustainable as a long-lived public portfolio project.

## No paid services

The core solution requires no paid database, server, scheduler, BI service or AI API. GitHub stores code and data, GitHub Actions runs the monthly pipeline and GitHub Pages serves the analytical application.
