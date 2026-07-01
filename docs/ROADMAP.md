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

## Current Track

### v2.8 Stabilization / Performance / Validation

Goals:

- Stabilize the expanded workstation experience.
- Validate key workflows across dashboard, chart, watchlist, journal, and analytics areas.
- Review performance of data-heavy workflows.
- Keep documentation, tests, and architecture boundaries current.
- Avoid feature expansion that belongs in later milestones.

Planned work:

- Workflow validation.
- Performance profiling where needed.
- Error-state and empty-state review.
- Documentation polish.
- Release readiness checklist.

## Next Planned Work

### v2.9 Data Provider Abstraction

Planned:

- Abstract market and reference data provider boundaries.
- Keep yfinance/local CSV behavior working.
- Prepare optional provider adapters.
- Clearly separate free/local data paths from future premium integrations.

Premium data integrations are planned only and are not implemented.

### v3.0 Beta

Planned:

- Beta packaging and release readiness.
- Broader workflow validation.
- Usability polish.
- Configuration and setup review.
- Known limitations and operational documentation.

## Ongoing Principles

- Preserve layered architecture.
- Keep UI free of analytics and persistence logic.
- Keep SQL inside `DatabaseManager`.
- Keep calculators pure.
- Prefer small, testable issues.
- Mark planned modules as planned until implemented in source.
