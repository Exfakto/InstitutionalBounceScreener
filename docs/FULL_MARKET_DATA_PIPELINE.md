# Full Market Data Pipeline

## Purpose

The full-market pipeline discovers eligible NYSE and NASDAQ common stocks,
persists the universe master list, refreshes market data, and enables full-market
screening beyond the seed ticker set.

## Provider Priority

Universe discovery uses the existing provider architecture with this priority:

1. Polygon
2. Financial Modeling Prep
3. Finnhub
4. Local database fallback

Provider output is normalized into records with ticker, company name, exchange,
security type, sector, industry, market cap, price, average volume, average
dollar volume, active flag, and source when available.

## Required Environment Variables

- `POLYGON_API_KEY`
- `FMP_API_KEY`
- `FINNHUB_API_KEY`

Only one configured live provider is required for discovery. Polygon is the
preferred source because its reference tickers endpoint supports active stock
pagination.

## Universe Source And Expected Counts

The target universe is active NYSE and NASDAQ common stocks. Live provider row
counts vary by plan, exchange definitions, and timing, but a healthy production
run should populate thousands of eligible records rather than the 25-stock seed
dataset.

## Filtering Rules

Eligible rows must be active NYSE or NASDAQ common stocks/equities.

Excluded rows include:

- ETF
- ADR
- SPAC
- preferred shares
- warrants
- rights
- units
- funds
- trusts
- notes

The downloader de-duplicates by ticker and exchange before persistence and
deactivates stale universe symbols that no longer appear in the latest provider
result.

## Limitations

- Sector, industry, market cap, price, and volume fields depend on provider
  availability.
- Provider API limits can return partial results; usable completed pages are
  preserved where provider behavior allows it.
- Full-market scans still depend on historical price coverage after universe
  discovery.

## Manual Validation

1. Start the application.
2. Open Results / Full Market controls.
3. Click Update Universe.
4. Confirm the universe count grows beyond 25.
5. Refresh market data.
6. Run a full market scan.
