# Architecture

## Overview

Institutional Bounce Screener is a local-first PySide6 desktop application backed by SQLite. It imports market data, calculates analytics, validates support-zone bounces, scores candidates, supports institutional decision review, plans trades, tracks watchlist and paper trade records, and displays portfolio analytics.

The design is intentionally layered so analytics, persistence, services, and UI widgets remain independently testable.

## Layered Architecture

```text
UI widgets
Controllers
Services
Providers
DatabaseManager
SQLite
```

Pure analytics live beside this workflow and are called by services or pipelines when orchestration is required. Provider infrastructure is intentionally separate from analysis and UI code.

## UI Layer

The UI lives in `ui/` and reusable widgets live in `ui/widgets/`.

Responsibilities:

- Display supplied data.
- Emit user actions.
- Keep `MainWindow` focused on composition and signal wiring.
- Avoid SQL, service calls from widgets, market downloads, scoring formulas, and analytics calculations.

Current major widgets include:

- `CandidateTable`
- `KpiStrip`
- `OperationsToolbar`
- `HeaderBar`
- `ActivityPanel`
- `PriceChart`
- `ResearchPreview`
- `TradeCard`
- `WatchlistPanel`
- `TradeJournalPanel`
- `PerformanceDashboard`

## Controller Layer

Controllers live in `controllers/`.

Responsibilities:

- Provide GUI-safe methods.
- Own service instances.
- Coordinate workflows without direct SQL or analytics formulas.

Current controller areas include market data, indicators, support detection, bounce validation, scoring, chart data, watchlist, and trade journal workflows.

## Service Layer

Services live in `services/`.

Responsibilities:

- Own business workflows.
- Coordinate database reads/writes through `DatabaseManager`.
- Call pure calculators when workflow orchestration is needed.
- Return structured results to controllers.

Service areas include market workflows, indicator calculation, support detection, bounce validation, scoring context assembly, composite intelligence, chart data, watchlist persistence, trade journal persistence, live provider data access, and scheduled refresh orchestration.

`LiveDataService` is the service boundary for provider-backed reads. `RefreshScheduler` periodically refreshes registered tickers through `LiveDataService` and reports results through callbacks without importing UI code.

## Provider Layer

Provider code lives in `providers/`.

Responsibilities:

- Define data-provider interfaces.
- Normalize provider results into `ProviderResult`.
- Route calls through `ProviderManager`.
- Cache successful provider responses through `CacheManager`.
- Load active-provider settings through `ProviderConfig`.

Current providers:

- `LocalProvider` reads local database-backed data where available.
- `PolygonProvider` supports daily OHLCV price history when configured with `POLYGON_API_KEY`.

Providers must not perform scoring, analysis calculations, UI work, controller coordination, database writes, or secret storage. Polygon endpoints beyond price history remain not-yet-implemented until added in source.

## Database Layer

Database code lives in `database/`. `DatabaseManager` owns all SQL and uses SQLite as the local persistent store.

Current schema areas include:

- `stocks`
- `price_history`
- `technical_indicators`
- `support_levels`
- `bounce_validations`
- `fundamentals`
- `institutional_metrics`
- `earnings`
- `watchlist`
- `paper_trades`

The application remains local-first. Optional provider-backed reads are infrastructure additions and do not replace SQLite persistence or analysis workflows.

## Analysis Engines

Pure calculation modules live in:

- `indicators/`
- `support/`
- `bounce/`
- `analysis/`

Implemented analysis areas include:

- Technical and support scoring.
- Bounce validation metrics.
- Candidate scoring and composite intelligence.
- Opportunity rating.
- Institutional checklist.
- Trade thesis generation.
- Entry zone, stop loss, target projection, risk/reward, and position sizing.
- Portfolio statistics.
- Strategy analytics.

Pure calculators must not read SQLite, call services, or import UI code.

## Primary Data Flow

### Screening

1. UI action calls `ScoringController`.
2. Controller runs `AnalysisPipeline`.
3. Pipeline and scoring service build read-only contexts from existing SQLite data.
4. Analysis providers calculate score results.
5. Composite intelligence and decision-support engines enrich `CandidateScore`.
6. UI widgets display ranked candidates and read-only decision details.

### Chart Workspace

1. Candidate selection triggers chart update in `MainWindow`.
2. `ChartController` retrieves chart data through its service.
3. `PriceChart` renders supplied price, support, and bounce context.

### Watchlist and Journal

1. UI panels emit user actions.
2. `MainWindow` calls the appropriate controller.
3. Controllers delegate to services.
4. Services persist through `DatabaseManager`.
5. Panels refresh from supplied rows.

### Performance Analytics

Portfolio and strategy analytics are pure analysis engines. The current dashboard widget is read-only and expects precomputed statistics. It does not query the database or run analytics itself.

### Provider-Backed Data

1. A service calls `LiveDataService`.
2. `LiveDataService` validates and normalizes the ticker.
3. `ProviderManager` checks `CacheManager`.
4. On cache miss, the active provider retrieves data.
5. Successful `ProviderResult` values are cached and returned.
6. Failed provider results pass through safely and are not cached.

## Testing Philosophy

Tests focus on behavior and architecture boundaries:

- Pure calculators get direct unit tests.
- Database methods get persistence tests.
- Services get workflow tests with controlled data.
- Controllers get delegation and coordination tests.
- UI tests cover stable reusable widgets without relying on fragile visual details.

Before completing code changes, run the full test suite and compile check.

## Architectural Rules

- UI widgets must not contain analytics logic.
- UI widgets must not read or write the database.
- Controllers coordinate; they do not calculate.
- Services own business workflows and delegate SQL to `DatabaseManager`.
- SQL belongs only in `DatabaseManager`.
- Pure analysis engines must stay free of database, service, and UI dependencies.
- Missing optional data must not crash workflows.
- Planned integrations must remain clearly marked as planned until implemented.
