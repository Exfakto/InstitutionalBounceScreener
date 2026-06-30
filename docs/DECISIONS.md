# Architecture Decisions

## 2026-06-29 - SQLite Is the Local Source of Truth

The application uses SQLite for local persistence of stocks, price history, indicators, support levels, bounce validations, fundamentals, and institutional metrics.

Reason:

- The project is a local desktop application.
- SQLite keeps setup simple.
- Tests can exercise persistence without external infrastructure.

## 2026-06-29 - Preserve Layered GUI to Database Architecture

The application follows:

```text
GUI -> Controllers -> Services -> DatabaseManager -> SQLite
```

Reason:

- Keeps PySide6 UI code thin.
- Makes analytics workflows testable.
- Prevents SQL and business logic from leaking into widgets.

## 2026-06-29 - Use Pure Analytics Calculators

Indicator, support, bounce, and score provider classes should calculate from supplied data only.

Reason:

- Pure calculators are easier to test.
- Services can orchestrate reads, writes, and summaries.
- Future engines can reuse the same calculators.

## 2026-06-29 - Use Plugin-Style Indicator and Scoring Foundations

The project introduced base classes and engine-style discovery/registration patterns for extensible indicators and score providers.

Reason:

- New analytics can be added without rewriting orchestration.
- Provider failures can be isolated.
- Future custom providers remain possible.

## 2026-06-30 - AnalysisPipeline Owns Candidate Ranking Orchestration

`AnalysisPipeline` runs candidate scoring across active tickers and returns ranked `CandidateScore` objects.

Reason:

- The GUI can run the screener through `ScoringController`.
- Candidate ranking is reusable outside the dashboard.
- Scoring formulas remain inside analysis providers.

## 2026-06-30 - CandidateTable Is a Reusable Widget

The ranked candidate table was extracted from `MainWindow` into `ui/widgets/candidate_table.py`.

Reason:

- Keeps `MainWindow` thinner.
- Centralizes table columns, formatting, sorting, selection, and double-click behavior.
- Supports the v2.0 professional dashboard refactor.

## 2026-06-30 - KpiStrip Owns Dashboard KPI Cards

The dashboard KPI/statistics cards were extracted into `ui/widgets/kpi_strip.py`.

Reason:

- Keeps KPI layout and formatting out of `MainWindow`.
- Supports a compact professional dashboard layout.
- Preserves existing statistic refresh behavior.
