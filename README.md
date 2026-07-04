# Institutional Bounce Screener

A local-first PySide6 desktop workstation for identifying, reviewing, planning, and tracking institutional bounce opportunities in U.S. stocks.

## Overview

Institutional Bounce Screener combines market data, technical indicators, support-zone analysis, bounce validation, fundamentals, institutional metrics, candidate scoring, decision support, trade planning, watchlists, paper trade journaling, and portfolio analytics.

The project is designed as a professional research tool, not an execution platform. It uses SQLite as the local persistent store and keeps analytics engines testable outside the GUI.

## v2.0 Release-Candidate Platform

Institutional Bounce Screener is in v2.0 release-candidate readiness. Completed platform areas include:

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
- Provider abstraction with local and optional premium-provider foundations.
- Configurable provider resilience, failover event logging, provider health, provider configuration validation, in-memory provider caching, live data service, and refresh scheduler.
- Market-status-aware live refresh infrastructure and watchlist quote updates.
- Full-market screening orchestration, screening diagnostics, ranked results, export workflows, and end-to-end validation.
- Model calibration recommendations, history, trend, comparison, apply, validation, and integration audit tooling.
- Production readiness dashboard and Release Candidate Validation suite.
- Current dashboard widget implementation: `ui/widgets/dashboard.py`.

## Architecture

The application follows a layered local architecture:

```text
Repository -> Services -> Controllers -> UI
```

Pure calculation modules live in `analysis/`, `support/`, `bounce/`, `indicators/`, and deterministic service engines. Provider infrastructure lives in `providers/` and `market_data/` and feeds service workflows without changing analysis engines or UI code. Widgets display supplied data and emit user actions; they do not perform database reads, provider calls, or analytics calculations.

## Technology

- Python 3.13
- PySide6
- pandas
- yfinance
- SQLite
- pytest

## Milestone Status

Release-candidate capabilities:

- Professional dashboard and responsive workstation shell
- Provider abstraction, cache-first data access, provider resilience, provider health, failover logging, and provider configuration validation
- Full-market screening, technical/support/bounce/institutional analysis, composite scoring, ranking, and results workflows
- Export generation for ranked candidates, run packages, reports, validation artifacts, and beta/release workflows
- Model calibration recommendations, history, trend, comparison, apply, validation, and integration audit
- Production readiness dashboard, Release Candidate Validation, repository architecture audit, and end-to-end workflow validation

Current focus:

- v2.0 RC1 Release Freeze, Release Candidate Validation, repository architecture audit, and final release-readiness checks

Planned:

- RC packaging checks, validation, operational hardening, and deferred feature work

Premium provider foundations exist for Polygon.io, Financial Modeling Prep, Alpaca, SEC EDGAR, and Finnhub where implemented in source. Paid provider calls require API keys and tests use mocked responses.

Provider setup, PowerShell environment variables, and safe smoke-test commands are documented in `docs/PROVIDER_SETUP.md`.

Repository architecture readiness is documented in `docs/repository_architecture_audit.md`.
End-to-end workflow validation is documented in `docs/end_to_end_validation.md`.
Release Candidate Validation is documented in `docs/release_candidate_validation.md`.
RC1 release freeze criteria are documented in `docs/rc1_release_freeze_checklist.md`.

## Testing

The test suite uses `pytest` and covers pure analytics, persistence, service workflows, controller coordination, provider behavior, and stable UI widgets. Before completing code changes, run the full test suite and compile check.
