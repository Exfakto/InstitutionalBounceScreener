# Changelog

## v1.0-RC2 - 2026-06-29

### Added

- Bounce Validation Engine foundation.
- Historical support-zone bounce validation metrics.
- SQLite `bounce_validations` persistence.
- Bounce validation service and controller workflow.
- Dashboard stat and action for validated zones.
- Tests for bounce calculations, persistence, and service orchestration.

### Verified

- Unit test suite passes.
- Application source compiles successfully.

## v1.0-RC1 - 2026-06-29

### Added

- Support Detection Engine foundation.
- Swing-low detection, support-zone clustering, and support-strength scoring.
- SQLite `support_levels` persistence.
- Support detection service and controller workflow.
- Dashboard action for detecting support zones.
- Tests for support calculations, persistence, and service orchestration.

### Verified

- Unit test suite passes.
- Application source compiles successfully.

## v0.9.0 - 2026-06-29

### Added

- Project manifest with architectural boundaries and release scope.
- Base indicator foundation.
- SMA20, SMA50, and SMA200 indicator calculations.
- Indicator service workflow for calculating and persisting SMA values.
- Indicator controller for dashboard integration.
- Dashboard action for calculating indicators.
- Tests for SMA calculations and indicator service orchestration.

### Changed

- Repaired DatabaseManager indicator and price-history methods.
- Updated README project status for v0.9.0.
- Replaced release-blocking console output with logging.
- Repaired the legacy `main.py` entry point.

### Verified

- Unit test suite passes.
- Application source compiles successfully.
