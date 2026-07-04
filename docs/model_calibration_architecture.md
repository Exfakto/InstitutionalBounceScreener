# Model Calibration Architecture

The model calibration module is a recommendation-only layer around historical validation and signal quality results. It does not automatically change production scoring defaults.

## Components

- Persistence: `DatabaseManager` stores calibration runs and recommendations through the existing SQLite persistence layer.
- Analysis: `ModelCalibrationService` converts V8 validation and V9 signal quality evidence into calibration recommendations.
- Recommendations: `ModelCalibrationRecommendationService` exposes UI/export-ready recommendation DTOs.
- Recommendation Export: beta review pack and beta report export services include calibration recommendations without duplicating recommendation logic.
- History: `ModelCalibrationHistoryService` reads historical calibration runs and normalizes them into typed history items.
- Trend Visualization: `ModelCalibrationTrendService` prepares trend points for overall score, precision, recall, F1, calibration error, and sample size.
- Version Comparison: `ModelCalibrationComparisonService` compares two historical calibration runs and classifies metric deltas.
- Apply Recommendations: `ModelCalibrationApplyService` converts confirmed recommendations into settings updates and persists them through the existing settings infrastructure.
- Automated Validation: `ModelCalibrationValidationService` validates proposed settings against historical before/after metrics and blocks promotion on failed validation.
- Integration Audit: `ModelCalibrationIntegrationAuditService` verifies controller wiring, dependency injection, repository capabilities, and optional analysis/export availability.

## Controller Surface

`ModelCalibrationController` exposes the calibration module to UI and workflow code:

- `get_calibration_recommendations(run_id=None)`
- `get_calibration_history(limit=25, offset=0)`
- `get_calibration_run_details(run_id)`
- `get_calibration_trend(window="Last 25")`
- `compare_calibration_runs(base_run_id, comparison_run_id)`
- `apply_calibration_recommendations(recommendations, confirmed=False)`
- `validate_calibration_changes(current_settings=None, proposed_settings=None)`
- `audit_calibration_integration()`

## Data Flow

1. Validation and signal quality analysis produce evidence.
2. `ModelCalibrationService` generates recommendations and saves them with a calibration run.
3. Recommendation, history, trend, and comparison services read from the same persistence layer.
4. UI panels render typed DTOs only.
5. Users may explicitly validate and apply recommendations.
6. Settings changes are saved through the existing settings repository/service path.
7. Integration audit can be run to verify production readiness without mutating state.

## Safety Rules

- No recommendation is auto-applied.
- Apply requires explicit confirmation.
- Validation can block promotion when metric regressions exceed tolerances.
- No new storage mechanism is introduced.
- Audit logic is read-only and does not alter calibration behavior.
