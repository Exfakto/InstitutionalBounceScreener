from services.model_calibration_validation_service import (
    ModelCalibrationValidationService,
)


class HistoryService:
    def __init__(self, rows):
        self.rows = rows
        self.limit = None

    def get_history(self, limit=2):
        self.limit = limit
        return list(self.rows)


def run(
    run_id,
    overall_score,
    precision,
    recall,
    f1_score,
    calibration_error,
    sample_size,
):
    return {
        "run_id": run_id,
        "overall_score": overall_score,
        "precision": precision,
        "recall": recall,
        "f1_score": f1_score,
        "confidence_calibration_error": calibration_error,
        "sample_size": sample_size,
    }


def metric(result, name):
    return next(item for item in result.metrics if item.metric == name)


def test_calibration_validation_passes_when_metrics_improve():
    history = HistoryService(
        [
            run("after", 80, 0.7, 0.6, 0.65, 0.08, 120),
            run("before", 70, 0.6, 0.5, 0.55, 0.1, 100),
        ]
    )

    result = ModelCalibrationValidationService(history_service=history).validate_changes(
        current_settings={"calibration.minimum_final_score": 70},
        proposed_settings={"calibration.minimum_final_score": 75},
    )

    assert history.limit == 2
    assert result.status == "passed"
    assert result.promotion_blocked is False
    assert metric(result, "overall_score").before == 70.0
    assert metric(result, "overall_score").after == 80.0
    assert metric(result, "confidence_calibration_error").regressed is False


def test_calibration_validation_fails_and_blocks_promotion_on_regression():
    history = HistoryService(
        [
            run("after", 65, 0.5, 0.45, 0.48, 0.15, 100),
            run("before", 70, 0.6, 0.5, 0.55, 0.1, 100),
        ]
    )

    result = ModelCalibrationValidationService(history_service=history).validate_changes(
        proposed_settings={"calibration.minimum_final_score": 75}
    )

    assert result.status == "failed"
    assert result.promotion_blocked is True
    assert metric(result, "overall_score").regressed is True
    assert metric(result, "confidence_calibration_error").regressed is True
    assert result.errors


def test_calibration_validation_warning_for_insufficient_history():
    result = ModelCalibrationValidationService(
        history_service=HistoryService([run("after", 80, 0.7, 0.6, 0.65, 0.08, 120)])
    ).validate_changes(proposed_settings={"calibration.minimum_final_score": 75})

    assert result.status == "warning"
    assert result.metrics == []
    assert result.promotion_blocked is False
    assert "Insufficient historical calibration data" in result.warnings[0]


def test_calibration_validation_warning_without_proposed_settings():
    history = HistoryService(
        [
            run("after", 80, 0.7, 0.6, 0.65, 0.08, 120),
            run("before", 70, 0.6, 0.5, 0.55, 0.1, 100),
        ]
    )

    result = ModelCalibrationValidationService(history_service=history).validate_changes()

    assert result.status == "warning"
    assert "No proposed calibration settings supplied." in result.warnings


def test_calibration_validation_uses_tolerance():
    history = HistoryService(
        [
            run("after", 69.9, 0.6, 0.5, 0.55, 0.1005, 100),
            run("before", 70.0, 0.6, 0.5, 0.55, 0.1, 100),
        ]
    )

    result = ModelCalibrationValidationService(
        history_service=history,
        tolerances={"overall_score": 0.2, "confidence_calibration_error": 0.01},
    ).validate_changes(proposed_settings={"calibration.minimum_final_score": 75})

    assert result.status == "passed"
    assert metric(result, "overall_score").regressed is False
    assert metric(result, "confidence_calibration_error").regressed is False
