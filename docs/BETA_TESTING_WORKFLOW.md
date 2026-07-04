# Beta Testing Workflow

The beta testing workflow exercises the application like a production trading research workstation while staying local-first and testable. It uses configured provider diagnostics, cached market data, universe readiness checks, full-market scan results, candidate review packs, and optional backtest summaries.

## Run A Beta Test

Open the Results panel and use the Beta Testing section.

1. Choose the number of top candidates to review.
2. Optionally enable Backtest.
3. Click `Run Beta Workflow`.
4. Watch the status label for progress and warnings.
5. Export the beta report after completion.

Tests and offline runs should use mocked providers or local cached data. The workflow must not require API keys during automated testing.

## Manual Candidate Review

The review pack highlights the top candidates with:

- ticker
- grade
- final score
- setup label
- support zone summary
- bounce history summary
- institutional summary
- chart data availability
- warnings

The manual checklist CSV includes blank fields for:

- chart confirms support
- volume confirms accumulation
- no earnings risk
- sector/market trend acceptable
- risk/reward acceptable
- reject/approve/watchlist decision
- notes

## Warning Meanings

- Provider warnings mean credentials or selected provider settings should be checked.
- Universe warnings mean few or no eligible symbols are available.
- OHLCV warnings mean cached historical prices are missing or stale.
- Fundamentals warnings mean candidate quality context may be incomplete.
- Institutional warnings mean ownership/accumulation context may be incomplete.
- Export warnings mean reports may not be writable to the configured export directory.

The beta workflow does not modify scoring weights, rejection thresholds, or production defaults.
