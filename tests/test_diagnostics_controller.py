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
