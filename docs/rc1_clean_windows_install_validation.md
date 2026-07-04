# RC1 Clean Windows Install Validation

This checklist validates that the v2.0 RC1 package can be installed and launched on a clean Windows machine. It is intended for release-candidate testing after packaging verification passes.

## Scope

Validate:

- packaged application dependencies
- runtime folders
- first-launch behavior
- logs, config, database, data, export, and backup paths
- offline startup behavior
- provider setup expectations

This validation does not require live market data access or API keys.

## Packaged App Dependencies

The packaged app is built with PyInstaller from:

- `InstitutionalBounceScreener.spec`
- `app_entry.py`
- `scripts/build_release.ps1`

The bundle must include:

- Python runtime embedded by PyInstaller
- PySide6/Qt runtime files
- pandas runtime dependencies
- SQLite support from Python standard library
- bundled `config/`
- bundled `data/market_universe_template.csv`
- bundled `data/market_universe_seed.csv`
- bundled `docs/`
- bundled `resources/`

No separate Python installation should be required for the packaged executable.

## Expected Runtime Folders

On first launch, the application may create or use:

- `data/`
- `logs/`
- `exports/results/`
- `data/backups/`
- `config/`

These folders must be writable by the Windows user running the app.

## First-Launch Behavior

Expected first launch behavior:

1. Application window opens without unhandled exceptions.
2. SQLite database directory is prepared if missing.
3. Export and log directories are prepared if missing.
4. Missing database file is reported as a warning, not a crash.
5. Provider configuration defaults to offline-safe/local behavior unless API keys are configured.
6. Dashboard and diagnostics panels load with safe empty states when no market data exists.

## Logs, Config, Database, and Export Paths

Default paths in development and packaged-mode diagnostics:

- logs: `logs/`
- config: `config/`
- database: `data/institutional_bounce.db`
- data: `data/`
- exports: `exports/results/`
- backups: `data/backups/`
- resources: `resources/`

Packaged resources are resolved through `ResourcePathService`, which supports both development paths and PyInstaller `_MEIPASS` paths.

## Clean Windows Validation Steps

1. Start from a clean Windows user profile or clean VM snapshot.
2. Copy or install the RC1 package.
3. Launch `InstitutionalBounceScreener.exe`.
4. Confirm the main window opens.
5. Open diagnostics/about view and confirm startup diagnostics are available.
6. Confirm logs directory is created or writable.
7. Confirm config and bundled resources are available.
8. Confirm database initialization warning, if any, is non-fatal.
9. Confirm exports directory can be written.
10. Confirm provider configuration does not require API keys for offline/local validation.
11. Run RC1 smoke workflows if source checkout is available.

## Clean-Install Readiness Script

From the repository, run:

```powershell
.venv\Scripts\python.exe scripts\verify_clean_install_readiness.py
```

Expected result:

```text
Status: PASS
```

The script checks repository documentation and packaging prerequisites only. It does not launch the app, build the executable, or call live providers.

## Failure Handling

If validation fails:

1. Record the failed step and affected path.
2. Fix documentation, packaging configuration, or resource inclusion.
3. Re-run clean-install readiness verification.
4. Re-run RC1 packaging verification.
5. Re-run RC1 smoke tests before release handoff.
