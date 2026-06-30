# Roadmap

## Completed Milestones

### v0.9 Indicator Foundation

Completed:

- Base indicator structure.
- SMA indicator source implementation.
- Indicator service workflow.
- Indicator persistence in SQLite.
- Dashboard action for calculating indicators.
- Indicator tests.

### v1.0 Core Analytics Platform

Completed:

- Support Detection Engine.
- Swing-low detection.
- Support-zone clustering.
- Support strength scoring.
- Support-level persistence.
- Bounce Validation Engine.
- Historical bounce validation metrics.
- Bounce validation persistence.
- Dashboard actions and KPI counts for support and bounce workflows.

### v1.1 Candidate Scoring / Institutional Analysis

Completed:

- Fundamentals table and CSV importer foundation.
- Institutional metrics table and CSV importer foundation.
- Score result model and base score class.
- Score providers for quality, institutional, technical, support, and bounce.
- Composite score using `config/scoring.json`.
- Candidate score value object.
- Analysis pipeline for ranked candidates.
- Scoring service and controller.
- Run Screener dashboard workflow.
- Read-only stock detail data and detail window.

### v2.0 Professional Dashboard

In progress:

- Candidate table extraction.
- Compact KPI strip extraction.

Planned:

- Operations toolbar.
- Professional dark theme.
- Secondary activity/progress panel.
- Main window layout recomposition.
- Stock detail access polish.
- README and changelog update.

## Next Planned Work

### v2.0 Professional Dashboard

Goal: transform the engineering dashboard into a professional institutional research workstation.

Planned issues:

1. Candidate table extraction and polish.
2. Compact KPI strip.
3. Operations toolbar.
4. Professional dark theme.
5. Activity/progress secondary panel.
6. MainWindow layout recomposition.
7. Stock detail access polish.
8. README and CHANGELOG update.

### v2.1 Charts and Research Workspace

Planned:

- Ticker-focused chart area.
- Price and volume visualization.
- Support zone overlays.
- Bounce validation annotations.
- Read-only research workspace layout.
- No trading execution.

### v2.2 Institutional Intelligence

Planned:

- Richer institutional metrics.
- Better source attribution for imported data.
- Improved institutional score explanations.
- Optional additional CSV import formats.
- No paid API integration unless explicitly approved.

### v3.0 Strategy Lab / Backtesting

Planned:

- Backtesting engine.
- Strategy definitions.
- Historical candidate simulation.
- Performance summaries.
- Risk metrics.
- Exportable reports, if approved.

## Ongoing Principles

- Preserve layered architecture.
- Keep GUI free of analytics logic.
- Keep SQL inside `DatabaseManager`.
- Keep calculators pure.
- Prefer small, testable issues.
- Mark planned modules as planned until implemented in source.
