# v2.2 Release Checklist

Use this checklist before tagging the v2.2 Release Candidate.

## Required

- [ ] Run `pytest -q` to completion in CI or with a timeout longer than 5 minutes.
- [ ] Confirm all Technical, Bounce, Fundamental, and Risk analytics tests pass.
- [ ] Open a populated Candidate Detail page and confirm Overview, Technicals, Bounce History, and Risk show real analytics.
- [ ] Open a ticker with missing institutional data and confirm the UI says `Institutional data not configured`, not generic `N/A`.
- [ ] Run the technical indicator pipeline and confirm EMA20, EMA50, EMA200, RSI, MACD, ATR, VWAP, relative volume, and EMA distance fields persist.
- [ ] Confirm worker-owned repository tests still pass for indicator workers.
- [ ] Validate an existing pre-v2.2 database upgrades `technical_indicators` columns successfully.
- [ ] Confirm no UI freeze is visible when opening Candidate Detail for a full-history ticker.

## Recommended

- [ ] Replace remaining Candidate Detail `N/A` fallback text with clearer labels.
- [ ] Add logging around Candidate Detail load exceptions.
- [ ] Profile full-universe indicator calculation runtime.
- [ ] Document `calculate_sma()` as legacy/backward-compatible only.
- [ ] Run a real-data smoke test using at least one known populated ticker.
- [ ] Track synchronous Candidate Detail loading as deferred v2.3 performance work.

## Defer Past v2.2 Unless Blocking

- [ ] Move Candidate Detail chart widget into a dedicated widget module.
- [ ] Add a direct database query for latest ranked candidate by ticker.
- [ ] Optimize technical indicator persistence to batch commits.
- [ ] Clean up placeholder wording in non-detail preview/settings panels.
- [ ] Split long-running tests into explicit fast, integration, UI, and slow jobs.
