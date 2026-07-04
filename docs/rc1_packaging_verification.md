# RC1 Packaging Verification

RC1 packaging verification is a deterministic preflight check for the v2.0 release-candidate package. It validates required files and metadata without building the executable and without making live market data calls.

## Verification Script

Run:

```powershell
.venv\Scripts\python.exe scripts\verify_packaging.py
```

Expected result:

```text
Status: PASS
Build output: dist/
```

## What It Checks

- application entry points:
  - `app.py`
  - `main.py`
  - `app_entry.py`
- configuration files:
  - `config/app_metadata.py`
  - `config/logging_config.py`
  - `config/providers.json`
  - `config/scoring.json`
  - `config/settings.py`
- resources and seed data:
  - `resources/README.md`
  - `data/market_universe_template.csv`
  - `data/market_universe_seed.csv`
- packaging files:
  - `InstitutionalBounceScreener.spec`
  - `scripts/build_release.ps1`
  - `scripts/run_release_checks.ps1`
  - `docs/BUILD_AND_RELEASE.md`
- release metadata:
  - `APPLICATION_NAME`
  - `VERSION`
  - `BUILD_DATE`
  - `BUILD_TIMESTAMP`
  - `RELEASE_CHANNEL`
  - `SCHEMA_VERSION`
- documented build output path: `dist/`

## Offline Guarantee

The verifier only inspects local files. It does not import live provider modules, does not perform HTTP requests, and does not require API keys.

## Build Output

Release artifacts are expected in:

```text
dist/
```

Temporary build output is expected in:

```text
build/
```

## Failure Handling

If verification fails:

1. Review missing paths or metadata printed by the script.
2. Restore the missing file or metadata.
3. Re-run packaging verification.
4. Re-run RC1 smoke tests before packaging.
