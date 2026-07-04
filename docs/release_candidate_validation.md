# Release Candidate Validation

The Release Candidate Validation Suite is the final automated readiness pass before tagging a v2.0 release candidate. It does not replace subsystem diagnostics; it aggregates their existing results into one release-focused decision.

## Checks

The suite validates:

- Startup Diagnostics
- Production Readiness Dashboard
- Provider Configuration
- Provider Health
- Full Universe Validation
- Screening Diagnostics
- Model Calibration
- Export System
- Packaging Status

Each check returns:

- check name
- status: `passed`, `warning`, or `failed`
- reason
- severity
- recommended fix

## Overall Status

- `ready`: all checks passed.
- `ready_with_warnings`: no checks failed, but one or more checks need review.
- `blocked`: at least one check failed.

## Workflow

1. Run startup and production readiness diagnostics.
2. Validate market data provider configuration and provider health.
3. Confirm the full universe validation and latest screening diagnostics are acceptable.
4. Review model calibration status.
5. Verify export and packaging readiness.
6. Resolve all failed checks before cutting the release candidate.

Warnings can be accepted only when they are understood and documented. Failed checks block the release candidate.
