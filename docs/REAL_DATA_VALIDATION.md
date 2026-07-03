# Real Data Validation

Real-data validation uses configured provider data or local CSV data. Tests should use mocked providers or local fixtures only.

## Local CSV Mode

Use `local_csv` when validating without API keys.

Expected behavior:

- Missing CSVs produce warnings.
- Existing cached OHLCV rows are reused.
- Individual ticker failures do not stop validation.

## Provider Mode

Provider mode may use Polygon, FMP, or Alpaca when credentials are configured.

Expected behavior:

- Missing credentials produce safe warnings.
- Rate-limit or provider failures are reported per ticker.
- Cached data remains available for screening/backtesting.

## Backtesting Readiness

Backtesting runs only when enough cached OHLCV data exists. Missing data should generate warnings, not crashes.
