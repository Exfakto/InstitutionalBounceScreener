# End-to-End Validation

The end-to-end validation suite verifies that the major application workflows connect cleanly from startup through exported results without making live network calls.

## Covered Workflows

- Application startup and main window construction
- Universe ticker normalization/loading
- Live screening orchestration
- Technical, support, bounce, institutional, composite scoring, and ranking handoff
- Results table display
- Ranked candidate CSV export
- Ranked candidate JSON export
- Full screening run package export
- Model calibration recommendation generation
- Calibration controller recommendation, validation, and audit access
- Provider failover, provider health, provider configuration validation, and failover history

## Test Files

- `tests/test_end_to_end_screening_workflow.py`
- `tests/test_end_to_end_export_workflow.py`
- `tests/test_end_to_end_calibration_workflow.py`
- `tests/test_end_to_end_provider_workflow.py`

## Mocking Policy

External providers are mocked at the provider boundary. The tests do not perform real HTTP calls, do not require API keys, and do not write to production data files.

The screening workflow uses recording fakes for market data and scoring stages so the test can verify that every stage is invoked in order while still exercising the real `ScreeningOrchestrator`, candidate ranking path, and results panel rendering.

The export workflow writes to a pytest temporary directory and verifies generated file contents.

## Passing Criteria

A passing end-to-end validation run means:

- The application can start without unhandled exceptions.
- The screening pipeline can process normalized tickers and produce ranked candidates.
- Ranked candidates can be displayed in the UI results panel.
- Export services can generate CSV, JSON, and full run package artifacts.
- Calibration recommendations flow from analysis through controller-facing views.
- Provider failover is recorded and visible through controller-level health/history APIs.

These tests are not performance benchmarks and do not validate live provider credentials. They are release-safety checks for workflow integration.
