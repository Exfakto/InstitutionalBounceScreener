# Historical Strategy Validation

## Purpose

The historical strategy validation service measures whether past Institutional Bounce candidates showed forward trading edge after the screener signal. It is research infrastructure for v2.1 and does not change screening, scoring, portfolio, or UI behavior.

## Inputs

- Historical candidate rows or candidate-like objects.
- Price history rows with at least `date` and `close`.
- Optional `high` and `low` values for max gain and drawdown calculations.

Candidates should provide:

- `ticker`
- `signal_date` or `created_at`
- `final_score`, `primary_score_value`, or `score`

Price history can be passed as:

- a dictionary keyed by ticker, or
- a single list of price rows for one ticker.

## Outputs

The service returns a `StrategyValidationReport` containing:

- per-candidate `StrategyValidationSample` records
- forward return results by horizon
- max forward gain
- max forward drawdown
- aggregate average return
- aggregate median return
- aggregate win rate
- score bucket summaries
- warnings for incomplete samples

## Forward Return Horizons

The default horizons are:

- 5 trading days
- 10 trading days
- 20 trading days
- 60 trading days

The primary horizon for aggregate report statistics is currently 20 trading days.

## Lookahead-Bias Rule

The entry price is the first available trading row strictly after the candidate signal date. Same-day rows are not used for entry because the candidate may depend on information only known at or after that close.

Forward returns are measured from that entry close to the close after the requested number of trading days.

## Incomplete Samples

If insufficient forward data exists for a horizon, that horizon is marked incomplete. The sample remains in the report with warnings instead of failing validation. Aggregate statistics use only complete results for the selected horizon.

## Score Buckets

Primary-horizon results are grouped into:

- 90-100
- 80-89
- 70-79
- below 70

Each bucket reports sample count, completed count, average return, median return, and win rate.

## Current Limitations

- No persistence schema is added yet.
- No UI or dashboard panel is added yet.
- No transaction cost, slippage, or benchmark-relative return model is included yet.
- The service assumes clean, split-adjusted historical prices supplied by the caller.

## Next Steps

- Add repository-backed loading for historical screening runs and OHLCV data.
- Add optional benchmark-relative return calculations.
- Add export/report generation for validation batches.
- Add a future UI/controller integration once the service API stabilizes.
