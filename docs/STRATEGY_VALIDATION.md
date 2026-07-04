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

## Storage Model

Historical validation output can be persisted through `StrategyValidationRepository`.
The repository uses the existing SQLite `DatabaseManager` and does not introduce a
new persistence framework.

### Tables

`strategy_validation_runs`

- `id`
- `created_at`
- `strategy_name`
- `universe_size`
- `sample_count`
- `notes`

`strategy_validation_samples`

- `run_id`
- `ticker`
- `screen_date`
- `score`
- `score_bucket`
- `entry_price`
- `return_5d`
- `return_10d`
- `return_20d`
- `return_60d`
- `max_gain`
- `max_drawdown`
- `outcome`

Indexes are maintained for run lookup, ticker lookup, score bucket lookup, and
screen-date filtering.

## Repository Responsibilities

`StrategyValidationRepository` is responsible for:

- saving validation run metadata
- saving or updating validation samples
- loading recent validation runs
- loading samples by ticker
- loading samples by score bucket
- loading samples by screen-date range
- calculating lightweight summary statistics for stored samples

Duplicate samples are handled by `(run_id, ticker, screen_date)` upsert behavior,
so rerunning the same validation batch updates the existing sample instead of
creating duplicate rows.

## Analytics

`StrategyValidationAnalyticsService` computes research summaries from persisted
validation samples through `StrategyValidationRepository`.

The analytics report includes:

- overall performance
- forward return statistics for 5d, 10d, 20d, and 60d horizons
- score bucket performance
- sector performance when a `sector` field is available in sample rows
- outcome distribution

Overall performance includes total samples, completed samples, win rate, average
return, median return, average drawdown, average max gain, expectancy, and profit
factor when it can be calculated.

Forward return summaries include average, median, standard deviation, best, and
worst return for each horizon.

Analytics are intentionally presentation-neutral. The service returns lightweight
dataclasses and does not format results for UI display.

## Score Calibration Engine

`ScoreCalibrationService` evaluates how predictive each scoring component is
against stored forward-return outcomes. It is a research-only service and does
not update production model weights.

The calibration engine currently evaluates:

- overall score
- quality score
- institutional score
- technical score
- support score
- bounce score

For each component, the service calculates correlation against 5d, 10d, 20d,
and 60d forward returns. It also groups component scores into the standard score
buckets and reports sample count, win rate, average return, drawdown, and
expectancy for each bucket.

The service ranks components by predictive power and emits lightweight
recommendation objects:

- increase weight
- decrease weight
- keep current weight

Recommendations are intended for analyst review. They are not applied
automatically to scoring weights.

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

## Future Research Workflow

1. Load historical ranked candidates and historical OHLCV data.
2. Run `StrategyValidationService.validate(...)`.
3. Persist run metadata with `StrategyValidationRepository.save_run(...)`.
4. Persist sample-level outcomes with `save_samples(...)`.
5. Compare score buckets, horizons, and setup cohorts across stored runs.
6. Use `StrategyValidationAnalyticsService.analyze(...)` to summarize stored
   validation samples for research review.
7. Use `ScoreCalibrationService.calibrate(...)` to compare scoring-factor
   predictive power before proposing future model weight changes.
