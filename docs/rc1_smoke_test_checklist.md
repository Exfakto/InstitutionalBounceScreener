# RC1 Smoke Test Checklist

The RC1 smoke test suite is the fast release-candidate sanity check. It verifies that the application starts, key panels initialize, a mocked screening run completes, results display, and exports are generated without requiring live provider calls.

## Test Files

- `tests/test_rc1_smoke_startup.py`
- `tests/test_rc1_smoke_screening.py`
- `tests/test_rc1_smoke_export.py`
- `tests/test_rc1_smoke_ui.py`

## What RC1 Smoke Covers

- Application startup and `MainWindow` construction
- Dashboard panel initialization
- Screening results panel initialization
- Provider health panel initialization
- Screening diagnostics and production readiness panel initialization
- Mocked screening orchestration
- Candidate ranking and results display
- CSV export with mocked ranked results
- Offline execution with no live provider/API calls

## Run Command

```powershell
.venv\Scripts\python.exe -m pytest tests/test_rc1_smoke_startup.py tests/test_rc1_smoke_screening.py tests/test_rc1_smoke_export.py tests/test_rc1_smoke_ui.py -q
```

## Passing Criteria

- All RC1 smoke tests pass.
- No API keys are required.
- No real network calls are made.
- Temporary export files are written only to pytest temporary directories.
- No unhandled UI construction exceptions occur.

## Follow-Up

After RC1 smoke passes, run:

```powershell
.venv\Scripts\python.exe -m pytest -q
```

Then run Release Candidate Validation and the repository architecture audit before packaging.
