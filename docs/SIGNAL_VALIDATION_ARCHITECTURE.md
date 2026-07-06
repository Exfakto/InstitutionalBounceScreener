# Signal Validation Architecture

v3.0.0 Phase 1 creates the permanent history layer for generated screening candidates. This is not a backtest. It records recommendations produced during real screening runs so the platform can evaluate its own live signal quality over time.

## Phase 1 Scope

Every completed screening run can now append generated candidates into `screening_signal_history`.

The history table stores:

- run identity and creation timestamp
- ticker and company context
- score snapshot at the time of generation
- price, support, entry, stop, and target fields when available
- signal status and notes
- empty outcome placeholders for future measurement windows

Existing screening logic, scoring, ranking, threading, and pipeline orchestration remain unchanged.

## Data Flow

1. `ScreeningOrchestrator` completes a screening run.
2. Existing ranked-candidate persistence continues through `save_ranked_candidates(...)`.
3. The orchestrator checks whether the repository supports `save_screening_run(...)`.
4. `DatabaseManager.save_screening_run(...)` appends each generated candidate to `screening_signal_history`.
5. Prior runs are not overwritten. Each run becomes a separate historical dataset.

If a repository does not support signal history, the screening run still completes. If signal-history persistence fails, the error is logged and screening stability is preserved.

## Repository API

The repository exposes:

- `save_screening_run(run_id, candidates, created_at=None, notes=None)`
- `fetch_screening_history(run_id=None, ticker=None, limit=100, offset=0)`
- `fetch_signal(signal_id)`
- `fetch_latest_signals(limit=20, offset=0)`

These methods are intentionally separate from ranked-candidate display persistence. Ranked candidates can still be replaced for a run, while signal history remains append-only.

## Outcome Placeholders

The following fields are stored as empty placeholders in Phase 1:

- `price_after_5d`
- `price_after_10d`
- `price_after_20d`
- `price_after_60d`
- `max_drawdown`
- `max_runup`
- `outcome`

They are reserved for future outcome evaluation and should not be populated by the screening run itself.

## V3.1 Outcome Evaluation

Version 3.1 should add a scheduled or manually triggered evaluator that:

1. reads unresolved signals from `screening_signal_history`
2. looks up cached OHLCV data after each signal timestamp
3. calculates 5, 10, 20, and 60 trading-day prices
4. calculates max drawdown and max runup
5. assigns an outcome classification
6. updates only the outcome fields

The evaluator should use cached market data and should not alter the original score snapshot.

## V3.2 Scoring Recalibration

Version 3.2 should use accumulated signal history to compare generated scores with measured outcomes.

Potential recalibration work:

- measure hit rate by score band
- measure drawdown by risk score band
- compare bounce score with support-hold outcomes
- compare technical score with forward returns
- identify score components that overstate signal quality
- propose weighting adjustments

Any recalibration should be implemented as a deliberate scoring change with tests, documentation, and before/after validation.

## Stability Rules

- Do not overwrite signal history from prior runs.
- Do not change current screening scores when recording history.
- Do not populate future outcome fields during signal generation.
- Do not make signal-history persistence a hard dependency for screening completion.
- Keep this layer provider-independent and local-data driven.
