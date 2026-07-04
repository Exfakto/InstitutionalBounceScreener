from controllers.model_calibration_controller import ModelCalibrationController
from services.model_calibration_apply_service import CalibrationApplyResult
from services.model_calibration_integration_audit_service import (
    CalibrationIntegrationAuditResult,
)
from services.model_calibration_validation_service import CalibrationValidationResult
from services.model_calibration_recommendation_service import (
    CalibrationRecommendationView,
    ModelCalibrationRecommendationService,
)


def test_model_calibration_controller_delegates_to_service():
    class FakeService:
        def __init__(self):
            self.run_id = None

        def get_recommendations(self, run_id=None):
            self.run_id = run_id
            return [
                CalibrationRecommendationView(
                    title="Minimum Final Score",
                    severity="HIGH",
                    recommended_action="75",
                    reason="Weak lower buckets",
                    related_metric="minimum_final_score",
                )
            ]

    service = FakeService()
    controller = ModelCalibrationController(recommendation_service=service)

    result = controller.get_calibration_recommendations(run_id="cal-1")

    assert service.run_id == "cal-1"
    assert result[0].title == "Minimum Final Score"


def test_model_calibration_recommendation_service_fetches_latest_run():
    class FakeRepository:
        def fetch_latest_calibration_run(self):
            return {"run_id": "cal-1", "completed_at": "2026-01-03T00:00:00Z"}

        def fetch_calibration_recommendations(self, run_id):
            assert run_id == "cal-1"
            return [
                {
                    "recommendation_id": "rec-1",
                    "run_id": "cal-1",
                    "category": "minimum_support_score",
                    "recommended_value": 70,
                    "rationale": "Support score weakness",
                    "confidence": "MEDIUM",
                    "created_at": "2026-01-02T00:00:00Z",
                }
            ]

    service = ModelCalibrationRecommendationService(FakeRepository())

    result = service.get_recommendations()

    assert len(result) == 1
    assert result[0].title == "Minimum Support Score"
    assert result[0].severity == "MEDIUM"
    assert result[0].recommended_action == "70"
    assert result[0].reason == "Support score weakness"
    assert result[0].related_metric == "minimum_support_score"
    assert result[0].timestamp == "2026-01-02T00:00:00Z"


def test_model_calibration_recommendation_service_sorts_by_severity_then_timestamp():
    class FakeRepository:
        def fetch_calibration_recommendations(self, run_id):
            return [
                {
                    "category": "minimum_bounce_score",
                    "recommended_value": 70,
                    "rationale": "Older medium",
                    "confidence": "MEDIUM",
                    "created_at": "2026-01-01T00:00:00Z",
                },
                {
                    "category": "minimum_final_score",
                    "recommended_value": 75,
                    "rationale": "High severity",
                    "confidence": "HIGH",
                    "created_at": "2026-01-01T00:00:00Z",
                },
                {
                    "category": "minimum_support_score",
                    "recommended_value": 72,
                    "rationale": "Newer medium",
                    "confidence": "MEDIUM",
                    "created_at": "2026-01-03T00:00:00Z",
                },
            ]

    service = ModelCalibrationRecommendationService(FakeRepository())

    result = service.get_recommendations(run_id="cal-1")

    assert [item.related_metric for item in result] == [
        "minimum_final_score",
        "minimum_support_score",
        "minimum_bounce_score",
    ]


def test_model_calibration_recommendation_service_empty_without_run():
    class FakeRepository:
        def fetch_latest_calibration_run(self):
            return None

    service = ModelCalibrationRecommendationService(FakeRepository())

    assert service.get_recommendations() == []


def test_model_calibration_recommendation_service_propagates_repository_errors():
    class FakeRepository:
        def fetch_latest_calibration_run(self):
            raise RuntimeError("database unavailable")

    service = ModelCalibrationRecommendationService(FakeRepository())

    try:
        service.get_recommendations()
    except RuntimeError as exc:
        assert "database unavailable" in str(exc)
    else:
        raise AssertionError("Expected repository error to propagate")


def test_model_calibration_controller_apply_delegates_to_service():
    class ApplyService:
        def __init__(self):
            self.recommendations = None
            self.confirmed = None

        def apply_recommendations(self, recommendations, confirmed=False):
            self.recommendations = recommendations
            self.confirmed = confirmed
            return CalibrationApplyResult(status="applied", message="Applied 1")

    recommendation = CalibrationRecommendationView(
        title="Minimum Final Score",
        severity="HIGH",
        recommended_action="75",
        reason="Weak buckets",
        related_metric="minimum_final_score",
    )
    service = ApplyService()
    controller = ModelCalibrationController(apply_service=service)

    result = controller.apply_calibration_recommendations(
        [recommendation],
        confirmed=True,
    )

    assert service.recommendations == [recommendation]
    assert service.confirmed is True
    assert result.status == "applied"


def test_model_calibration_controller_validate_delegates_to_service():
    class ValidationService:
        def __init__(self):
            self.current_settings = None
            self.proposed_settings = None

        def validate_changes(self, current_settings=None, proposed_settings=None):
            self.current_settings = current_settings
            self.proposed_settings = proposed_settings
            return CalibrationValidationResult(status="passed", message="ok")

    service = ValidationService()
    controller = ModelCalibrationController(validation_service=service)

    result = controller.validate_calibration_changes(
        current_settings={"a": 1},
        proposed_settings={"b": 2},
    )

    assert service.current_settings == {"a": 1}
    assert service.proposed_settings == {"b": 2}
    assert result.status == "passed"


def test_model_calibration_controller_audit_delegates_to_service():
    class AuditService:
        def __init__(self):
            self.controller = None
            self.repository = None

        def audit(self, controller=None, repository=None):
            self.controller = controller
            self.repository = repository
            return CalibrationIntegrationAuditResult(items=[])

    repository = object()
    service = AuditService()
    controller = ModelCalibrationController(
        repository=repository,
        audit_service=service,
    )

    result = controller.audit_calibration_integration()

    assert service.controller is controller
    assert service.repository is repository
    assert result.status == "Pass"
