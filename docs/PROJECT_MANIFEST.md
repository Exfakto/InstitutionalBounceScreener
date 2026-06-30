# Project Manifest

## Purpose

Institutional Bounce Screener is a local desktop research application for finding U.S. stocks that may be strong institutional bounce candidates.

The app combines market data, technical indicators, support-zone detection, bounce validation, fundamentals, institutional metrics, and candidate scoring into a PySide6 workstation.

## Current Status

- Current active track: v2.0 Professional Dashboard, in progress.
- Latest completed UI work: reusable `CandidateTable` and compact `KpiStrip`.
- Core analytics foundation: v1.0 support and bounce engines completed.
- Candidate scoring foundation: v1.1 analysis pipeline and score providers completed.
- Last known full test status: passing with 88 tests.

## Repository Structure

- `app.py` - primary application entry point.
- `main.py` - compatibility entry point.
- `ui/` - PySide6 user interface.
- `ui/widgets/` - reusable dashboard widgets.
- `controllers/` - GUI-to-service coordination.
- `services/` - workflow orchestration and business use cases.
- `database/` - SQLite schema and `DatabaseManager`.
- `market/` - universe loading and market data download helpers.
- `indicators/` - indicator calculation framework and SMA source implementation.
- `support/` - swing-low detection, support-zone clustering, and support scoring.
- `bounce/` - historical bounce validation logic.
- `analysis/` - scoring framework, score providers, candidate model, and pipeline.
- `fundamentals/` - CSV importer for fundamental metrics.
- `institutional/` - CSV importer for institutional metrics.
- `config/` - settings, logging, and scoring weights.
- `data/` - local CSV inputs, sample price data, and generated local data.
- `tests/` - unit tests for analytics, persistence, services, controllers, and stable UI widgets.
- `docs/` - project governance and planning documents.

## Major Modules

### UI

- `ui/main_window.py` builds the current dashboard and wires user actions to controllers.
- `ui/stock_detail_window.py` displays read-only candidate detail data.
- `ui/widgets/candidate_table.py` displays ranked candidates.
- `ui/widgets/kpi_strip.py` displays compact KPI cards.
- `ui/widgets/statistics_card.py`, `activity_log.py`, and `progress_panel.py` provide smaller reusable controls.
- `ui/theme.py` currently contains early theme constants; the full dark theme is planned.

### Controllers

Controllers expose GUI-safe methods and delegate work to services or analysis orchestration:

- `market_controller.py`
- `indicator_controller.py`
- `support_controller.py`
- `bounce_controller.py`
- `scoring_controller.py`
- `application_controller.py`

### Services

Services own workflows:

- Market universe import and price download.
- Indicator calculation and persistence.
- Support detection and persistence.
- Bounce validation and persistence.
- Candidate scoring context assembly and read-only detail data.

### Database

SQLite is the local source of truth. `DatabaseManager` owns SQL access. Schema tables include:

- `stocks`
- `price_history`
- `technical_indicators`
- `support_levels`
- `bounce_validations`
- `fundamentals`
- `institutional_metrics`

### Analysis

The scoring layer includes:

- `BaseScore`
- `ScoreResult`
- `ScoringEngine`
- `QualityScore`
- `InstitutionalScore`
- `TechnicalScore`
- `SupportScore`
- `BounceScore`
- `CompositeScore`
- `CandidateScore`
- `AnalysisPipeline`

## Completed Modules

- PySide6 desktop shell.
- Market universe import.
- Market price download.
- SQLite persistence layer.
- SMA indicator workflow.
- Support Detection Engine.
- Bounce Validation Engine.
- Fundamentals and institutional CSV importer foundations.
- Candidate scoring providers and composite score.
- Analysis pipeline for ranked candidates.
- Run Screener dashboard workflow.
- Read-only stock detail window.
- Candidate table widget extraction.
- Compact KPI strip extraction.

## In Progress

- v2.0 Professional Dashboard.
- Dark visual system.
- Operations toolbar.
- Secondary activity/progress panel.
- Main window layout recomposition.
- Stock detail access polish.

## Planned

- v2.1 chart and research workspace.
- v2.2 deeper institutional intelligence.
- v3.0 strategy lab and backtesting.
- Expanded sourced implementations for technical indicators beyond current SMA source, where needed.

## Dependencies

Runtime dependencies are listed in `requirements.txt`:

- PySide6
- yfinance
- pandas

The project also uses Python standard library modules including `sqlite3`, `dataclasses`, `datetime`, `logging`, and `pathlib`.

## Test Status

The test suite is based on `pytest`. Current coverage includes:

- Indicator calculations.
- Support detection calculations.
- Bounce validation calculations.
- Database persistence methods.
- Service workflows.
- Scoring providers and scoring engine.
- Analysis pipeline.
- Controller behavior where practical.
- Stable UI widgets such as `CandidateTable` and `KpiStrip`.

Before completing code changes, run:

```powershell
.venv\Scripts\python.exe -m compileall app.py main.py controllers services support bounce database ui analysis tests
.venv\Scripts\python.exe -m pytest
```
