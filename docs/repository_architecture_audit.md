# Repository Architecture Audit

## Summary

This audit reviews the final v2.0 release-candidate codebase for architecture consistency, test coverage, naming consistency, and release readiness.

Overall result: **Passed with documented warnings**.

The repository follows the intended layered architecture:

```text
Repository -> Services -> Controllers -> UI
```

The application remains local-first, SQLite-backed, and PySide6-based. Business workflows live in services, controllers coordinate GUI-safe actions, and UI widgets render data and emit user intent.

## Passed Checks

- Services are covered by dedicated tests for the major release-critical workflows.
- Controllers are covered by dedicated tests for major coordination paths.
- UI widgets do not import the database layer directly.
- Services and repositories do not import UI modules except for documented application-shell boundaries.
- Provider resilience, provider failover logging, provider health, provider configuration validation, production readiness, and Release Candidate Validation are represented in tests.
- Model calibration has service, controller, UI panel, history, trend, comparison, apply, validation, audit, and export coverage.
- End-to-end validation tests cover startup, screening, ranking, result display, export generation, calibration, and provider failover.
- Documentation now reflects the v2.0 release-candidate architecture and validation workflow.
- Release-critical filenames are aligned with the actual repository structure, including `ui/widgets/dashboard.py` rather than a non-existent `dashboard_panel.py`.

## Documented Exceptions

### `services/exception_handler.py`

This service imports PySide6 to register a global exception handler and display user-friendly crash dialogs. It is intentionally a UI-adjacent infrastructure service and should remain isolated from business logic.

Recommended guardrail: keep all PySide6 usage in this file limited to exception presentation.

### `services/diagnostics_service.py`

This service imports PySide6 metadata to report the installed Qt/PySide version in diagnostics. It must remain metadata-only and must not create widgets, dialogs, or UI workflows.

Recommended guardrail: keep PySide6 usage in this file limited to version discovery.

### `controllers/application_controller.py`

This controller imports `ui.main_window.MainWindow` as the application shell boundary. It is intentionally responsible for constructing the GUI root.

Recommended guardrail: keep feature workflows out of this controller.

## Warnings

- Several legacy services still instantiate `DatabaseManager` directly. This is compatible with the current architecture but should gradually move toward repository injection where practical.
- `ui/main_window.py` remains a large orchestration file. It is stable, but future UI additions should prefer smaller widgets and controller/service delegation.
- Runtime folders such as `logs/`, `exports/`, `.pytest_cache/`, and `__pycache__/` may exist in working trees. These should stay out of release bundles.

## Compatibility and Legacy Modules

- `main.py` remains a compatibility entry point for launching the application.
- `app.py` and `app_entry.py` are application entry-point helpers for development and packaging workflows.
- `providers/provider_manager.py`, `providers/provider_config.py`, and `providers/cache_manager.py` remain legacy-compatible provider infrastructure while newer market-data workflows also use `market_data/` and provider resilience services.
- `services/exception_handler.py` and `services/diagnostics_service.py` are documented PySide6 service-layer exceptions.
- `controllers/application_controller.py` is the documented application-shell boundary that constructs `ui.main_window.MainWindow`.
- No `ui/widgets/dashboard_panel.py` file exists; the dashboard widget is `ui/widgets/dashboard.py`.

## Failures

No blocking architecture failures were identified by the automated audit.

## Recommended Fixes

1. Continue keeping UI imports out of services except the documented exception-handler boundary.
2. Continue keeping direct database access out of UI and controller files.
3. Prefer constructor injection for new services that need persistence.
4. Split new MainWindow features into reusable widgets before wiring them into the shell.
5. Keep provider calls behind provider/service abstractions and mock them in tests.
6. Review release bundles for runtime artifacts before packaging.
7. Keep end-to-end workflow tests current as release-critical workflows change.

## Automated Audit Coverage

The audit is enforced by `tests/test_repository_architecture_audit.py`.

It checks:

- forbidden UI/PySide imports inside services and database modules, with documented exceptions
- forbidden UI imports inside controllers, with documented application-shell exception
- no direct database imports inside UI modules
- test coverage for major services
- test coverage for major controllers
- duplicate service module names
- documentation coverage for current release layers and v2.0 validation
