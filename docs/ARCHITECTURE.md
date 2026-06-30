# Architecture

## Overview

Institutional Bounce Screener is a local PySide6 desktop application backed by SQLite. It imports market data, calculates analytics, validates support-zone bounces, scores candidates, and displays ranked results in a GUI.

The design is intentionally layered so analytics and persistence remain testable outside the GUI.

## Layered Architecture

```text
GUI
Controllers
Services
DatabaseManager
SQLite
```

### GUI

The GUI lives in `ui/`.

Responsibilities:

- Build screens and widgets.
- Display statistics, candidate rows, status, progress, logs, and read-only details.
- Forward user actions to controllers.
- Avoid calculations, SQL, market downloads, and persistence logic.

Current UI modules:

- `main_window.py` - dashboard composition and signal wiring.
- `stock_detail_window.py` - read-only detail window.
- `widgets/candidate_table.py` - ranked candidate table.
- `widgets/kpi_strip.py` - compact KPI cards.
- `widgets/statistics_card.py` - reusable statistic card.
- `widgets/activity_log.py` - read-only activity log.
- `widgets/progress_panel.py` - status and progress bar.
- `theme.py` - early theme constants.

### Controllers

Controllers live in `controllers/`.

Responsibilities:

- Expose GUI-safe methods.
- Own or call services and orchestration objects.
- Keep scoring, calculations, and persistence out of the GUI.

### Services

Services live in `services/`.

Responsibilities:

- Run workflows such as price download, indicator calculation, support detection, bounce validation, and candidate scoring context assembly.
- Coordinate calculators and database reads/writes.
- Return structured summaries to controllers and the GUI.

### DatabaseManager

Database code lives in `database/`.

Responsibilities:

- Create and manage SQLite schema.
- Own all SQL.
- Use parameterized SQL.
- Return simple data structures or DataFrames to services.

### Domain Calculators

Pure calculation modules live in:

- `indicators/`
- `support/`
- `bounce/`
- `analysis/`

These modules should not read or write SQLite and should not call GUI code.

## Data Flow

### Market Data

1. GUI action calls `MarketController`.
2. Controller calls market service workflow.
3. Market helpers load universe or download prices.
4. `DatabaseManager` persists stocks and price history.
5. GUI refreshes KPI statistics.

### Indicators

1. GUI action calls `IndicatorController`.
2. Controller calls `IndicatorService`.
3. Service reads price history from SQLite.
4. Indicator calculators produce DataFrames.
5. Service persists rows through `DatabaseManager`.
6. GUI refreshes KPI statistics and logs a summary.

### Support Detection

1. GUI action calls `SupportController`.
2. Controller calls `SupportDetectionService`.
3. Service reads price history.
4. Swing lows are detected and clustered into support zones.
5. Strength and distance metrics are calculated.
6. Zones are saved through `DatabaseManager`.

### Bounce Validation

1. GUI action calls `BounceController`.
2. Controller calls `BounceValidationService`.
3. Service reads support zones and price history.
4. `BounceValidator` validates historical touches.
5. Metrics are saved through `DatabaseManager`.

### Candidate Scoring

1. GUI action calls `ScoringController`.
2. Controller owns `AnalysisPipeline`.
3. Pipeline reads active tickers through `ScoringService`.
4. `ScoringService` builds a read-only context from existing database metrics.
5. Score providers calculate individual `ScoreResult` objects.
6. `CompositeScore` calculates the overall score using `config/scoring.json`.
7. Pipeline returns ranked `CandidateScore` objects.
8. GUI displays rows in `CandidateTable`.

## UI Architecture

`MainWindow` is being reduced to composition and signal wiring. Reusable widgets should live under `ui/widgets/`.

Current extracted widgets:

- `CandidateTable`
- `KpiStrip`
- `StatisticsCard`
- `ActivityLog`
- `ProgressPanel`

Planned v2.0 UI components:

- Operations toolbar.
- Secondary activity/progress panel.
- Professional dark theme.
- Clear selected-row stock detail action.

## Analysis Pipeline

The analysis layer provides:

- Score provider base class and result model.
- Plugin-style score provider discovery in `ScoringEngine`.
- Individual score providers for quality, institutional, technical, support, and bounce metrics.
- `CompositeScore` weighted by `config/scoring.json`.
- `CandidateScore` value object.
- `AnalysisPipeline` to run scoring across active tickers and return ranked candidates.

Score providers must remain pure and must tolerate missing data by returning safe low or neutral results with warnings.

## Testing Philosophy

Tests should focus on behavior and architecture boundaries:

- Pure calculators get direct unit tests.
- Database methods get persistence tests.
- Services get workflow tests with controlled data.
- Controllers get thin coordination tests where practical.
- UI tests should cover stable reusable widgets, not brittle visual details.

Code changes should compile and pass the full test suite before completion.

## Architectural Rules

- GUI must not contain analytics logic.
- GUI must not read or write the database.
- Controllers must not calculate scores or indicators.
- Services may orchestrate workflows but should delegate persistence to `DatabaseManager`.
- SQL belongs only in `DatabaseManager`.
- Domain calculators must stay pure.
- Missing optional data must not crash workflows.
- Future modules must be clearly marked planned until source files exist.
