from services.model_calibration_apply_service import ModelCalibrationApplyService
from services.model_calibration_recommendation_service import CalibrationRecommendationView


class SettingsRepository:
    def __init__(self, fail=False):
        self.values = {}
        self.fail = fail

    def set_setting(self, key, value):
        if self.fail:
            raise RuntimeError("settings unavailable")
        self.values[key] = value
        return value


def recommendation(metric, action, title="Recommendation"):
    return CalibrationRecommendationView(
        title=title,
        severity="HIGH",
        recommended_action=action,
        reason="validation evidence",
        related_metric=metric,
    )


def test_apply_requires_explicit_confirmation():
    repository = SettingsRepository()
    service = ModelCalibrationApplyService(repository)

    result = service.apply_recommendations(
        [recommendation("minimum_final_score", "75")],
        confirmed=False,
    )

    assert result.status == "skipped"
    assert result.skipped[0]["reason"] == "Confirmation required"
    assert repository.values == {}


def test_apply_score_threshold_recommendation():
    repository = SettingsRepository()
    service = ModelCalibrationApplyService(repository)

    result = service.apply_recommendations(
        [recommendation("minimum_final_score", "75")],
        confirmed=True,
    )

    assert result.status == "applied"
    assert repository.values["calibration.minimum_final_score"] == 75.0
    assert result.failed == []


def test_apply_confidence_threshold_recommendation():
    repository = SettingsRepository()
    service = ModelCalibrationApplyService(repository)

    result = service.apply_recommendations(
        [
            recommendation(
                "confidence_filtering_rules",
                "Require MEDIUM or HIGH confidence",
                title="Confidence Filtering Rules",
            )
        ],
        confirmed=True,
    )

    assert result.status == "applied"
    assert repository.values["calibration.confidence_threshold"] == "MEDIUM"


def test_apply_weight_adjustment_recommendation():
    repository = SettingsRepository()
    service = ModelCalibrationApplyService(repository)

    result = service.apply_recommendations(
        [recommendation("support_weight", {"support": 0.35, "technical": 0.25})],
        confirmed=True,
    )

    assert result.status == "applied"
    assert repository.values["calibration.scoring_weights"] == {
        "support": 0.35,
        "technical": 0.25,
    }


def test_apply_validation_failure_for_bad_threshold():
    repository = SettingsRepository()
    service = ModelCalibrationApplyService(repository)

    result = service.apply_recommendations(
        [recommendation("minimum_bounce_score", "125")],
        confirmed=True,
    )

    assert result.status == "failed"
    assert result.failed[0]["reason"] == "Score thresholds must be between 0 and 100."
    assert repository.values == {}


def test_apply_validation_failure_for_bad_weight():
    repository = SettingsRepository()
    service = ModelCalibrationApplyService(repository)

    result = service.apply_recommendations(
        [recommendation("support_weight", {"support": 1.5})],
        confirmed=True,
    )

    assert result.status == "failed"
    assert "between 0 and 1" in result.failed[0]["reason"]


def test_apply_settings_failure_returns_failed_result():
    service = ModelCalibrationApplyService(SettingsRepository(fail=True))

    result = service.apply_recommendations(
        [recommendation("minimum_support_score", "70")],
        confirmed=True,
    )

    assert result.status == "failed"
    assert "settings unavailable" in result.failed[0]["reason"]


def test_apply_unsupported_recommendation_is_skipped():
    repository = SettingsRepository()
    service = ModelCalibrationApplyService(repository)

    result = service.apply_recommendations(
        [recommendation("manual_review", "Review weak groups")],
        confirmed=True,
    )

    assert result.status == "skipped"
    assert result.skipped[0]["reason"] == "Unsupported recommendation"
    assert repository.values == {}
