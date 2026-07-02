# Project Manifest

## Purpose

Institutional Bounce Screener is a local desktop research workstation for identifying, evaluating, planning, and tracking institutional bounce opportunities in U.S. stocks.

The app combines market data, technical indicators, support-zone detection, bounce validation, fundamentals, institutional metrics, candidate scoring, decision support, trade planning, watchlists, paper trade journaling, and analytics into a PySide6 application backed by SQLite.

## Current Status

- Current active track: v3.0.0-beta release readiness.
- Completed through: v3.0 Beta infrastructure and dashboard refresh integration.
- Current architecture: local-first SQLite, layered GUI/controller/service/provider/database workflow, and pure analysis engines.
- Optional premium provider foundations exist behind provider configuration and environment variables. Additional provider endpoint expansion remains deferred unless implemented in source.

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

Services own workflow orchestration for market data, indicators, support detection, bounce validation, scoring context, composite intelligence, chart data, watchlist persistence, trade journal persistence, live provider data access, market status, and scheduled refresh.

### Providers

Providers expose a consistent read-only data access boundary through `ProviderResult`. `ProviderManager` selects and fails over between providers, `ProviderConfig` loads safe configuration defaults, and `CacheManager` stores successful responses in memory. `LocalProvider` remains the default. Polygon.io, Financial Modeling Prep, SEC EDGAR, and Finnhub integrations are available where implemented and require no secrets in source.

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

v3.0.0-beta Finalization:

- Keep architecture boundaries stable.
- Validate provider-backed workflows without changing scoring or persistence schemas.
- Keep configuration, cache, live data, market status, and refresh scheduling production-ready for beta.
- Maintain release checklist, known limitations, documentation, and tests.

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
