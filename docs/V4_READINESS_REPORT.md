# v4.0 Readiness Report

Date: 2026-07-03

## Executive Summary

InstitutionalBounceScreener is substantially beyond its older v3.0 beta documentation. The codebase now includes a mature local-first research workstation, provider abstraction, decision-support workflow, paper trade tracking, portfolio analytics, and a broad deterministic backtesting foundation. The current project is not yet a polished v4.0 release, but it is close enough that v4.0 should be treated as a stabilization, documentation, packaging, and workflow-validation milestone rather than a major feature-build milestone.

Overall readiness estimate: **82% toward v4.0**.

Primary recommendation: **Proceed toward v4.0 after a focused hardening sprint**, with emphasis on documentation alignment, runtime artifact hygiene, full manual workflow validation, packaging, provider configuration validation, and refactoring of the largest UI/database modules.

## Readiness Snapshot

| Area | Status | Readiness |
| --- | --- | --- |
| Architecture | Strong layered foundation; some large-file pressure | 85% |
| Data Platform | Local-first workflow is solid; premium-provider breadth needs validation | 78% |
| Research Engine | Broad and well-tested; calibration still needs real-world review | 86% |
| Backtesting Engine | Strong deterministic foundation; not yet integrated into UI/workflows | 80% |
| UI / UX | Professional workstation experience; large MainWindow remains risk | 82% |
| Test Coverage | Excellent breadth; limited pixel/manual/provider-live coverage | 90% |
| Documentation | Older docs lag current capability | 65% |
| Release / Packaging | Not yet release-ready | 62% |

## 1. Architecture Review

### analysis/

The analysis layer is a major strength. It contains pure scoring and research engines for quality, technicals, institutional score, support, bounce, composite intelligence, opportunity rating, checklist, trade thesis, entry/stop/target/risk/reward/position sizing, portfolio statistics, strategy analytics, and watchlist intelligence.

Strengths:
- Broad separation from UI, providers, and persistence.
- Strong test coverage across individual calculators and orchestration.
- Decision-support modules map well to the daily research workflow.

Risks:
- Some modules are large, especially `analysis/research_report.py`.
- Score calibration appears structurally complete, but real-world calibration should be treated as ongoing, not finished.
- Naming has evolved across versions; some legacy/composite/Gen 2 names still coexist.

### backtesting/

The backtesting package has grown into a coherent deterministic framework:
- trade simulation
- result/statistics models
- equity curve
- performance analysis
- trade replay
- strategy comparison
- parameter optimization
- walk-forward validation

Strengths:
- Pure deterministic calculations.
- No provider/database/UI dependency.
- Good unit coverage.
- Architecture is composable: optimizer and walk-forward reuse the engine.

Risks:
- Backtesting remains a foundation, not a full production backtesting product.
- No slippage, commissions, position sizing portfolio allocation, overlapping trade controls, liquidity modeling, survivorship-bias controls, or realistic order fill modeling yet.
- Not integrated into UI or persisted workflows, which is appropriate for current scope but important for v4.0 expectations.

### services/

Services are the main workflow layer and cover historical sync, fundamentals sync, diagnostics, scoring context, chart data, live data, refresh scheduling, watchlist, trade journal, and analysis support services.

Strengths:
- Service boundaries are mostly clear.
- Sync and diagnostics services are tested.
- Local-first flow is preserved.

Risks:
- Service count and responsibility breadth are growing.
- Some workflow orchestration may eventually need clearer domain grouping.
- Provider-backed services should be validated with real configured environments before v4.0.

### controllers/

Controllers provide GUI-safe coordination for market, indicator, support, bounce, scoring, chart, watchlist, trade journal, settings, diagnostics, export, and presets.

Strengths:
- Controllers keep most business logic out of widgets.
- Test coverage exists for important coordination paths.

Risks:
- `ui/main_window.py` still performs substantial orchestration and remains the largest architectural pressure point.
- As workflows grow, controller/service responsibilities should be audited to prevent drift.

### providers/

Provider abstraction is solid:
- `ProviderResult`
- base provider contract
- local provider
- Polygon
- FMP
- Finnhub
- SEC EDGAR
- provider manager
- config
- cache

Strengths:
- Provider results are normalized.
- Failover and cache behavior are tested.
- Optional paid providers are isolated behind config/environment.

Risks:
- Live provider behavior is only as reliable as real API response compatibility.
- Several provider endpoints are intentionally foundational rather than exhaustive.
- Provider normalization hardening should remain a v4.0 pre-release task.

### database/

SQLite remains the local source of truth. Current schema areas include stocks, price history, indicators, support, bounce validations, fundamentals, institutional metrics, earnings, watchlist, and paper trades.

Strengths:
- Local-first workflow is appropriate for a personal research workstation.
- Database-related tests exist.

Risks:
- `database/manager.py` is large and should be considered for future decomposition.
- Runtime database files exist under `data/`; verify they are intentionally untracked before release.
- No schema changes are required for v4.0 readiness, but migration/versioning strategy should be documented before broader distribution.

### ui/

The UI is a capable PySide6 workstation with dockable panels, candidate grid, chart, research preview, trade card, watchlist, trade journal, performance dashboard, status bar, and workspace persistence.

Strengths:
- Professional dashboard and dockable workspace are implemented.
- Widget tests cover stable structure and behavior.
- Recent chart and UX polish improved cohesion.

Risks:
- `ui/main_window.py` and `ui/widgets/research_preview.py` are very large.
- Some UI tests are structural rather than interactive/manual.
- Packaging and cross-machine display validation remain open.

### tools/

Tools exist for historical sync, fundamental sync, diagnostics, and provider smoke testing.

Strengths:
- CLI workflows are tested.
- Operational diagnostics are part of the project, not an afterthought.

Risks:
- CLI documentation should be refreshed for v4.0.
- Error-handling behavior should be manually validated against real missing-key and partial-data scenarios.

### tests/

The suite is broad and impressive. The most recent full run observed during this assessment passed **946 tests**.

Strengths:
- Analysis, services, providers, database, UI widgets, CLI tools, and backtesting are covered.
- Deterministic tests dominate, which fits the local-first architecture.

Risks:
- `tests/` contains compiled `.pyc` files in the workspace, suggesting runtime artifacts need cleanup.
- Provider live tests are mocked by design; live smoke testing is still needed outside unit tests.
- UI visual/pixel validation is intentionally limited.

## 2. Data Platform Assessment

### Polygon Integration

Polygon support exists for provider-backed price history where configured. It is properly isolated behind provider abstractions and environment variables.

Readiness: **usable foundation, not fully production-hardened**.

Before v4.0:
- Run provider smoke tests with a real key.
- Validate rate-limit and error messages.
- Confirm price normalization for edge cases such as splits, empty payloads, and partial candles.

### FMP Integration

FMP exists in the provider layer and fundamental sync path. Tests cover expected workflows with controlled responses.

Readiness: **good integration foundation**.

Before v4.0:
- Validate representative real payloads.
- Confirm field mappings for profile, fundamentals, and missing-value behavior.

### Provider Abstraction

The provider abstraction is one of the cleaner pieces of the project. `ProviderResult`, `ProviderManager`, config, cache, and local provider create a good boundary.

Remaining work:
- Document provider priority semantics.
- Document unsupported endpoints clearly.
- Add a release smoke-test checklist for configured and unconfigured environments.

### Historical Sync

Historical sync has CLI and service coverage. It appears ready for continued local-first operation.

Risks:
- Large imports and repeated runs should be validated for performance.
- Error reporting for partial provider failures should be reviewed manually.

### Fundamental Sync

Fundamental sync service and CLI have strong test coverage.

Risks:
- Real-world provider schema drift remains the main uncertainty.
- Field provenance and timestamping should be reviewed before v4.0 if decisions depend heavily on fundamentals.

### Diagnostics

Diagnostics services and CLIs are a strength. They make the app more operable as a personal workstation.

Before v4.0:
- Consolidate a “first run diagnostics” guide.
- Include provider keys, database presence, data freshness, and local config checks.

### Local SQLite Workflow

SQLite is appropriate for the current single-user desktop workflow. Local CSV and DB files under `data/` support the research station model.

Readiness risk:
- Ensure `.gitignore` and repository tracking state exclude runtime DBs, local cache, logs, workspace state, and compiled artifacts.

## 3. Research Engine Assessment

### Opportunity Scoring

Opportunity scoring is implemented and connected to research preview/candidate workflows. It is suitable for ranking and decision support.

Risk:
- Score meaning should be calibrated with historical review and actual trade outcomes before being treated as predictive.

### Composite Intelligence

Composite intelligence exists and is service-integrated. It appears well-covered by tests.

Risk:
- Multiple score families and fallback paths should be documented so users understand which score is primary.

### Research Report Engine

The report engine is feature-rich and tested. It supports export workflows and broader review.

Risk:
- `analysis/research_report.py` is large. Future changes may benefit from splitting formatting, section generation, and data normalization.

### Watchlist Intelligence

Watchlist intelligence exists and is wired into the watchlist panel. It supports monitoring and triage.

Risk:
- Live quote updates are intentionally non-persistent. This is acceptable, but should be documented for users expecting persisted watchlist prices.

### Export Framework

Export services/controllers/dialogs are tested and appear mature.

Risk:
- Real user output review is still needed: file naming, markdown/CSV ergonomics, and failure handling.

## 4. Backtesting Engine Assessment

Backtesting is now a serious foundation:
- `BacktestEngine`
- `BacktestTrade`
- `BacktestResult`
- `BacktestStatistics`
- `EquityCurve`
- `PerformanceAnalysis`
- `TradeReplayEngine`
- `StrategyComparisonEngine`
- `ParameterOptimizer`
- `WalkForwardValidator`

Ready:
- Deterministic trade simulation.
- Core statistics.
- Equity curve and drawdown analysis.
- Monthly/yearly period returns.
- Trade replay.
- Strategy comparison.
- Parameter grid optimization.
- Walk-forward validation.

Not ready as a full trading-grade backtester:
- No slippage.
- No commissions.
- No capital allocation model.
- No trade overlap constraints.
- No realistic intraday sequencing beyond deterministic OHLC assumptions.
- No survivorship-bias prevention.
- No benchmark comparison.
- No persisted backtest run history.
- No UI for inspection.

Recommendation:
- Treat v4.0 as “backtesting foundation included,” not “full institutional backtesting platform.”

## 5. UI / UX Assessment

### Dockable Workspace

The dockable workspace and layout presets are good enough for daily use. Workspace state persistence exists.

Risk:
- Manual testing is needed across window sizes and monitor configurations.

### Professional Status Bar

The status bar tracks market/provider/database/refresh/selection/preset/workspace state. This is useful and release-worthy.

### Candidate Grid

The grid is mature: ranked rows, stable formatting, score roles, and no-edit behavior.

Potential improvement:
- Add explicit empty-state messaging near the table if no candidates are present.

### Trade Card

Trade Card is feature-complete for read-only planning review. Copy/compact behavior exists.

Potential improvement:
- Clarify whether generated trade plans are advisory only and not executable orders.

### Research Preview

Research Preview 2.0 is one of the core strengths. It is also one of the largest UI files.

Risk:
- Continued additions should be split into smaller presenter/section helpers.

### Chart Presentation

The chart panel is significantly improved: professional header, empty state, support bands, SMA legend, axis styling, and chart modes.

Risk:
- QtCharts availability remains an environment dependency.

### Workspace Persistence

Workspace state service persists layout metadata, dock visibility/floating state, and active layout. Good readiness.

Risk:
- `config/workspace_state.json` is runtime state and should remain untracked.

## 6. Test Coverage Assessment

Strengths:
- Broad unit coverage across analysis engines.
- Service and controller workflows are tested.
- Provider abstractions and provider manager are tested.
- CLI sync/diagnostic tools are tested.
- UI widgets have stable structure/behavior tests.
- Backtesting has dedicated tests for simulation, equity curve, performance analysis, replay, comparison, optimization, and walk-forward validation.
- Full suite recently observed: **946 passed**.

Likely gaps:
- Manual end-to-end app launch and daily workflow validation.
- Real provider smoke testing with actual API keys.
- Large local dataset performance testing.
- Packaging/installer validation.
- Visual regression or screenshot testing for important UI layouts.
- Database migration/versioning tests for future schema changes.
- Long-running refresh/scheduler behavior under real market sessions.

Recommendation:
- Keep the existing deterministic test philosophy, but add a short manual release validation checklist for UI and provider reality checks.

## 7. Technical Debt

### Large Files

Largest files by current scan include:
- `ui/main_window.py`
- `ui/widgets/research_preview.py`
- `database/manager.py`
- `analysis/research_report.py`
- `ui/widgets/price_chart.py`
- `services/export_service.py`
- `ui/widgets/trade_card.py`
- `ui/theme.py`

These are not urgent blockers, but they are the highest-risk files for future change.

Recommended refactors:
- Split `MainWindow` workflow methods into smaller coordinator classes or mixins.
- Split `ResearchPreview` into section widgets/builders.
- Split `DatabaseManager` by domain or introduce repository-style helpers while keeping SQL ownership clear.
- Split report generation into section builders and formatters.

### Duplicate Code / Similar Helpers

There are recurring helper patterns:
- date parsing
- numeric coercion
- missing-value formatting
- warning collection
- dictionary/object value extraction

This is tolerable now, but v4.x should introduce small shared utility modules in narrowly scoped areas, especially backtesting and UI formatting.

### Naming Inconsistencies

Observed naming drift:
- Gen 2 / composite / institutional bounce / opportunity score naming.
- `entry`, `recommended_entry`, `entry_price` variants.
- `target`, `target_1`, `target_price` variants.
- `risk_reward`, `best_rr`, `rr_1` variants.

Recommendation:
- Document canonical field names and aliases before more integrations are added.

### Runtime Artifacts

Runtime/cache artifacts are present in the workspace:
- `.pytest_cache/`
- `__pycache__/`
- many compiled `.pyc` files under `tests/`
- `config/workspace_state.json`
- local data files and `data/InstitutionalBounce.db`

`.gitignore` already excludes most of these patterns, but release readiness requires verifying they are not tracked and cleaning the working tree before tagging.

### Config / Data Files

Important files:
- `config/providers.json`
- `config/scoring.json`
- `data/*.csv`
- `data/InstitutionalBounce.db`

Before v4.0:
- Confirm which files are sample data versus personal runtime data.
- Ensure secrets are never stored in config.
- Provide `.example` config files if needed.

## 8. Release Readiness

### Ready

- Local-first research workflow.
- Candidate scoring and research preview.
- Trade planning display.
- Watchlist and paper trade journal.
- Provider abstraction.
- Historical/fundamental sync foundations.
- Diagnostic tools.
- Backtesting foundation.
- Broad automated test coverage.
- Professional desktop UI foundation.

### Not Ready

- Packaging/installer.
- Fully updated roadmap/manifest.
- Manual v4.0 workflow signoff.
- Real provider smoke-test signoff.
- Runtime artifact cleanup.
- Canonical data/config setup guide.
- Backtesting UI/persistence if those are considered part of v4.0.

### Should Complete Before v4.0

1. Update docs to reflect v3.8/v3.9 capabilities.
2. Run full manual daily workflow validation.
3. Run provider smoke tests with configured keys.
4. Verify `.gitignore` and tracked-file hygiene.
5. Clean runtime caches/artifacts from the working tree.
6. Add or update first-run setup docs.
7. Validate packaging path or explicitly defer it.
8. Audit large files for any high-risk quick refactors.
9. Document canonical field aliases.
10. Create a v4.0 release checklist tied to actual workflows.

### Can Safely Wait

- Full backtesting UI.
- Persisted backtest run history.
- Slippage/commission modeling.
- Benchmark comparison.
- Hosted/multi-user architecture.
- Alerts and automated trading.
- Broad visual regression infrastructure.

## 9. Personal Trading Workflow Readiness

### Daily Screening

Readiness: **High**.

The app supports universe/data sync, indicator calculation, support detection, bounce validation, scoring, and candidate display. This is the strongest daily workflow.

Remaining work:
- Ensure data freshness indicators are trusted.
- Add a personal daily checklist outside code or in docs.

### Research Review

Readiness: **High**.

Research Preview, opportunity rating, checklist, thesis, warnings, and export/report support are strong.

Remaining work:
- Calibrate scoring against actual review outcomes.
- Clarify score interpretation in documentation.

### Trade Planning

Readiness: **Medium-high**.

Entry, stop, targets, risk/reward, position sizing, and Trade Card exist.

Remaining work:
- Confirm plans are read-only and advisory.
- Consider a user-facing caveat that no order execution exists.

### Watchlist Monitoring

Readiness: **Medium-high**.

Watchlist persistence and live quote refresh exist, but live quotes are non-persistent by design.

Remaining work:
- Validate live update behavior during market sessions.
- Document non-persistence of live quote cells.

### Backtesting

Readiness: **Medium**.

The deterministic engine foundation is strong. It is not yet a full production-grade backtester or UI workflow.

Remaining work:
- Add realistic trading assumptions only when explicitly needed.
- Decide whether v4.0 includes CLI or UI access to backtesting.

### Strategy Validation

Readiness: **Medium**.

Parameter optimization and walk-forward validation exist as pure engines.

Remaining work:
- Validate with real historical candidate datasets.
- Avoid over-trusting early results before survivorship and data-quality risks are addressed.

## 10. Final Recommendation

Recommendation: **Advance toward v4.0 after a short hardening and documentation sprint.**

This project has crossed from prototype/beta into a capable personal research workstation. The core architectural boundaries are mostly intact, the test suite is unusually broad, and the backtesting foundation is now meaningful. The main blockers are not missing core engines; they are release hygiene, documentation drift, manual validation, packaging, and reducing risk around large orchestration files.

### Strengths

1. Strong local-first architecture.
2. Clear UI/controller/service/provider/database layering.
3. Broad pure analysis engine coverage.
4. Mature decision-support workflow.
5. Provider abstraction with safe optional premium integrations.
6. Practical diagnostics and sync tools.
7. Robust deterministic backtesting foundation.
8. Professional PySide6 workstation UI.
9. Excellent automated test breadth.
10. Conservative handling of no-provider/no-database/no-randomness boundaries in new engines.

### Top Risks

1. Documentation is behind the actual codebase.
2. Large files increase regression risk.
3. Runtime artifacts and local data need release hygiene review.
4. Provider integrations need real smoke testing.
5. Backtesting can be misinterpreted as production-grade if limitations are not documented.
6. Score calibration needs real-world feedback.
7. Packaging/installer path is unresolved.
8. UI manual validation across screen sizes is incomplete.
9. Canonical data field names are not fully standardized.
10. Local SQLite workflow needs setup/migration documentation before broader distribution.

### Top 10 Recommended Next Tasks

1. Update `docs/ROADMAP.md` and `docs/PROJECT_MANIFEST.md` for v3.8/v3.9/v4.0 reality.
2. Create a v4.0 release checklist based on daily screening, research, trade planning, watchlist, journal, and backtesting workflows.
3. Verify tracked/untracked status for `data/`, `config/workspace_state.json`, `.pytest_cache/`, `__pycache__/`, and `.pyc` files.
4. Run provider smoke tests with real Polygon/FMP configuration.
5. Run a full manual app workflow from fresh start through screening, research review, chart inspection, watchlist, trade card, and journal.
6. Document backtesting assumptions and limitations.
7. Document canonical field aliases for entry/stop/target/risk/opportunity fields.
8. Add first-run setup documentation for local database, config, provider keys, and diagnostics.
9. Identify a low-risk split plan for `ui/main_window.py`, `ui/widgets/research_preview.py`, and `database/manager.py`.
10. Decide whether v4.0 includes backtesting as engine-only or requires a user-facing CLI/UI workflow.

### Recommended v4.0 Roadmap

#### v4.0.0 Release Hardening

- Documentation refresh.
- Release checklist.
- Runtime artifact cleanup.
- Provider smoke-test signoff.
- Manual workflow validation.
- Packaging decision.

#### v4.0.1 Workflow Stabilization

- Daily workflow refinements.
- Data freshness/status improvements.
- Better setup and diagnostics documentation.
- Minor UI polish based on real usage.

#### v4.1 Backtesting Access

- CLI or UI access to backtesting engines.
- Backtest assumptions documentation.
- Optional persisted run summaries if schema changes are approved later.

#### v4.2 Data Reliability

- Provider normalization hardening.
- More robust data freshness checks.
- Expanded diagnostics.

#### v4.3 Maintainability

- Refactor largest UI and database modules.
- Consolidate repeated date/numeric/value helper patterns.
- Improve canonical naming across trade-planning fields.

## Bottom Line

InstitutionalBounceScreener is **functionally strong and test-rich**, with a credible path to v4.0. The app should not be called v4.0 until documentation, release hygiene, provider smoke testing, and manual workflow validation catch up to the implementation. Once those are done, v4.0 is a reasonable and honest milestone for a local-first institutional bounce research workstation with a deterministic backtesting foundation.
