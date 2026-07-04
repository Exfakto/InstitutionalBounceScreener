# Algorithm Validation

The algorithm validation subsystem measures how historical institutional bounce signals would have performed using cached local market data. It is intentionally separate from production scoring. Weight optimization reports candidate configurations, but it does not change application defaults automatically.

## Look-Ahead Bias Prevention

Historical replay builds each signal using only OHLCV rows with dates on or before the replay date. Forward rows are used only after the signal is created, during outcome labeling. This keeps the replay workflow deterministic and prevents future prices from influencing signal generation.

## Outcome Labeling

Each historical signal can be labeled with forward returns over configurable trading-day windows, defaulting to 5, 10, 20, and 60 rows. Labels also include max gain, max drawdown, profit-target hits, and stop-loss hits when enough cached forward OHLCV data exists.

## Factor Analysis

The validation service buckets support, bounce, technical, institutional, and final scores into score ranges. For each bucket it reports signal count, win rate, average return, median return, drawdown, and expectancy. This helps identify whether higher score bands are actually associated with better outcomes.

## Weight Optimization

The weight optimizer tests deterministic scoring-weight combinations across support quality, bounce history, technical confirmation, and institutional strength. Results are ranked by a simple objective that combines expectancy, win rate, average return, profit factor, and drawdown. The optimizer is advisory only.

## Walk-Forward Validation

Walk-forward validation splits labeled outcomes into training and testing windows. Weights are selected on the training window and evaluated on the out-of-sample testing window. This provides a more realistic view of whether a configuration is stable across time.

## Benchmark Comparison

If cached benchmark data exists, such as SPY, validation compares signal returns against benchmark forward returns. The report includes average excess return, alpha, and hit rate versus the benchmark. Missing benchmark data produces warnings rather than failures.

## Reports

Validation reports can be exported as JSON. Reports include summary metrics, factor bucket results, best weight configurations, walk-forward results, benchmark comparison, warnings, and errors.
