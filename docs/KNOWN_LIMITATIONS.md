# Known Limitations

This document captures beta limitations for Institutional Bounce Screener.

- Paid provider calls require user-supplied API keys through environment variables.
- Provider tests use mocked responses and do not require live subscriptions.
- Live data behavior depends on `config/providers.json`, provider availability, and environment configuration.
- The app is a research workstation only; it does not execute real trades.
- Market holiday handling is intentionally basic and covers only common U.S. market holidays needed for beta refresh behavior.
- Provider data normalization may evolve as provider responses and workflows mature.
- Live watchlist quote updates are runtime UI values and are not persisted to SQLite.
- Provider failover returns the first successful provider result; downstream interpretation may be refined after beta feedback.
- The application is a local-first desktop beta and is not a hosted, multi-user, or production trading platform.
- Packaging and installer workflows remain post-beta work.
