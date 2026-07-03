# Release Checklist

Use this checklist before tagging or distributing a build.

## Required Checks

- Confirm `python -m pytest -q` passes.
- Confirm `python -m compileall app.py main.py app_entry.py controllers services database ui backtesting market_data` passes.
- Run `scripts/run_release_checks.ps1`.
- Run beta validation from `About & Diagnostics`.
- Confirm beta validation JSON and CSV reports are exported.
- Review warnings for the validation basket: AAPL, MSFT, NVDA, AMZN, META, GOOGL, JPM, XOM, UNH, COST.
- Confirm app launches in dev mode with `python main.py`.
- Create a database backup from the About & Diagnostics dialog.
- Confirm export directory is writable.
- Confirm provider configuration is present for the selected provider.
- Confirm local/offline mode still works without API keys.

## Build Checks

- Run `scripts/build_release.ps1 -Clean`.
- Confirm output appears in `dist/`.
- Confirm bundled config/data/docs/resources are present.
- Launch packaged executable on a clean workstation profile if possible.

## Common Release Risks

- Missing API keys should show safe messages, not crashes.
- Empty databases should show empty states, not sample data.
- Backups must pass SQLite `PRAGMA integrity_check`.
- Large universe scans should respect configured guardrails.
