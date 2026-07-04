from types import SimpleNamespace

from controllers.model_calibration_controller import ModelCalibrationController
from services.model_calibration_service import ModelCalibrationService


class CalibrationWorkflowRepository:
    def __init__(self):
        self.runs = {}
        self.recommendations = {}
        self.settings = {}

    def save_calibration_run(self, run):
        self.runs[run.run_id] = run
        return run

    def save_calibration_recommendations(self, run_id, recommendations):
        self.recommendations[run_id] = list(recommendations or [])
        return list(recommendations or [])

    def fetch_latest_calibration_run(self):
        return list(self.runs.values())[-1] if self.runs else None

    def fetch_calibration_recommendations(self, run_id):
        return list(self.recommendations.get(run_id, []))

    def fetch_calibration_run_history(self, limit=25, offset=0):
        rows = [
            SimpleNamespace(
                run_id="history-after",
                completed_at="2026-07-04T11:00:00+00:00",
                status="COMPLETED",
                summary="After calibration",
                summary_metrics={
                    "model_version": "v2.0",
                    "overall_score": 84.0,
                    "precision": 0.72,
                    "recall": 0.68,
                    "f1_score": 0.70,
                    "confidence_calibration_error": 0.05,
                    "sample_size": 150,
                },
            ),
            SimpleNamespace(
                run_id="history-before",
                completed_at="2026-07-03T11:00:00+00:00",
                status="COMPLETED",
                summary="Before calibration",
                summary_metrics={
                    "model_version": "v1.9",
                    "overall_score": 80.0,
                    "precision": 0.70,
                    "recall": 0.65,
                    "f1_score": 0.67,
                    "confidence_calibration_error": 0.06,
                    "sample_size": 140,
                },
            ),
        ]
        return rows[offset : offset + limit]

    def fetch_calibration_run(self, run_id):
        return self.runs.get(run_id)

    def clear_calibration_run(self, run_id):
        self.runs.pop(run_id, None)
        self.recommendations.pop(run_id, None)
        return 1

    def set_setting(self, key, value):
        self.settings[key] = value
        return value


def test_end_to_end_calibration_workflow_recommendations_validation_and_audit():
    repository = CalibrationWorkflowRepository()
    calibration_service = ModelCalibrationService(repository=repository)
    signal_quality_report = SimpleNamespace(
        report_id="quality-1",
        weak_groups=[
            {
                "dimension": "final_score_bucket",
                "group": "60-70",
                "weak": True,
                "win_rate": 0.35,
                "expectancy": -0.2,
            },
            {
                "dimension": "confidence_level",
                "group": "LOW",
                "weak": True,
                "win_rate": 0.30,
            },
        ],
        warnings=[],
    )

    calibration = calibration_service.calibrate(
        validation_result=SimpleNamespace(run_id="validation-1"),
        signal_quality_report=signal_quality_report,
        run_id="calibration-e2e",
    )
    controller = ModelCalibrationController(
        repository=repository,
        analysis_service=calibration_service,
    )

    recommendations = controller.get_calibration_recommendations()
    validation = controller.validate_calibration_changes(
        current_settings={"minimum_final_score": 60},
        proposed_settings={"minimum_final_score": 70},
    )
    audit = controller.audit_calibration_integration()

    assert calibration["run"].run_id == "calibration-e2e"
    assert calibration["recommendations"]
    assert recommendations[0].run_id == "calibration-e2e"
    assert any(item.related_metric == "minimum_final_score" for item in recommendations)
    assert validation.status == "passed"
    assert validation.promotion_blocked is False
    assert audit.items
    assert {item.status for item in audit.items} <= {"Pass", "Warning"}
