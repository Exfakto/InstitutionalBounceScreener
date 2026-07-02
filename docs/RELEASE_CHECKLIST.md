# Release Checklist

Use this checklist before tagging a beta release.

## Environment

- Activate the virtual environment:
  ```powershell
  .venv\Scripts\Activate.ps1
  ```
- Confirm dependencies are installed:
  ```powershell
  python -m pip install -r requirements.txt
  ```

## Verification

- Run the full test suite:
  ```powershell
  python -m pytest
  ```
- Run the compile check:
  ```powershell
  python -m compileall app.py main.py controllers services support bounce analysis fundamentals institutional earnings database ui market providers tests
  ```
- Run the app:
  ```powershell
  python app.py
  ```

## Manual Smoke Tests

- Dashboard smoke test: launch the app, verify header, KPI strip, candidate table, operations toolbar, and activity panel render.
- Chart smoke test: select a candidate and verify the price chart area handles available or missing chart data safely.
- Watchlist smoke test: add a selected candidate, refresh the watchlist panel, remove an item, and verify live quote cells do not clear existing rows on failure.
- Trade journal smoke test: create, close, delete, and refresh paper trade records.
- Decision dashboard smoke test: select a candidate and verify Research Preview and Trade Card show clean available or unavailable states.
- Refresh smoke test: verify market status and auto-refresh indicators display in the header.

## Provider And Secrets

- Verify `config/providers.json` contains no API keys or secrets.
- Verify paid provider keys are supplied only through environment variables when needed.
- Verify tests do not require live provider subscriptions.

## Git And Release

- Verify working tree is clean:
  ```powershell
  git status
  ```
- Review release notes and known limitations.
- Tag the release:
  ```powershell
  git tag v3.0.0-beta
  ```
- Push the tag when ready:
  ```powershell
  git push origin v3.0.0-beta
  ```
