from pathlib import Path
from types import SimpleNamespace

from PySide6.QtWidgets import QApplication

from services.app_config_service import AppConfig, AppConfigService
from services.beta_validation_service import BetaValidationService, VALIDATION_BASKET
from ui.about_dialog import AboutDialog


class FakeProviderDiagnostics:
    def __init__(self, provider="local_csv", credential_status="Configured"):
        self.provider = provider
        self.credential_status = credential_status

    def run(self):
        return SimpleNamespace(
            selected_provider=self.provider,
            credential_status=self.credential_status,
            warnings=[],
            errors=[],
        )


class FakeReleaseDiagnostics:
    def __init__(self, warnings=None, errors=None):
        self.warnings = warnings or []
        self.errors = errors or []

    def run(self):
        return SimpleNamespace(
            status="PASS" if not self.errors else "FAIL",
            warnings=self.warnings,
            errors=self.errors,
        )


class FakeRefreshService:
    def __init__(self):
        self.tickers = None
        self.force_refresh = None

    def refresh_tickers(self, tickers, force_refresh=False, progress_callback=None):
        self.tickers = list(tickers)
        self.force_refresh = force_refresh
        if progress_callback:
            progress_callback({"processed_tickers": len(self.tickers), "total_tickers": len(self.tickers)})
        return SimpleNamespace(warnings=[], errors=[])


class FakeCacheService:
    def __init__(self, covered=None):
        self.covered = set(covered or [])

    def coverage(self):
        return [
            SimpleNamespace(
                ticker=ticker,
                row_count=252,
                first_date="2025-01-01",
                last_date="2026-01-01",
                stale=False,
            )
            for ticker in sorted(self.covered)
        ]


class FakeQualityService:
    def generate_report(self, tickers):
        return SimpleNamespace(warnings=[])


def config_service(tmp_path):
    return AppConfigService(
        AppConfig(
            database_path=tmp_path / "data" / "app.db",
            export_directory=tmp_path / "exports",
            log_directory=tmp_path / "logs",
            data_directory=tmp_path / "data",
            config_directory=tmp_path / "config",
        )
    )


def service(tmp_path, **overrides):
    return BetaValidationService(
        app_config_service=config_service(tmp_path),
        provider_diagnostics_service=overrides.get(
            "provider_diagnostics_service",
            FakeProviderDiagnostics(),
        ),
        release_diagnostics_service=overrides.get(
            "release_diagnostics_service",
            FakeReleaseDiagnostics(),
        ),
        market_data_refresh_service=overrides.get(
            "market_data_refresh_service",
            FakeRefreshService(),
        ),
        cache_service=overrides.get("cache_service", FakeCacheService(VALIDATION_BASKET)),
        data_quality_service=overrides.get("data_quality_service", FakeQualityService()),
        screening_runner=overrides.get("screening_runner", lambda tickers: [object(), object()]),
        backtest_runner=overrides.get("backtest_runner", lambda: [object()]),
    )


def test_beta_validation_service_construction(tmp_path):
    validator = service(tmp_path)

    assert validator.validation_basket == VALIDATION_BASKET


def test_beta_validation_basket_behavior(tmp_path):
    refresh = FakeRefreshService()
    validator = service(tmp_path, market_data_refresh_service=refresh)

    report = validator.run(force_refresh=True)

    assert refresh.tickers == list(VALIDATION_BASKET)
    assert refresh.force_refresh is True
    assert report.scan_result_count == 2
    assert report.backtest_result_count == 1
    assert report.provider == "local_csv"


def test_beta_validation_missing_provider_config_warning(tmp_path):
    validator = service(
        tmp_path,
        provider_diagnostics_service=FakeProviderDiagnostics(
            provider="polygon",
            credential_status="Polygon API key missing",
        ),
    )

    report = validator.run()

    assert "Polygon API key missing" in report.warnings
    assert any(issue.area == "provider" for issue in report.issues)


def test_beta_validation_missing_ohlcv_coverage_warnings(tmp_path):
    validator = service(tmp_path, cache_service=FakeCacheService(covered={"AAPL"}))

    report = validator.run()

    assert report.ticker_coverage["AAPL"]["row_count"] == 252
    assert report.ticker_coverage["MSFT"]["row_count"] == 0
    assert any(issue.ticker == "MSFT" for issue in report.issues)


def test_beta_validation_report_export(tmp_path):
    validator = service(tmp_path)
    report = validator.run()

    export = validator.export_report(report, output_dir=tmp_path, basename="beta")

    assert export["success"] is True
    assert Path(export["json_path"]).exists()
    assert Path(export["csv_path"]).exists()
    assert "app_version" in Path(export["json_path"]).read_text(encoding="utf-8")
    assert "severity" in Path(export["csv_path"]).read_text(encoding="utf-8")


class FakeDiagnosticsController:
    def get_diagnostics(self):
        return {
            "app_name": "Institutional Bounce Screener",
            "version": "4.0.0",
            "build_date": "2026-07-03",
            "schema_version": "1",
        }

    def diagnostics_text(self):
        return "diagnostics"

    def startup_report(self):
        return None

    def health_report(self):
        return None


class FakeBetaValidation:
    def run(self):
        return SimpleNamespace(summary="PASS: beta validation complete", issues=[])

    def export_report(self, report):
        return {"json_path": "exports/results/beta_validation_report.json"}


def test_about_dialog_beta_validation_ui_hook(tmp_path):
    app = QApplication.instance() or QApplication([])
    dialog = AboutDialog(controller=FakeDiagnosticsController())
    dialog.beta_validation_service = FakeBetaValidation()

    report = dialog.run_beta_validation()

    assert report.summary == "PASS: beta validation complete"
    assert dialog.run_beta_validation_button.text() == "Run Beta Validation"
    assert dialog.release_labels["beta_validation"].text() == report.summary
    assert "beta_validation_report.json" in dialog.release_labels["beta_report"].text()
    assert app is not None
