# Release Candidate Punch List

This punch list records final repository review findings before v2.0 RC1 packaging. It groups work by release priority and distinguishes blockers from accepted cleanup items.

## Blocker Priority

- None currently documented.

Blockers must be fixed before RC1 packaging. Examples include missing release-critical scripts, missing release validation documents, or failures that prevent the RC1 regression runner from executing.

## High Priority

- None currently documented.

High-priority items should be resolved before final packaging unless explicitly accepted by the release owner.

## Medium Priority

- Review any direct service/controller modules reported without one-to-one test files. Some modules may be covered through integration tests; document accepted cases rather than creating brittle duplicate tests.
- Review runtime artifacts before packaging and confirm release scripts exclude cache, log, build, and temporary output folders.

## Low Priority

- Review TODO/FIXME comments reported by `scripts/repository_review.py` and either resolve them or document why they are acceptable for RC1.
- Review modules not explicitly represented in `docs/PROJECT_MANIFEST.md` and add subsystem-level documentation where release-critical.
- Review stale documentation references if reported after documentation edits.

## Required Evidence

Before closing the punch list for RC1:

1. Run `scripts\repository_review.py`.
2. Confirm no blocker findings remain.
3. Run `scripts\run_rc1_regression.py`.
4. Run `scripts\verify_packaging.py`.
5. Run `scripts\verify_clean_install_readiness.py`.
6. Run the full pytest suite.

## Acceptance Rule

RC1 can be declared ready when:

- blocker priority is empty,
- high-priority findings are fixed or accepted,
- medium and low findings are documented,
- regression, packaging, and clean-install validation pass.
