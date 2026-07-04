# Project Manifest

## v2.0 Release-Candidate Architecture Update

The current release-facing architecture is validated as a v2.0 release candidate. The active dependency direction is:

```text
Repository -> Services -> Controllers -> UI
```

Release-critical subsystems now include Provider resilience, full-market screening, screening diagnostics, results export, Model calibration, production readiness, Release Candidate Validation, and end-to-end workflow validation.

The repository architecture audit is documented in `docs/repository_architecture_audit.md` and enforced by `tests/test_repository_architecture_audit.py`.

## Purpose

Institutional Bounce Screener is a local desktop research workstation for identifying, evaluating, planning, and tracking institutional bounce opportunities in U.S. stocks.

The app combines market data, technical indicators, support-zone detection, bounce validation, fundamentals, institutional metrics, candidate scoring, decision support, trade planning, watchlists, paper trade journaling, and analytics into a PySide6 application backed by SQLite.

## Current Status

- Current active track: v2.0 release-candidate readiness.
- Completed through: production readiness, Release Candidate Validation, provider resilience, model calibration, full-market workflow validation, and end-to-end workflow validation.
- Current architecture: local-first SQLite, Repository -> Services -> Controllers -> UI workflow, provider abstractions, and pure analysis engines.
- Optional premium provider foundations exist behind provider configuration and environment variables. Tests use mocked provider responses and must not require API keys.

## Repository Structure

- `app.py` - primary application entry point.
- `main.py` - compatibility entry point.
- `ui/` - PySide6 user interface.
- `ui/widgets/` - reusable dashboard, decision, trade, watchlist, journal, and performance widgets.
- `controllers/` - GUI-to-service coordination.
- `services/` - business workflows and persistence orchestration.
- `providers/` - provider interfaces, local and optional live providers, provider manager, configuration, and cache.
- `database/` - SQLite schema and `DatabaseManager`.
- `market/` - universe loading and market data download helpers.
- `indicators/` - indicator calculation framework and SMA implementation.
- `support/` - swing-low detection, support-zone clustering, and support scoring.
- `bounce/` - historical bounce validation logic.
- `analysis/` - scoring, decision engines, trade planning, portfolio statistics, and strategy analytics.
- `fundamentals/` - CSV importer for fundamental metrics.
- `institutional/` - CSV importer for institutional metrics.
- `earnings/` - earnings import and scoring support.
- `config/` - settings, logging, and scoring weights.
- `data/` - local input and generated local data.
- `tests/` - tests for analytics, persistence, services, controllers, and stable UI widgets.
- `docs/` - architecture, roadmap, decisions, and project governance.

## Major Modules

### UI

`ui/main_window.py` composes the desktop workspace and wires widget signals to controllers and services. Reusable widgets include candidate ranking, KPI summary, operations toolbar, activity panel, chart workspace, research preview, trade card, watchlist panel, trade journal panel, performance dashboard, and header refresh status.

### Controllers

Controllers expose GUI-safe workflows and delegate to services. Implemented controller areas include market, indicators, support, bounce, scoring, chart data, watchlist, and trade journal.

### Services

Services own workflow orchestration for market data, indicators, support detection, bounce validation, institutional intelligence, composite scoring, candidate ranking, chart data, watchlist persistence, trade journal persistence, provider resilience, screening diagnostics, export generation, model calibration, production readiness, and Release Candidate Validation.

### Providers

Providers expose a consistent read-only data access boundary through provider interfaces and result objects. Provider resilience tracks health, failover events, configuration validity, and safe offline behavior. Local and mocked providers remain the default for tests. Polygon.io, Financial Modeling Prep, Alpaca, SEC EDGAR, Finnhub, and local CSV integrations are available where implemented and require no secrets in source.

### Database

SQLite is the local source of truth. `DatabaseManager` owns all SQL. Current tables include stocks, price history, technical indicators, support levels, bounce validations, fundamentals, institutional metrics, earnings, watchlist, and paper trades.

### Analysis

The analysis layer includes score providers, composite scoring, composite intelligence, opportunity rating, institutional checklist, trade thesis, trade planning engines, portfolio statistics, and strategy analytics. These engines are pure and must not depend on UI, services, or database access.

## Completed Milestones

- v2.0 Professional Dashboard.
- v2.1 Intelligence Layer.
- v2.2 Chart Workspace.
- v2.3 Decision Engine.
- v2.4 Trade Planning Suite.
- v2.5 Trade Card.
- v2.6 Watchlist.
- v2.7 Portfolio Intelligence.
- v2.8 Stabilization / Performance / Validation.
- v2.9 Data Provider Abstraction.
- v3.0 Beta Infrastructure.

## Current Focus

v2.0 Release-Candidate Finalization:

- Keep architecture boundaries stable.
- Validate provider-backed workflows without changing scoring or persistence schemas.
- Keep configuration, cache, live data, market status, diagnostics, calibration, and export workflows production-ready.
- Maintain release checklist, repository architecture audit, end-to-end validation, known limitations, documentation, and tests.

## Planned

- Post-beta packaging and release validation.
- Additional provider endpoints where explicitly implemented.
- Alerts, richer automation, provider normalization hardening, and packaging remain deferred.

## Dependencies

Runtime dependencies are listed in `requirements.txt` and include PySide6, pandas, and yfinance. The project also uses SQLite through Python's standard `sqlite3` module.

## Test Status

The suite uses `pytest` and covers:

- Pure analysis engines.
- Database persistence methods.
- Services.
- Controllers.
- Stable UI widgets.
- MainWindow integration paths where practical.

For code changes, run:

```powershell
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m compileall app.py main.py controllers services support bounce analysis fundamentals institutional earnings database ui market providers tests
```
