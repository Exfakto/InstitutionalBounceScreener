from controllers.diagnostics_controller import DiagnosticsController


class FakeDiagnosticsService:
    def __init__(self):
        self.get_called = False
        self.text_called = False

    def get_diagnostics(self):
        self.get_called = True
        return {"app_name": "Institutional Bounce Screener"}

    def diagnostics_text(self):
        self.text_called = True
        return "Application: Institutional Bounce Screener"


class FakeProductionReadinessDashboardService:
    def __init__(self):
        self.called = False

    def build_dashboard(self):
        self.called = True
        return "production readiness"


class FakeReleaseCandidateValidationService:
    def __init__(self):
        self.called = False

    def validate(self):
        self.called = True
        return "release candidate validation"


def test_diagnostics_controller_delegates_diagnostics():
    service = FakeDiagnosticsService()
    controller = DiagnosticsController(diagnostics_service=service)

    assert controller.get_diagnostics() == {
        "app_name": "Institutional Bounce Screener"
    }
    assert service.get_called is True


def test_diagnostics_controller_delegates_text():
    service = FakeDiagnosticsService()
    controller = DiagnosticsController(diagnostics_service=service)

    assert controller.diagnostics_text() == "Application: Institutional Bounce Screener"
    assert service.text_called is True


def test_diagnostics_controller_delegates_production_readiness_dashboard():
    readiness_service = FakeProductionReadinessDashboardService()
    controller = DiagnosticsController(
        diagnostics_service=FakeDiagnosticsService(),
        production_readiness_dashboard_service=readiness_service,
    )

    assert controller.get_production_readiness_dashboard() == "production readiness"
    assert readiness_service.called is True


def test_diagnostics_controller_delegates_release_candidate_validation():
    validation_service = FakeReleaseCandidateValidationService()
    controller = DiagnosticsController(
        diagnostics_service=FakeDiagnosticsService(),
        release_candidate_validation_service=validation_service,
    )

    assert controller.run_release_candidate_validation() == "release candidate validation"
    assert validation_service.called is True
