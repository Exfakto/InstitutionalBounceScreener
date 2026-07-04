# RC1 Release Freeze Checklist

This checklist defines the v2.0 RC1 feature freeze. Once the checklist is accepted, feature development stops and only release-blocking fixes, documentation corrections, and validation updates are allowed.

## Feature Freeze Rules

- No new application features after RC1 freeze.
- No scoring formula changes after RC1 freeze.
- No database schema changes after RC1 freeze unless required to fix a release blocker.
- No provider framework redesigns after RC1 freeze.
- No UI redesigns after RC1 freeze.
- Allowed changes are limited to critical bug fixes, test stabilization, documentation corrections, packaging fixes, and release validation.

## Required RC1 Validation Steps

Run and confirm:

1. RC1 smoke tests.
2. Full regression test suite.
3. Repository architecture audit.
4. Release Candidate Validation suite.
5. Production readiness dashboard review.
6. Provider configuration validation.
7. Provider health and failover history review.
8. Full universe validation.
9. Screening diagnostics review.
10. Export validation.
11. Packaging validation.
12. Documentation review.

## RC1 Smoke Tests

Required command:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_rc1_smoke_startup.py tests/test_rc1_smoke_screening.py tests/test_rc1_smoke_export.py tests/test_rc1_smoke_ui.py -q
```

Expected result: all RC1 smoke tests pass without live provider calls or API keys.

## Architecture Audit

Required command:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_repository_architecture_audit.py -q
```

Expected result: audit passes and any architecture exceptions are documented in `docs/repository_architecture_audit.md`.

## Production Readiness

Confirm:

- Startup diagnostics are passing or have accepted warnings.
- Production readiness dashboard status is `Ready` or explicitly accepted as `Ready with Warnings`.
- No `Not Ready` production readiness status remains unresolved.

## Provider Validation

Confirm:

- Provider configuration validation passes or has accepted warnings.
- At least one healthy provider or offline/local CSV path is configured for validation.
- Provider failover history is reviewable.
- No real network calls are required for automated tests.

## Full Universe Validation

Confirm:

- Full universe validation completes or reports only accepted warnings.
- Missing-data, provider, calculation, ranking, and export issues are reviewed.
- Full-market scan readiness is documented before RC1 handoff.

## Export Validation

Confirm:

- Ranked candidates CSV export works.
- Ranked candidates JSON export works.
- Full run package JSON export works.
- Export outputs are written to controlled output directories.

## Packaging Validation

Confirm:

- Release diagnostics pass or have accepted warnings.
- Build scripts exist.
- Packaged resource paths are validated.
- Database backup/restore health is reviewed.
- Release checklist documentation is current.

## Documentation Updated for v2.0 RC1

Confirm these documents are current:

- `README.md`
- `docs/PROJECT_MANIFEST.md`
- `docs/CODEX_INSTRUCTIONS.md`
- `docs/repository_architecture_audit.md`
- `docs/release_candidate_validation.md`
- `docs/end_to_end_validation.md`
- `docs/rc1_smoke_test_checklist.md`
- `docs/rc1_release_freeze_checklist.md`

## Critical Blockers

Current RC1 status: **No known critical blockers documented in this checklist.**

If a critical blocker is discovered after freeze:

1. Record the blocker and impacted subsystem.
2. Fix the smallest possible surface area.
3. Re-run RC1 smoke tests.
4. Re-run the relevant focused tests.
5. Re-run the full regression suite before RC1 handoff.

## Freeze Decision

RC1 is ready for feature freeze when:

- required validation steps are complete,
- no critical blockers remain,
- documentation is updated for v2.0 RC1,
- release artifacts and packaging checks are ready for candidate testing.
