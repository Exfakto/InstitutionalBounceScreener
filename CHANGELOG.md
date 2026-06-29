# Changelog

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
