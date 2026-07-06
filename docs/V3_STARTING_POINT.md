# Version 3 Starting Point

Version 3 begins from the v2.2.0 RC baseline. The core screening engine, analytics services, database persistence, threading model, and Candidate Detail data aggregation are considered stable unless a Version 3 task explicitly changes them.

## Current Architecture

The application is a local-first PySide6 desktop research workstation backed by SQLite.

Primary layers:

- `database/`: schema and `DatabaseManager`.
- `services/`: workflow orchestration, analytics, persistence coordination, diagnostics, validation, and release utilities.
- `providers/`: provider abstractions and local/provider-specific adapters.
- `controllers/`: GUI-safe coordination between widgets and services.
- `ui/`: desktop widgets, Candidate Detail, screening panels, diagnostics, beta tools, and research views.
- `analysis/`: pure scoring, research, trade, and strategy logic.

The stable dependency direction remains repository/data access into services, services into controllers, and controllers into UI.

## Completed Modules

- Full-market universe workflow.
- Incremental OHLCV cache workflow.
- Technical Indicator Engine.
- Support detection.
- Bounce validation.
- Bounce Analytics Service.
- Fundamental Analytics Service.
- Risk Analytics Service.
- Institutional provider interface and analytics service.
- Candidate Detail Data Service.
- Candidate Detail research workstation.
- Screening Orchestrator.
- Candidate Ranking Engine.
- Screening run persistence.
- Screening signal history persistence.
- Beta Phase 1 documentation and feedback templates.
- Release and architecture documentation.

## Deferred Work

- Non-blocking Candidate Detail data loading for very large histories.
- Real institutional provider adapters.
- Outcome evaluator for stored screening signals.
- Evidence-based score recalibration.
- Shared helper consolidation across analytics services.
- Formal migration versioning beyond additive table/column creation.
- Legacy SMA-only path retirement after compatibility review.
- Broader provider smoke testing with real credentials.

## Recommended Version 3 Priorities

1. Stabilize signal validation history collection during live beta usage.
2. Build the v3.1 outcome evaluator using cached OHLCV.
3. Add reporting over signal cohorts, score bands, sectors, and risk classes.
4. Use measured outcomes to design v3.2 scoring recalibration.
5. Add provider adapters only after the provider-neutral architecture has remained stable in beta.
6. Move heavy Candidate Detail loading off the UI path if beta usage shows visible blocking.
7. Consolidate low-risk duplicate analytics helpers after behavior-sensitive work is complete.

## Development Guardrails

- Do not change screening logic without a scoring-change task.
- Do not change thread ownership rules.
- Do not bypass incremental synchronization.
- Do not add provider-specific code outside the provider layer.
- Do not overwrite historical signal records.
- Do not fabricate missing institutional or fundamental data.
- Keep tests green before and after each milestone.

## Starting Verification Baseline

The current baseline verification is:

```text
1753 passed
```

Use this as the starting quality bar for Version 3 changes.
