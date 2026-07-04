from types import SimpleNamespace

from PySide6.QtWidgets import QApplication

from services.app_config_service import AppConfigService
from services.beta_testing_service import BetaReadinessDiagnosticsService
from services.diagnostics_service import DiagnosticsService
from tests.release_test_utils import app_config
from ui.about_dialog import AboutDialog


class ProviderDiagnostics:
    def __init__(self, status="Configured"):
        self.status = status

    def run(self):
        return SimpleNamespace(selected_provider="local_csv", credential_status=self.status)


class Coverage:
    def __init__(self, report):
        self._report = report

    def report(self):
        return self._report


def test_beta_readiness_diagnostics_reports_required_checks(tmp_path):
    report = {
        "ticker_count": 10,
        "ohlcv_covered_count": 8,
        "missing_fundamentals": ["A"],
        "missing_institutional": ["B"],
    }
    diagnostics = BetaReadinessDiagnosticsService(
        provider_diagnostics_service=ProviderDiagnostics(),
        coverage_service=Coverage(report),
        app_config_service=AppConfigService(app_config(tmp_path)),
    ).run()

    names = {item["name"] for item in diagnostics["items"]}
    assert diagnostics["status"] == "PASS"
    assert {
        "provider_configured",
        "universe_available",
        "ohlcv_coverage",
        "fundamentals_coverage",
        "institutional_coverage",
        "export_path_writable",
    }.issubset(names)


def test_beta_readiness_diagnostics_warns_when_provider_or_data_missing(tmp_path):
    diagnostics = BetaReadinessDiagnosticsService(
        provider_diagnostics_service=ProviderDiagnostics("Missing API key"),
        coverage_service=Coverage(
            {
                "ticker_count": 0,
                "ohlcv_covered_count": 0,
                "missing_fundamentals": [],
                "missing_institutional": [],
            }
        ),
        app_config_service=AppConfigService(app_config(tmp_path)),
    ).run()

    assert diagnostics["status"] == "WARNING"
    assert any(item["name"] == "provider_configured" and item["status"] == "WARNING" for item in diagnostics["items"])


class FakeDiagnosticsController:
    def get_diagnostics(self):
        return {
            "app_name": "Institutional Bounce Screener",
            "version": "4.0.0",
            "build_date": "2026-07-03",
            "schema_version": "1",
            "beta_readiness_status": "PASS",
        }

    def diagnostics_text(self):
        return "diagnostics"

    def startup_report(self):
        return None

    def health_report(self):
        return None


def test_about_dialog_displays_beta_readiness_status():
    app = QApplication.instance() or QApplication([])
    dialog = AboutDialog(controller=FakeDiagnosticsController())

    assert dialog.release_labels["beta_readiness"].text() == "PASS"
    assert app is not None


def test_diagnostics_service_includes_beta_readiness_payload(tmp_path):
    class BetaReadiness:
        def run(self):
            return {
                "status": "WARNING",
                "items": [{"name": "provider_configured", "status": "WARNING", "message": "Missing"}],
            }

    service = DiagnosticsService(provider_config_path=tmp_path / "missing.json")
    service.beta_readiness_service = BetaReadiness()

    diagnostics = service.get_diagnostics()

    assert diagnostics["beta_readiness_status"] == "WARNING"
    assert diagnostics["beta_readiness_items"][0]["name"] == "provider_configured"
    assert "Beta Readiness: WARNING" in service.diagnostics_text()
