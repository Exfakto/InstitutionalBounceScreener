from services.model_calibration_integration_audit_service import (
    ModelCalibrationIntegrationAuditService,
)


class CompleteRepository:
    def save_calibration_run(self, run):
        return run

    def save_calibration_recommendations(self, run_id, recommendations):
        return recommendations

    def fetch_latest_calibration_run(self):
        return None

    def fetch_calibration_recommendations(self, run_id):
        return []

    def fetch_calibration_run_history(self, limit=25, offset=0):
        return []

    def fetch_calibration_run(self, run_id):
        return None

    def clear_calibration_run(self, run_id):
        return 0


class CompleteController:
    recommendation_service = object()
    history_service = object()
    trend_service = object()
    comparison_service = object()
    apply_service = object()
    validation_service = object()
    analysis_service = object()
    export_service = object()

    def get_calibration_recommendations(self, run_id=None):
        return []

    def get_calibration_history(self, limit=25, offset=0):
        return []

    def get_calibration_run_details(self, run_id):
        return None

    def get_calibration_trend(self, window="Last 25"):
        return None

    def compare_calibration_runs(self, base_run_id, comparison_run_id):
        return None

    def apply_calibration_recommendations(self, recommendations, confirmed=False):
        return None

    def validate_calibration_changes(self, current_settings=None, proposed_settings=None):
        return None


def item(result, component):
    return next(entry for entry in result.items if entry.component_name == component)


def test_calibration_integration_audit_complete_integration_passes():
    result = ModelCalibrationIntegrationAuditService().audit(
        controller=CompleteController(),
        repository=CompleteRepository(),
    )

    assert result.status == "Pass"
    assert all(entry.status == "Pass" for entry in result.items)
    assert item(result, "Persistence").status == "Pass"
    assert item(result, "Automated Validation").status == "Pass"


def test_calibration_integration_audit_detects_missing_dependencies():
    class PartialController(CompleteController):
        trend_service = None

    result = ModelCalibrationIntegrationAuditService().audit(
        controller=PartialController(),
        repository=CompleteRepository(),
    )

    assert result.status == "Fail"
    trend = item(result, "Trend Visualization")
    assert trend.status == "Fail"
    assert "missing dependencies" in trend.issue_description


def test_calibration_integration_audit_detects_failed_repository_component():
    class IncompleteRepository:
        def fetch_latest_calibration_run(self):
            return None

    result = ModelCalibrationIntegrationAuditService().audit(
        controller=CompleteController(),
        repository=IncompleteRepository(),
    )

    assert result.status == "Fail"
    persistence = item(result, "Persistence")
    assert persistence.status == "Fail"
    assert "save_calibration_run" in persistence.issue_description


def test_calibration_integration_audit_warns_for_optional_analysis_export():
    class ControllerWithoutOptional(CompleteController):
        analysis_service = None
        export_service = None

    result = ModelCalibrationIntegrationAuditService().audit(
        controller=ControllerWithoutOptional(),
        repository=CompleteRepository(),
    )

    assert result.status == "Warning"
    assert item(result, "Analysis").status == "Warning"
    assert item(result, "Recommendation Export").status == "Warning"
