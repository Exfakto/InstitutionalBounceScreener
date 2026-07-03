# Build And Release

## Output Folder

Release artifacts are written to:

```powershell
dist/
```

Temporary build files are written to:

```powershell
build/
```

## Run Release Checks

```powershell
scripts/run_release_checks.ps1
```

This compiles application modules and runs the test suite.

## Build Executable

```powershell
scripts/build_release.ps1 -Clean
```

The script uses `InstitutionalBounceScreener.spec` and `app_entry.py`.

## Troubleshooting

- If PyInstaller is missing, install it in the active virtual environment before building.
- If resources are missing, confirm `config/`, `data/`, `docs/`, and `resources/` exist.
- If the app cannot write exports, update the default export directory in Settings.
- If restore fails, verify the backup is a valid SQLite database.
