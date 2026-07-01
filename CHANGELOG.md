# Changelog

## v3.0 - Beta Infrastructure

### Added

- Provider configuration for selecting active data providers without code changes.
- Optional Polygon.io price-history provider using `POLYGON_API_KEY`.
- In-memory provider cache manager with endpoint-specific TTLs.
- Live data service for routing provider data into service workflows.
- Automatic refresh scheduler for periodic ticker refreshes through `LiveDataService`.

### Stabilized

- Provider failures return structured `ProviderResult` objects.
- Provider tests use mocks and fake services; no paid API calls are required.
- Documentation updated for the v3.0 Beta architecture.

## v2.9 - Data Provider Abstraction

### Added

- Provider interfaces and `ProviderResult`.
- Local provider for database-backed reads.
- Provider manager for registration, provider selection, and request delegation.
- Safe provider config defaults for missing or malformed configuration.

## v2.8 - Stabilization / Performance / Validation

### Status

- Documentation updated to reflect the current v2.7 platform state.
- Next work focuses on stabilization, performance review, validation, and release readiness.

### Current Completed Platform

- v2.0 Professional Dashboard.
- v2.1 Intelligence Layer.
- v2.2 Chart Workspace.
- v2.3 Decision Engine.
- v2.4 Trade Planning Suite.
- v2.5 Trade Card.
- v2.6 Watchlist.
- v2.7 Portfolio Intelligence.

## v2.7 - Portfolio Intelligence

### Added

- Paper trade journal SQLite foundation, service, controller, and desktop panel.
- Portfolio statistics analysis engine.
- Strategy analytics analysis engine.
- Read-only performance dashboard widget for precomputed portfolio and strategy analytics.

## v2.6 - Watchlist

### Added

- Local SQLite watchlist foundation.
- Watchlist service and controller.
- Desktop watchlist panel for viewing and managing saved candidates.

## v2.5 - Trade Card

### Added

- Read-only Trade Card widget.
- MainWindow integration for displaying prepared trade plans when available.

## v2.4 - Trade Planning Suite

### Added

- Entry Zone engine.
- Stop Loss engine.
- Target Projection engine.
- Risk / Reward engine.
- Position Size calculator.

## v2.3 - Decision Engine

### Added

- Research Preview 2.0 decision dashboard.
- Opportunity rating integration.
- Institutional checklist engine and pipeline integration.
- Trade thesis engine and dashboard integration.

## v2.2 - Chart Workspace

### Added

- Price chart workspace.
- Chart data service and controller.
- Support-zone and bounce-validation context for selected candidates.

## v2.1 - Intelligence Layer

### Added

- Gen 2 Institutional Bounce Intelligence Score.
- Composite intelligence service.
- Candidate ranking preference for Gen 2 score with legacy composite fallback.
- Expanded scoring display compatibility.

## v2.0 - Professional Dashboard

### Added

- Professional dashboard layout.
- Reusable candidate table, KPI strip, toolbar, activity panel, header bar, and dark theme improvements.
- Cleaner selected-candidate workflows.

## v1.x - Core Analytics Foundation

### Added

- Market universe import and price history persistence.
- SMA indicator workflow.
- Support Detection Engine.
- Bounce Validation Engine.
- Fundamentals and institutional CSV import foundations.
- Candidate scoring providers, composite score, analysis pipeline, and stock detail view.

### Verification

- The project is maintained with `pytest` coverage across analytics, persistence, services, controllers, and stable UI widgets.
- Application source is expected to pass `compileall` before release-oriented changes are completed.
