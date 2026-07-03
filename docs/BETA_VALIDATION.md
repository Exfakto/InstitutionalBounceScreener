# Beta Validation

Beta validation is the final local workflow before distributing a build.

## Validation Basket

The standard basket is:

```text
AAPL, MSFT, NVDA, AMZN, META, GOOGL, JPM, XOM, UNH, COST
```

## What It Checks

- Application startup readiness
- Database health
- Provider configuration
- OHLCV cache coverage
- Universe scan readiness
- Export directory readiness
- Release build artifacts when present
- Screening and backtest readiness when runners are configured

## UI Workflow

Open `About & Diagnostics`, then click `Run Beta Validation`.

The dialog shows:

- beta validation status
- report summary
- report location

## Outputs

The validation service exports:

- JSON summary report
- CSV issue list

Reports include timestamp, app version, provider, ticker coverage, scan result count, and backtest result count.
