from services.model_calibration_comparison_service import (
    ModelCalibrationComparisonService,
)


class HistoryService:
    def __init__(self, rows):
        self.rows = rows

    def get_run_details(self, run_id):
        return self.rows.get(run_id)


def run(run_id, **metrics):
    return {
        "run_id": run_id,
        "completed_at": f"2026-01-0{1 if run_id == 'base' else 2}T00:00:00Z",
        "status": metrics.pop("status", "COMPLETED"),
        **metrics,
    }


def metric(comparison, name):
    return next(item for item in comparison.metrics if item.metric == name)


def test_calibration_comparison_detects_improvements():
    service = ModelCalibrationComparisonService(
        history_service=HistoryService(
            {
                "base": run(
                    "base",
                    overall_score=70,
                    precision=0.5,
                    recall=0.4,
                    f1_score=0.45,
                    confidence_calibration_error=0.12,
                    sample_size=100,
                ),
                "new": run(
                    "new",
                    overall_score=80,
                    precision=0.6,
                    recall=0.5,
                    f1_score=0.55,
                    confidence_calibration_error=0.08,
                    sample_size=120,
                ),
            }
        )
    )

    comparison = service.compare_runs("base", "new")

    assert comparison.missing_run is False
    assert metric(comparison, "overall_score").classification == "improved"
    assert metric(comparison, "precision").delta == 0.09999999999999998
    assert metric(comparison, "confidence_calibration_error").classification == "improved"
    assert metric(comparison, "sample_size").percent_delta == 20.0


def test_calibration_comparison_detects_regressions():
    service = ModelCalibrationComparisonService(
        history_service=HistoryService(
            {
                "base": run("base", overall_score=80, confidence_calibration_error=0.08),
                "new": run("new", overall_score=70, confidence_calibration_error=0.12),
            }
        )
    )

    comparison = service.compare_runs("base", "new")

    assert metric(comparison, "overall_score").classification == "regressed"
    assert metric(comparison, "confidence_calibration_error").classification == "regressed"


def test_calibration_comparison_detects_unchanged_metrics_and_status_change():
    service = ModelCalibrationComparisonService(
        history_service=HistoryService(
            {
                "base": run("base", overall_score=80, status="COMPLETED"),
                "new": run("new", overall_score=80, status="NO_RECOMMENDATIONS"),
            }
        )
    )

    comparison = service.compare_runs("base", "new")

    assert metric(comparison, "overall_score").classification == "unchanged"
    assert metric(comparison, "status").classification == "changed"


def test_calibration_comparison_handles_missing_run():
    service = ModelCalibrationComparisonService(
        history_service=HistoryService({"base": run("base", overall_score=80)})
    )

    comparison = service.compare_runs("base", "missing")

    assert comparison.missing_run is True
    assert comparison.metrics == []
    assert "missing" in comparison.warnings[0]


def test_calibration_comparison_reads_summary_metrics_aliases():
    service = ModelCalibrationComparisonService(
        history_service=HistoryService(
            {
                "base": {
                    "run_id": "base",
                    "summary_metrics": {
                        "score": 70,
                        "precision": 0.5,
                        "recall": 0.4,
                        "f1": 0.45,
                        "calibration_error": 0.1,
                        "signal_count": 100,
                    },
                    "status": "COMPLETED",
                },
                "new": {
                    "run_id": "new",
                    "summary_metrics": {
                        "score": 75,
                        "precision": 0.55,
                        "recall": 0.45,
                        "f1": 0.5,
                        "calibration_error": 0.09,
                        "signal_count": 110,
                    },
                    "status": "COMPLETED",
                },
            }
        )
    )

    comparison = service.compare_runs("base", "new")

    assert metric(comparison, "overall_score").comparison_value == 75.0
    assert metric(comparison, "f1_score").comparison_value == 0.5
    assert metric(comparison, "sample_size").classification == "improved"
