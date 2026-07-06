# V3 Development Guide

This guide defines the guardrails for building on the stable v2.2 architecture.

## Development Principles

- Keep the screening pipeline, candidate ranking flow, incremental synchronization, and thread-owned repository model stable unless a V3 design explicitly replaces them.
- Prefer additive changes and backward-compatible migrations.
- Keep analytics deterministic and local-data driven.
- Keep provider-specific code inside provider adapters.
- Avoid UI work that performs network calls or long database operations on the main thread.
- Preserve clear missing-data labels. Do not reintroduce raw `N/A` placeholders.

## Recommended V3 Extension Points

### Candidate Detail

Use `CandidateDetailDataService` as the single aggregation point for Candidate Detail data. New Candidate Detail sections should consume fields from that service or from services it composes. Avoid duplicating analytics calculations in Qt widgets.

### Technical Analytics

Extend `TechnicalIndicatorEngine` for new technical metrics. Keep `IndicatorService.calculate_indicators()` as the batch entry point and preserve `calculate_sma()` as a compatibility path until the legacy API can be formally retired.

### Bounce Analytics

Extend `BounceAnalyticsService` for additional historical support and bounce statistics. New calculations should be derived from `support_levels`, `bounce_validations`, and cached OHLCV, not from live network calls.

### Fundamental Analytics

Extend `FundamentalAnalyticsService` for new derived metrics, component scores, flags, and research text. The service should continue to read stored fundamentals only.

### Risk Analytics

Extend `RiskAnalyticsService` when new technical, bounce, or fundamental metrics need to affect risk. Risk changes are scoring changes and should include focused regression tests and explicit release notes.

### Institutional Providers

Add future institutional data providers by implementing `providers.institutional_provider.InstitutionalProvider`.

Provider adapters should normalize external data into:

- `InstitutionalOwnership`
- `OwnershipTrend`
- `ThirteenFActivity`
- `InsiderActivity`
- `ShortInterest`
- `InstitutionalSnapshot`

The rest of the application should consume only provider-neutral models or `InstitutionalAnalyticsService` output.

## Repository And Threading Rules

- Worker code must obtain repositories through the existing thread-local factory pattern.
- Services running inside a worker should receive the worker-owned repository.
- Do not share repository instances across worker threads.
- Keep test doubles that assert thread ownership strict.
- Repository close/commit behavior should remain owned by the worker or service boundary that created the repository.

## Database Migration Rules

- Prefer additive columns and idempotent `ensure_*` methods.
- Avoid destructive migrations in minor releases.
- Keep repository methods tolerant of older rows.
- Batch services should control commits at the batch boundary where possible.
- Tests should cover both fully populated data and partial/older data.

## UI Rules

- Keep Candidate Detail tabs and existing workflows intact.
- Use cached OHLCV and already computed analytics.
- Do not block the UI with provider calls, large queries, or indicator calculation.
- Render unavailable metrics as `Data not available`, `Pending refresh`, `Not configured`, or `Provider not configured` depending on context.
- Avoid redesigning shared UI components as part of analytics changes.

## Testing Expectations

For any V3 change, add focused tests for:

- complete data
- missing or partial data
- stale or older database rows
- provider not configured and provider failure cases
- thread-owned repository behavior when workers are involved
- UI rendering without raw placeholders

Before release, run:

```powershell
.venv\Scripts\python.exe -m pytest -q
```

For Candidate Detail changes, also run the Candidate Detail and research tests directly before the full suite.

## Safe Cleanup Candidates

These are appropriate for V3 cleanup planning but should be treated as behavior-sensitive:

- consolidating duplicate analytics helper functions
- extracting common score/normalization utilities
- reducing direct `DatabaseManager` construction in services
- introducing typed protocols for repositories and provider adapters
- moving Candidate Detail loading to a non-blocking data-loading path

## Release Readiness Checklist

- Full test suite is green.
- No raw `N/A` appears in Candidate Detail.
- New provider failures degrade gracefully.
- New database changes are backward compatible.
- Worker tests still prove thread-owned repositories are used and closed.
- Documentation identifies any deferred performance or architecture work.
