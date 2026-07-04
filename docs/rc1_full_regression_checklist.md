# RC1 Full Regression Checklist

This checklist defines the repeatable RC1 regression sequence that must pass before final packaging. It is validation tooling only and does not require live market data access or API keys.

## Regression Command

Run the ordered regression runner from the repository root:

```powershell
.venv\Scripts\python.exe scripts\run_rc1_regression.py
```

Optional fast-fail mode:

```powershell
.venv\Scripts\python.exe scripts\run_rc1_regression.py --stop-on-failure
```

Expected result:

```text
RC1 Full Regression Summary
Overall: PASS
```

## Required Sequence

The regression runner executes these sections in order:

1. Startup validation.
2. RC1 smoke tests.
3. Repository architecture audit.
4. Production readiness and release-candidate validation.
5. Provider configuration, health, failover, and resilience validation.
6. Model calibration validation.
7. Export workflow validation.
8. Packaging verification.
9. Clean Windows install readiness validation.

## Startup

Validates application startup and main-window smoke coverage. This confirms the app can initialize without unhandled exceptions in the RC1 test environment.

## Smoke Tests

Validates mocked screening, export, and UI smoke paths:

- startup completes,
- dashboard and key panels initialize,
- mocked screening produces results,
- export workflow completes without live provider calls.

## Architecture Audit

Validates Repository -> Services -> Controllers -> UI layering and checks for forbidden dependencies, missing tests, orphaned files, and naming drift.

## Production Readiness

Validates startup diagnostics, health checks, production readiness dashboard behavior, and release-candidate validation aggregation.

## Provider Validation

Validates provider configuration, provider health, failover history, resilience, retries, and offline/local-safe behavior. Tests use mocked providers only.

## Calibration

Validates model calibration persistence, recommendation generation, UI rendering, history, trends, comparison, apply flow, automated validation, and integration audit.

## Export

Validates ranked candidate exports, beta reports, signal-quality exports, and end-to-end export workflow behavior.

## Packaging

Validates release-freeze documentation and packaging prerequisites through `scripts/verify_packaging.py`.

## Clean Install

Validates clean Windows install readiness through `scripts/verify_clean_install_readiness.py`, including documented dependencies, runtime folders, first-launch behavior, and logs/config/database/export paths.

## Failure Handling

If any section fails:

1. Review the failed section summary.
2. Re-run the failed section directly with pytest.
3. Fix the smallest release-blocking issue.
4. Re-run `scripts\run_rc1_regression.py`.
5. Re-run the full pytest suite before final packaging.

## Final Packaging Gate

Final RC1 packaging can proceed only when:

- RC1 full regression summary is `PASS`,
- full pytest suite passes,
- packaging verification passes,
- clean Windows install readiness passes,
- no critical blockers remain in the release freeze checklist.
