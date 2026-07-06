# v2.2 Release Candidate Audit

Audit date: 2026-07-06

Blocker closeout update: Candidate Detail raw `N/A` fallbacks and technical-indicator per-ticker commits were addressed after this audit. Synchronous Candidate Detail loading remains intentionally deferred as v2.3 performance work.

Scope: current codebase after Technical, Bounce, Fundamental, and Risk analytics integration. This audit intentionally avoids production behavior changes and focuses on release risk, dead code, duplicate paths, placeholder leakage, thread safety, database migration risk, and coverage gaps.

## Executive Summary

The v2.2 analytics stack is broadly integrated: `IndicatorService.calculate_indicators()` now delegates to `TechnicalIndicatorEngine`, Candidate Detail assembles technical, bounce, fundamental, and risk data through `CandidateDetailDataService`, and database migration coverage exists for the expanded `technical_indicators` schema.

No critical release blocker was confirmed from code inspection. The main release risks are operational rather than architectural:

- Full `pytest -q` did not complete within the 5-minute local command timeout, so a longer CI run is required before tagging.
- Candidate Detail still has a few literal `N/A` paths in institutional fallback text and legacy generic metric tabs.
- Candidate Detail data assembly performs multiple synchronous database reads when opening a detail window; acceptable for RC if candidate counts are modest, but worth profiling.
- `DatabaseManager.save_technical_indicators()` commits per ticker even though `IndicatorService.calculate_technical_indicators()` commits at the end, which can slow full-universe indicator runs.

## Test Run

Command requested:

```powershell
.venv\Scripts\python.exe -m pytest -q
```

Result: timed out after approximately 304 seconds in this environment before producing a final pass/fail result.

Recent focused verification available from the current workspace:

- Candidate Detail and stock detail tests: 20 passed.
- Adjacent chart/detail/analytics tests: 71 passed.

Release recommendation: do not tag v2.2 until the full suite completes in CI or in a local run with a longer timeout.

## Findings By Severity

## Critical

No confirmed critical blocker found during this audit.

## High

### H1. Full regression suite did not complete in local audit window

Files involved:

- Test suite broadly
- CI/release process

Evidence:

- `pytest -q` timed out after approximately 304 seconds.

Risk:

- The current local audit cannot prove the full suite is green.
- Long-running tests may hide failures, hangs, or slow database/UI tests.

Recommended fix:

- Run `pytest -q` in CI or locally with a longer timeout.
- If runtime remains excessive, split release gates into fast unit, UI, integration, and slow/regression jobs.
- Add a documented maximum expected runtime for RC validation.

Safe to fix before release: Yes.

Defer: No. Full-suite verification should happen before release tagging.

## Medium

### M1. Candidate Detail still exposes some literal `N/A` text

Files involved:

- `ui/candidate_detail_window.py:1549`
- `ui/candidate_detail_window.py:2065`
- `tests/test_candidate_detail_window.py:268`

Evidence:

- Institutional summary fallback returns `Institutional sponsorship is N/A.`
- Generic `metrics_tab()` fallback still creates `QLabel("N/A")`.
- Tests currently assert the institutional `N/A` string, so the behavior is intentional but no longer aligned with the newer "Data not available" / "Institutional data not configured" language.

Risk:

- Candidate Detail can still look partially placeholder-like when institutional data is unavailable or when a generic metric tab is reused.
- This conflicts with the v2.2 acceptance goal of replacing generic `N/A` with clearer labels.

Recommended fix:

- Change institutional fallback to `Institutional data not configured.`
- Change generic metrics fallback to `Data not available`.
- Update tests that explicitly expect `N/A`.

Safe to fix before release: Yes, if limited to display text and tests.

Defer: Optional. This is visible polish, not a data correctness blocker.

### M2. Candidate Detail opens perform synchronous multi-service reads on the UI path

Status: Deferred to v2.3 performance work. Do not change for v2.2 unless release testing shows visible UI freezes.

Files involved:

- `ui/main_window.py:2383`
- `ui/main_window.py:2406`
- `services/scoring_service.py:119`
- `services/candidate_detail_data_service.py:28`
- `services/candidate_detail_data_service.py:38`
- `services/candidate_detail_data_service.py:121`
- `services/candidate_detail_data_service.py:180`
- `services/bounce_analytics_service.py:88`

Evidence:

- `open_stock_detail()` calls `candidate_detail_for_ticker()` directly before showing the dialog.
- `CandidateDetailDataService` reads universe data, fundamentals, OHLCV, technical indicators, support, bounce validations, institutional metrics, ranked candidates, and analytics services synchronously.
- Bounce analytics also fetches cached OHLCV.

Risk:

- Opening a candidate detail window can block the UI if the local database is large, on slower disks, or if ranked candidate history is large.
- The detail open path catches exceptions and returns `{}`, which prevents crashes but can mask performance/data problems.

Recommended fix:

- Before release, profile opening a candidate detail for a high-history ticker.
- If slow, add a small worker-backed load for Candidate Detail or cache the latest ranked candidate lookup.
- Log exceptions in `candidate_detail_for_ticker()` before returning `{}`.

Safe to fix before release: Logging/profiling is safe. Worker conversion is larger and should be deferred unless profiling proves a blocker.

Defer: Defer architectural async loading unless release testing shows visible UI freezes.

### M3. Technical indicator persistence commits once per ticker

Files involved:

- `services/indicator_service.py:27`
- `services/indicator_service.py:66`
- `services/indicator_service.py:72`
- `database/manager.py:651`
- `database/manager.py:755`

Evidence:

- `IndicatorService.calculate_technical_indicators()` loops over tickers, calls `db.save_technical_indicators(result)`, then commits at the end.
- `DatabaseManager.save_technical_indicators()` also calls `self.connection.commit()`.

Risk:

- Full-universe technical indicator runs may be slower than necessary.
- The service-level final commit gives the appearance of batch persistence, but actual writes are committed per ticker.

Recommended fix:

- For RC, leave behavior unchanged unless performance testing shows indicator runs are too slow.
- Post-RC, add a batch mode or optional `commit=False` argument and commit once per full calculation.

Safe to fix before release: Only if done narrowly and covered by database tests.

Defer: Yes, unless full-universe runtime is a release blocker.

### M4. Legacy SMA-only path remains callable and appears in older workflow tests

Files involved:

- `services/indicator_service.py:103`
- `database/manager.py:788`
- `tests/test_end_to_end_workflows.py:305`
- `tests/test_indicator_service.py:62`

Evidence:

- `calculate_sma()` and `save_sma()` remain for backward compatibility.
- `calculate_indicators()` correctly routes to v2.2 technical indicators, but older tests still exercise `calculate_sma()` directly.

Risk:

- A user or older workflow could still run the SMA-only path and overwrite rows in `technical_indicators` with only SMA values for the same ticker/date.

Recommended fix:

- Keep the methods for backward compatibility as requested.
- Add documentation or UI labeling that `calculate_indicators()` is the production v2.2 path and `calculate_sma()` is legacy.
- Consider adding a warning log in `calculate_sma()`.

Safe to fix before release: Documentation and logging are safe.

Defer: Do not remove the path before release.

## Low

### L1. Duplicate OHLCV row normalization exists in multiple services

Files involved:

- `services/ohlcv_cache_access.py:18`
- `services/indicator_service.py:82`
- `services/candidate_detail_data_service.py:144`

Evidence:

- OHLCV frame-to-row conversion is implemented in the canonical cache helper, the indicator service, and Candidate Detail data service.

Risk:

- Low immediate risk, but future schema changes could drift across implementations.

Recommended fix:

- Post-RC, reuse `frame_to_ohlcv_rows()` from `services/ohlcv_cache_access.py` where practical.

Safe to fix before release: Yes, but not necessary.

Defer: Yes.

### L2. Non-detail UI panels intentionally retain placeholder wording

Files involved:

- `ui/widgets/candidate_chart_panel.py:33`
- `ui/widgets/candidate_chart_panel.py:76`
- `ui/widgets/candidate_chart_panel.py:155`
- `ui/widgets/candidate_chart_panel.py:157`
- `ui/settings_dialog.py:323`
- `ui/settings_dialog.py:325`

Evidence:

- Candidate chart panel labels itself as a placeholder preview.
- Settings dialog includes placeholder choices for light theme and font scaling.

Risk:

- These do not directly affect Candidate Detail v2.2 analytics, but they can make the overall RC feel unfinished.

Recommended fix:

- Leave as deferred polish unless these panels are in the RC demo path.
- If included in demo, rename placeholder wording to "Preview unavailable" or hide unimplemented settings.

Safe to fix before release: Yes for wording only.

Defer: Yes if outside release-critical workflows.

### L3. Ranked candidate lookup is linear over latest candidates

Files involved:

- `services/candidate_detail_data_service.py:180`
- `database/manager.py:1963`

Evidence:

- `fetch_ranked_candidate()` calls `fetch_latest_ranked_candidates()` and scans in Python for the selected ticker.

Risk:

- Usually low, but a large latest screening run could make Candidate Detail open slower.

Recommended fix:

- Add a repository method for latest ranked candidate by ticker after RC.

Safe to fix before release: Requires new database method and tests; not necessary unless profiling shows a problem.

Defer: Yes.

### L4. Candidate Detail chart was added inline to the dialog

Files involved:

- `ui/candidate_detail_window.py:20`

Evidence:

- `InteractiveCandlestickChart` now lives inside `candidate_detail_window.py`.

Risk:

- Low runtime risk, but it increases the size and responsibility of the dialog file.

Recommended fix:

- Post-RC, move the chart widget to a dedicated `ui/widgets` module and add targeted paint/interaction tests.

Safe to fix before release: No need.

Defer: Yes.

## Positive Findings

- v2.2 technical indicator persistence has schema migration coverage:
  - `database/manager.py:582`
  - `database/schema.py:218`
  - `tests/test_chart_database.py:159`
- `IndicatorService.calculate_indicators()` now routes through `calculate_technical_indicators()`:
  - `services/indicator_service.py:20`
  - `services/indicator_service.py:27`
  - `tests/test_indicator_service.py:94`
- Thread-owned repository behavior is covered for indicator workers:
  - `tests/test_main_window.py:1504`
  - `tests/test_main_window.py:1518`
- Candidate Detail has focused coverage for populated NEE-style analytics:
  - `tests/test_stock_detail_data.py:278`
  - `tests/test_stock_detail_data.py:319`

## Recommended Release Fix Order

1. Run full `pytest -q` to completion in a longer CI/local window.
2. Fix Candidate Detail visible `N/A` strings in institutional fallback and generic metrics fallback.
3. Add logging around swallowed Candidate Detail load exceptions.
4. Profile Candidate Detail open time for a ticker with full OHLCV and analytics history.
5. If indicator runtime is excessive, consider a narrow batch-commit optimization; otherwise defer.

## Release Blocker Assessment

Block release until resolved:

- Full test suite must complete and pass.

Safe pre-release fixes:

- Candidate Detail fallback wording.
- Logging swallowed detail-load exceptions.
- Documentation clarifying `calculate_sma()` as legacy.

Defer:

- Batch indicator commit refactor.
- Dedicated ranked-candidate-by-ticker query.
- Moving chart widget out of `candidate_detail_window.py`.
- Broad UI placeholder cleanup outside Candidate Detail.
