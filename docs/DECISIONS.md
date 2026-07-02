# Architecture Decisions

## 2026-06-29 - SQLite Is the Local Source of Truth

The application uses SQLite for local persistence of stocks, price history, indicators, support levels, bounce validations, fundamentals, and institutional metrics.

Reason:

- The project is a local desktop application.
- SQLite keeps setup simple.
- Tests can exercise persistence without external infrastructure.

## 2026-06-29 - Preserve Layered GUI to Database Architecture

The application follows:

```text
GUI -> Controllers -> Services -> DatabaseManager -> SQLite
```

Reason:

- Keeps PySide6 UI code thin.
- Makes analytics workflows testable.
- Prevents SQL and business logic from leaking into widgets.

## 2026-06-29 - Use Pure Analytics Calculators

Indicator, support, bounce, and score provider classes should calculate from supplied data only.

Reason:

- Pure calculators are easier to test.
- Services can orchestrate reads, writes, and summaries.
- Future engines can reuse the same calculators.

## 2026-06-29 - Use Plugin-Style Indicator and Scoring Foundations

The project introduced base classes and engine-style discovery/registration patterns for extensible indicators and score providers.

Reason:

- New analytics can be added without rewriting orchestration.
- Provider failures can be isolated.
- Future custom providers remain possible.

## 2026-06-30 - AnalysisPipeline Owns Candidate Ranking Orchestration

`AnalysisPipeline` runs candidate scoring across active tickers and returns ranked `CandidateScore` objects.

Reason:

- The GUI can run the screener through `ScoringController`.
- Candidate ranking is reusable outside the dashboard.
- Scoring formulas remain inside analysis providers.

## 2026-06-30 - CandidateTable Is a Reusable Widget

The ranked candidate table was extracted from `MainWindow` into `ui/widgets/candidate_table.py`.

Reason:

- Keeps `MainWindow` thinner.
- Centralizes table columns, formatting, sorting, selection, and double-click behavior.
- Supports the v2.0 professional dashboard refactor.

## 2026-06-30 - KpiStrip Owns Dashboard KPI Cards

The dashboard KPI/statistics cards were extracted into `ui/widgets/kpi_strip.py`.

Reason:

- Keeps KPI layout and formatting out of `MainWindow`.
- Supports a compact professional dashboard layout.
- Preserves existing statistic refresh behavior.

## 2026-06-30 - Gen 2 Intelligence Score Is Primary Screener Ranking

The screener ranks candidates by `institutional_bounce_score` from the Gen 2 Institutional Bounce Intelligence layer when that score is available. The legacy `composite_score` remains on `CandidateScore` and is used as the fallback ranking and display score when Gen 2 cannot be calculated.

Reason:

- Gen 2 combines the broader v2.1 intelligence components into the primary research signal.
- Legacy composite scoring remains useful for backward compatibility and safe fallback.
- Missing optional Gen 2 components should reduce confidence or produce warnings, not crash the screener.
- Gen 2 scores are read-only runtime outputs for now; no database persistence or schema changes are introduced.

## 2026-07-01 - Decision and Trade Planning Engines Remain Pure

Opportunity rating, institutional checklist, trade thesis, entry zone, stop loss, target projection, risk/reward, position sizing, portfolio statistics, and strategy analytics are implemented as pure analysis engines.

Reason:

- Keeps decision support deterministic and testable.
- Prevents database, service, and UI dependencies from entering calculation code.
- Allows dashboards and controllers to display or coordinate results without recalculating inside widgets.

## 2026-07-01 - Research, Trade, Journal, and Performance Widgets Are Passive

Research Preview, Trade Card, Watchlist Panel, Trade Journal Panel, and Performance Dashboard are UI widgets that render supplied data and emit user actions.

Reason:

- Preserves the boundary that widgets do not perform persistence, service calls, or business calculations.
- Keeps `MainWindow` responsible for composition and signal wiring.
- Supports stable UI tests that check behavior without coupling to implementation details.

## 2026-07-01 - Watchlist and Paper Trades Use Local SQLite

Watchlist items and paper trade journal entries are stored locally in SQLite through `DatabaseManager`, with services and controllers layered above.

Reason:

- Maintains the local-first desktop model.
- Keeps all SQL centralized in `DatabaseManager`.
- Provides durable workflow state without introducing external infrastructure.

## 2026-07-01 - Provider Abstraction Is the Boundary for External Data

The application uses provider interfaces, `ProviderResult`, `ProviderManager`, `ProviderConfig`, and `CacheManager` to isolate local and external data reads from services, analysis engines, and UI widgets.

Reason:

- Local SQLite workflows remain the default and continue to work without API keys.
- Optional external data access can be added behind providers without rewriting analysis or UI code.
- Successful provider responses can be cached to reduce repeated provider calls.
- Provider failures stay structured and safe for services to pass through.

## 2026-07-01 - Polygon Is Optional Price History Only

`PolygonProvider` supports daily OHLCV price history when `POLYGON_API_KEY` is available and selected through provider configuration. Other Polygon endpoints return not-yet-implemented `ProviderResult` failures.

Reason:

- Keeps secrets out of source and configuration files.
- Avoids implying unsupported provider endpoints are production-ready.
- Allows live price-history validation without changing scoring formulas, persistence, or UI behavior.

## 2026-07-02 - Live Refresh Remains Non-Persistent

Live dashboard refresh, market-status display, and watchlist quote updates are runtime UI/controller-service workflows. They do not write refreshed quote values to SQLite.

Reason:

- Preserves the local-first persistence model and avoids schema churn during beta.
- Keeps live provider behavior separate from durable watchlist and journal records.
- Failed refreshes can leave existing UI row values intact without corrupting stored data.

## 2026-07-02 - Beta Provider Calls Require Explicit User Configuration

Premium provider integrations are available only where implemented and require user-supplied environment variables or provider configuration. Tests rely on mocked responses.

Reason:

- Prevents secrets from entering source control.
- Keeps CI and local tests deterministic and offline.
- Makes provider normalization safe to evolve after beta feedback.
