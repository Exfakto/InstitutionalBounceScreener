# Institutional Bounce Platform v2.2 Architecture

This document captures the completed v2.2 architecture as the stable base for v3 development.

## Release Scope

v2.2 is the analytics-completion release for Candidate Detail. It enriches the existing screening result with cached market data, technical indicators, support and bounce analytics, fundamentals, risk analytics, and provider-neutral institutional status. The release does not change the screening pipeline orchestration, incremental market-data synchronization, thread-owned repository model, or candidate ranking architecture.

## Core Data Flow

1. Market data and reference data are persisted through the existing repository/database layer.
2. The screening pipeline produces candidates and score/category output.
3. `CandidateDetailDataService` assembles the detail view model from existing database records and analytics services.
4. The Candidate Detail UI renders the view model and displays clear missing-data labels instead of raw placeholders.

## Candidate Detail Data Service

`services/candidate_detail_data_service.py` is the aggregation boundary for the Candidate Detail window. It reads:

- `universe_symbols` for company identity, exchange, sector, and industry.
- `historical_ohlcv_cache` through `services/ohlcv_cache_access.py` for latest close, latest volume, and 52-week range.
- `technical_indicators` for EMA/SMA/RSI/MACD/ATR/VWAP and related distance metrics.
- `support_levels` and `bounce_validations` through `BounceAnalyticsService`.
- stored fundamentals through `FundamentalAnalyticsService`.
- combined metrics through `RiskAnalyticsService`.
- provider-neutral institutional data through `InstitutionalAnalyticsService`.

The service should remain provider-independent and should not perform network calls. Missing values are rendered as user-friendly text such as `Data not available`, `Pending refresh`, or `Provider not configured`.

## Technical Indicators

`services/indicator_service.py` is the production batch entry point for technical indicator calculation. `calculate_indicators()` delegates to the v2.2 `TechnicalIndicatorEngine` path and persists rows through `db.save_technical_indicators(...)`. `calculate_sma()` and `save_sma()` remain for backward compatibility and direct legacy tests only.

Indicator batch work should let `IndicatorService` control the final commit. Repository implementations can preserve backward compatibility by allowing direct saves while avoiding per-ticker commits during batch execution.

## Bounce Analytics

`services/bounce_analytics_service.py` converts stored `support_levels`, `bounce_validations`, and cached OHLCV into historical bounce statistics:

- primary support and support zone boundaries
- support width and distance from support
- historical tests, successful bounces, and failed breakdowns
- bounce success, average/median/largest bounce, and days to peak
- most recent bounce date
- bounce quality score and label
- per-bounce history rows

The service is deterministic and uses existing local data only.

## Fundamental Analytics

`services/fundamental_analytics_service.py` converts stored fundamentals into derived company-quality analytics. It calculates growth, margin, balance-sheet, cash-flow, and valuation metrics, then produces component scores, a Fundamental Intelligence Score, quality flags, commentary, and a research summary.

This service does not fetch fundamentals. Synchronization and provider behavior remain outside the analytics layer.

## Risk Analytics

`services/risk_analytics_service.py` aggregates technical, bounce, and fundamental metrics into a composite Risk Intelligence Score. Lower scores are safer. The service also produces risk class, recommendation, flags, and deterministic commentary.

Risk scoring is a read-only transformation of already assembled metrics and must not mutate candidate ranking state.

## Institutional Analytics

`providers/institutional_provider.py` defines the provider-neutral institutional interface and normalized dataclasses. `services/institutional_analytics_service.py` consumes those normalized models and returns institutional score, ownership trend, accumulation/distribution/conviction/smart-money scores, confidence, and warnings.

The default state is no configured provider. In that mode the application returns `Provider not configured` without exceptions or fabricated data. Future providers should be implemented as adapters under `providers/` and should not require service or UI rewrites.

## UI Boundary

`ui/candidate_detail_window.py` renders the research view from the already assembled view model. It should not duplicate analytics rules or fetch external data. Charting and detail rendering must use cached OHLCV and existing service output.

Synchronous Candidate Detail loading is a known performance item deferred to v2.3/v3. It should be addressed without changing the screening pipeline or repository ownership rules.

## Threading And Repositories

Worker flows must use thread-owned repositories from the existing repository factory pattern. Services running inside workers should operate on the repository passed to them and should not leak repository instances across threads. Test doubles in `tests/test_main_window.py` intentionally assert thread ownership and should remain strict.

Services that create their own `DatabaseManager` for direct use are compatible with the current architecture, but new V3 work should prefer dependency injection when a worker or UI owner already provides a repository.

## Database And Migration Notes

The v2.2 analytics layer relies on existing tables and additive technical indicator columns. Migrations should remain backward compatible and idempotent. Avoid destructive schema changes before V3. Repository methods should tolerate older rows with missing analytics fields and return clear missing-data labels rather than raw placeholders.

## Stabilization Notes

Do not remove these compatibility surfaces before V3 planning:

- `calculate_sma()` and `save_sma()`
- legacy composite score fallback fields
- older institutional screening services used by the screening engine
- repository methods that preserve historical table APIs

Potential V3 cleanup candidates:

- consolidate repeated `row_dict`, numeric coercion, and score clamp helpers
- introduce optional shared analytics typing protocols
- move remaining direct `DatabaseManager` construction toward repository injection where practical
- make Candidate Detail data loading asynchronous or cached at the UI boundary
