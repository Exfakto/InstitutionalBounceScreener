# Full Market Validation

## Summary

- Validation type: production integration validation
- Branch: `feature/v2.1-strategy-validation`
- Automated regression status: pending final full-suite run in this validation pass
- Live provider execution status: not executed in this sandboxed run
- Universe size: pending live provider run
- Overall status: REVIEW REQUIRED until live provider credentials are validated

## Call Path Under Validation

Primary Update Universe workflow:

```text
MainWindow.update_universe
-> MainWindow.run_full_market_universe_update
-> UniverseDownloaderService.update_universe
-> ProviderFactory.create
-> provider.fetch_universe_symbols
-> DatabaseManager.upsert_universe_symbols
-> DatabaseManager.deactivate_stale_universe_symbols
```

Full Market panel workflow:

```text
ScreeningResultsPanel.update_full_market_universe_requested
-> MainWindow.update_full_market_universe
-> MainWindow.run_full_market_universe_update
-> same UniverseDownloaderService path
```

Refresh Market Data workflow:

```text
MainWindow.refresh_full_market_data
-> FullMarketRefreshOrchestrator.refresh_all
-> UniverseDownloaderService.update_universe
-> HistoricalDataUpdateService.update_history
-> FundamentalDownloaderService.update_fundamentals
-> InstitutionalDataRefreshService.update_institutional_data
```

Full Market Scan workflow:

```text
MainWindow.run_full_market_scan
-> FullMarketScanRunner.run_scan
-> repository.fetch_eligible_universe_tickers
-> repository.fetch_ohlcv
-> ScreeningOrchestrator.run
```

## Instrumentation Added

`FullMarketValidationService` records each stage with:

- stage name
- elapsed time
- rows processed
- rows persisted
- skipped records
- warnings
- errors
- coverage snapshot
- throughput in rows/sec

Provider failures should be captured with provider, endpoint, ticker, and
exception details when those attributes are available on the exception object.

## Stage Validation Checklist

### Update Universe

Expected live outcome:

- Thousands of eligible NYSE/NASDAQ common stocks
- ETFs, ADRs, SPACs, preferred shares, warrants, rights, units, funds, trusts,
  and notes excluded
- Stale symbols deactivated

Current automated status:

- Synthetic validation covers processed, persisted, skipped, warnings, and
  coverage metrics.

### Refresh Market Data

Expected live outcome:

- Historical OHLCV downloaded for eligible universe tickers
- Throughput measured as rows/sec and tickers/sec where service details expose it
- Per-ticker failures captured and processing continues

Current automated status:

- Synthetic validation covers historical refresh throughput and persisted rows.

### Refresh Fundamentals

Expected live outcome:

- Fundamentals persisted where provider support exists
- Provider limitations reported as warnings rather than fatal pipeline failures

Current automated status:

- Synthetic validation covers optional service behavior and persisted rows.

### Refresh Institutional Data

Expected live outcome:

- Institutional records persisted where provider support exists
- Unsupported provider capability reported as a warning

Current automated status:

- Synthetic validation covers unsupported-provider warnings.

### Run Full Market Scan

Expected live outcome:

- Scan uses eligible tickers with OHLCV coverage
- Candidates generated from full universe coverage, not the 25-stock seed set
- Warnings/errors captured without aborting recoverable ticker-level failures

Current automated status:

- Synthetic validation covers processed ticker count, persisted candidate count,
  skipped records, and run metadata capture.

## Coverage Metrics

Live validation should record:

- `ticker_count`
- `ohlcv_covered_count`
- `scan_ready_count`
- `missing_ohlcv`
- `missing_fundamentals`
- `missing_institutional`
- `stale_data`
- coverage warnings

## Failures

No live provider failures were captured in this sandboxed validation pass.

## Warnings

- Live provider execution was not performed here.
- Production validation still requires configured provider credentials:
  - `POLYGON_API_KEY`
  - `FMP_API_KEY`
  - `FINNHUB_API_KEY`

## Performance

The validation harness measures:

- universe download time
- historical refresh throughput
- fundamental refresh throughput
- institutional refresh throughput
- screening throughput

Live performance numbers are pending a credentialed production run.

## Recommendations

- Run the validation harness or manual workflow with live credentials enabled.
- Confirm Update Universe produces a universe materially larger than 25 tickers.
- Confirm OHLCV coverage reaches an acceptable threshold before treating scan
  output as production-grade.
- Review provider warnings by provider, endpoint, and ticker after the first live
  run.
- Keep the legacy CSV import path as an explicit fallback/import utility only.
