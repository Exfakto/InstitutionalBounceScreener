# Institutional Bounce Screener

A local-first PySide6 desktop workstation for identifying, reviewing, planning, and tracking institutional bounce opportunities in U.S. stocks.

## Overview

Institutional Bounce Screener combines market data, technical indicators, support-zone analysis, bounce validation, fundamentals, institutional metrics, candidate scoring, decision support, trade planning, watchlists, paper trade journaling, and portfolio analytics.

The project is designed as a professional research tool, not an execution platform. It uses SQLite as the local persistent store and keeps analytics engines testable outside the GUI.

## Current Platform

Completed platform areas include:

- Professional dashboard shell with dark institutional styling.
- Candidate ranking using Gen 2 Institutional Bounce Intelligence with legacy score fallback.
- Price chart workspace with support and bounce context.
- Research Preview decision dashboard.
- Opportunity rating, institutional checklist, and trade thesis engines.
- Trade planning engines for entry zone, stop loss, targets, risk/reward, and position size.
- Read-only Trade Card widget and dashboard integration.
- Local watchlist persistence, service, controller, and UI panel.
- Paper trade journal persistence, service, controller, and UI panel.
- Portfolio statistics and strategy analytics engines.
- Read-only performance dashboard widget for precomputed analytics.

## Architecture

The application follows a layered local architecture:

```text
UI widgets
Controllers
Services
DatabaseManager
SQLite
```

Pure calculation modules live in `analysis/`, `support/`, `bounce/`, and `indicators/`. Widgets display supplied data and emit user actions; they do not perform database reads, service calls, or analytics calculations.

## Technology

- Python 3.13
- PySide6
- pandas
- yfinance
- SQLite
- pytest

## Milestone Status

Completed:

- v2.0 Professional Dashboard
- v2.1 Intelligence Layer
- v2.2 Chart Workspace
- v2.3 Decision Engine
- v2.4 Trade Planning Suite
- v2.5 Trade Card
- v2.6 Watchlist
- v2.7 Portfolio Intelligence

Current focus:

- v2.8 Stabilization / Performance / Validation

Planned:

- v2.9 Data Provider Abstraction
- v3.0 Beta

Future premium data integrations are planned only; they are not currently implemented.

## Testing

The test suite uses `pytest` and covers pure analytics, persistence, service workflows, controller coordination, and stable UI widgets. Before completing code changes, run the full test suite and compile check.
