# Roadmap

## Completed Milestones

### v2.0 Professional Dashboard

Completed:

- Main dashboard recomposition.
- Candidate table and KPI strip extraction.
- Operations toolbar, header bar, activity panel, and dark theme improvements.
- Stable selected-candidate workflows.

### v2.1 Intelligence Layer

Completed:

- Gen 2 Institutional Bounce Intelligence Score.
- Composite intelligence orchestration.
- Candidate ranking preference for Gen 2 score with legacy composite fallback.
- Expanded score display compatibility.

### v2.2 Chart Workspace

Completed:

- Price chart widget.
- Chart data service and controller.
- Selected-candidate chart updates.
- Support and bounce context display support.

### v2.3 Decision Engine

Completed:

- Research Preview 2.0 decision dashboard.
- Opportunity rating engine and integration.
- Institutional checklist engine and integration.
- Trade thesis engine and dashboard display.

### v2.4 Trade Planning Suite

Completed:

- Entry zone engine.
- Stop loss engine.
- Target projection engine.
- Risk/reward engine.
- Position size calculator.

### v2.5 Trade Card

Completed:

- Read-only Trade Card widget.
- Trade Card integration into the decision workspace.
- Missing trade-plan placeholder behavior.

### v2.6 Watchlist

Completed:

- SQLite watchlist table.
- DatabaseManager watchlist methods.
- Watchlist service and controller.
- Watchlist panel integration.

### v2.7 Portfolio Intelligence

Completed:

- SQLite paper trade journal table.
- Trade journal service and controller.
- Trade journal panel integration.
- Portfolio statistics engine.
- Strategy analytics engine.
- Read-only performance dashboard widget.

### v2.8 Stabilization / Performance / Validation

Completed:

- Stabilize the expanded workstation experience.
- Validate key workflows across dashboard, chart, watchlist, journal, and analytics areas.
- Keep documentation, tests, and architecture boundaries current.

### v2.9 Data Provider Abstraction

Completed:

- Provider interfaces and `ProviderResult`.
- Local provider.
- Provider manager.
- Provider configuration.
- Optional Polygon.io price-history provider.

## Current Track

### v3.0 Beta

Goals:

- Stabilize provider-backed infrastructure.
- Keep live data service and refresh scheduling independent from UI code.
- Preserve local-first SQLite workflows.
- Validate release readiness through full tests and compile checks.

Completed:

- Provider cache manager.
- Live data service.
- Automatic refresh scheduler.
- Release stabilization documentation pass.

## Next Planned Work

### Post-Beta Release Readiness

Planned:

- Packaging and installer review.
- Broader workflow validation.
- Operational setup documentation.
- Known limitations and operational documentation.

Additional premium data integrations are planned only when explicitly implemented in source.

## Ongoing Principles

- Preserve layered architecture.
- Keep UI free of analytics and persistence logic.
- Keep SQL inside `DatabaseManager`.
- Keep calculators pure.
- Prefer small, testable issues.
- Mark planned modules as planned until implemented in source.
