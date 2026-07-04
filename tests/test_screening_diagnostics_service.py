from controllers.diagnostics_controller import DiagnosticsController
from services.screening_diagnostics_service import ScreeningDiagnosticsService
from services.screening_performance_analytics_service import (
    ScreeningPerformanceAnalytics,
    ScreeningStageTiming,
)


def analytics(stage_duration=1.0):
    stages = [
        ScreeningStageTiming("universe_loading", "Universe loading", stage_duration),
        ScreeningStageTiming("support_detection", "Support detection", 2.0),
    ]
    return ScreeningPerformanceAnalytics(
        run_id="run-1",
        total_screening_time_seconds=stage_duration + 2,
        average_time_per_symbol_seconds=1.5,
        symbol_count=2,
        slowest_stage=stages[0],
        stages=stages,
    )


class PerformanceService:
    def __init__(self, report):
        self.report = report

    def analyze_latest(self):
        return self.report

    def analyze_run(self, run):
        return self.report


class Repository:
    def __init__(self, run):
        self.run = run

    def fetch_latest_screening_run(self):
        return self.run


def test_screening_diagnostics_healthy_run():
    run = {"run_id": "run-1", "warnings": [], "errors": [], "stage_statuses": {}}
    service = ScreeningDiagnosticsService(
        repository=Repository(run),
        performance_analytics_service=PerformanceService(analytics()),
    )

    result = service.get_latest_diagnostics()

    assert result.overall_status == "passed"
    assert result.symbol_count == 2
    assert result.warning_count == 0
    assert result.error_count == 0
    assert result.stages[0].status == "passed"


def test_screening_diagnostics_slow_stage_warning():
    run = {"run_id": "run-1", "warnings": [], "errors": []}
    service = ScreeningDiagnosticsService(
        repository=Repository(run),
        performance_analytics_service=PerformanceService(analytics(stage_duration=45.0)),
        slow_stage_seconds=30,
    )

    result = service.get_latest_diagnostics()

    assert result.overall_status == "warning"
    assert result.stages[0].status == "warning"
    assert "unusually slow" in result.messages[0].message
    assert result.messages[0].recommended_action


def test_screening_diagnostics_failed_stage():
    run = {
        "run_id": "run-1",
        "warnings": [],
        "errors": ["support failed"],
        "stage_statuses": {"support_detection": "failed"},
    }
    service = ScreeningDiagnosticsService(
        repository=Repository(run),
        performance_analytics_service=PerformanceService(analytics()),
    )

    result = service.get_latest_diagnostics()

    assert result.overall_status == "failed"
    support = next(stage for stage in result.stages if stage.stage_key == "support_detection")
    assert support.status == "failed"
    assert result.error_count == 1
    assert any(message.severity == "failed" for message in result.messages)


def test_screening_diagnostics_empty_diagnostics():
    result = ScreeningDiagnosticsService(repository=Repository(None)).get_latest_diagnostics()

    assert result.overall_status == "warning"
    assert result.stages == []
    assert result.messages[0].message == "No screening run diagnostics available."


def test_diagnostics_controller_screening_integration():
    class ScreeningDiagnostics:
        def __init__(self):
            self.called = False

        def get_latest_diagnostics(self):
            self.called = True
            return "screening diagnostics"

    service = ScreeningDiagnostics()
    controller = DiagnosticsController(screening_diagnostics_service=service)

    assert controller.get_screening_diagnostics() == "screening diagnostics"
    assert service.called is True
