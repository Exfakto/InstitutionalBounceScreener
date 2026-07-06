import sqlite3
from types import SimpleNamespace

from PySide6.QtWidgets import QApplication

from database.manager import DatabaseManager
from services.data_quality_service import DataQualityService
from services.market_data_cache_service import MarketDataCacheService
from services.market_data_refresh_service import MarketDataRefreshService
from services.provider_diagnostics_service import ProviderDiagnosticsService
from services.results_export_service import ResultsExportService
from ui.widgets.screening_results_panel import ScreeningResultsPanel


def build_manager():
    manager = DatabaseManager.__new__(DatabaseManager)
    manager.connection = sqlite3.connect(":memory:")
    manager.connection.row_factory = sqlite3.Row
    manager.cursor = manager.connection.cursor()
    manager.initialize()
    return manager


def test_cache_coverage_and_clear_behavior():
    manager = build_manager()
    manager.upsert_ohlcv(
        "aaa",
        [
            {"date": "2026-01-01", "open": 10, "high": 11, "low": 9, "close": 10, "volume": 1000},
            {"date": "2026-01-02", "open": 10, "high": 12, "low": 10, "close": 11, "volume": 1200},
        ],
        source="unit",
    )
    service = MarketDataCacheService(repository=manager, stale_days=1)

    coverage = service.coverage(today="2026-01-05")

    assert coverage[0].ticker == "AAA"
    assert coverage[0].row_count == 2
    assert coverage[0].age_days == 3
    assert coverage[0].stale is True
    assert service.clear_ticker("AAA") == 2
    assert service.coverage() == []
    manager.upsert_ohlcv(
        "bbb",
        [{"date": "2026-01-01", "open": 1, "high": 2, "low": 1, "close": 2, "volume": 10}],
        source="unit",
    )
    assert service.clear_all() == 1
    manager.close()


def test_data_quality_report_generation_detects_warnings():
    manager = build_manager()
    manager.upsert_ohlcv(
        "AAA",
        [
            {"date": "2026-01-01", "open": 10, "high": 11, "low": 9, "close": 10, "volume": 1000},
            {"date": "2026-01-05", "open": -1, "high": 12, "low": 10, "close": 11, "volume": -5},
        ],
        source="unit",
    )
    service = DataQualityService(repository=manager, stale_days=1, minimum_history_rows=3)

    report = service.generate_report(["aaa"], today="2026-01-10")
    ticker_report = report.ticker_reports["AAA"]

    assert ticker_report.row_count == 2
    assert ticker_report.missing_dates
    assert ticker_report.invalid_ohlcv_values
    assert ticker_report.insufficient_history is True
    assert any("Stale OHLCV data" in warning for warning in ticker_report.warnings)
    manager.close()


def test_provider_diagnostics_reports_credentials_and_connectivity(monkeypatch):
    class FakeSettings:
        def get_all_settings(self):
            return {
                "selected_market_data_provider": "polygon",
                "polygon_api_key": "",
                "request_timeout_seconds": 10,
                "max_retries": 2,
                "rate_limit_sleep_seconds": 1,
            }

    monkeypatch.delenv("POLYGON_API_KEY", raising=False)

    result = ProviderDiagnosticsService(settings_service=FakeSettings()).run(
        connectivity_test=False
    )

    assert result.selected_provider == "polygon"
    assert result.credential_status == "Polygon API key missing"
    assert "Polygon API key missing" in result.warnings


def test_provider_diagnostics_accepts_environment_credentials(monkeypatch):
    class FakeSettings:
        def get_all_settings(self):
            return {
                "selected_market_data_provider": "polygon",
                "polygon_api_key": "",
                "request_timeout_seconds": 10,
                "max_retries": 2,
                "rate_limit_sleep_seconds": 1,
            }

    monkeypatch.setenv("POLYGON_API_KEY", "env-key")

    result = ProviderDiagnosticsService(settings_service=FakeSettings()).run(
        connectivity_test=False
    )

    assert result.selected_provider == "polygon"
    assert result.credential_status == "Configured"
    assert result.warnings == []


def test_provider_diagnostics_uses_testable_provider_factory():
    class FakeProvider:
        def get_last_updated(self):
            return "2026-01-01"

    class FakeFactory:
        def create(self):
            return SimpleNamespace(success=True, provider=FakeProvider(), errors=[])

    result = ProviderDiagnosticsService(
        settings_service=None,
        provider_factory=FakeFactory(),
    ).run(connectivity_test=True)

    assert result.connectivity_status == "PASS"


def test_results_export_includes_provider_metadata_and_reports(tmp_path):
    service = ResultsExportService()
    package = service.export_full_run_package(
        {"run_id": "run-1"},
        [],
        tmp_path,
        "package",
        provider_metadata={"provider": "local_csv", "source": "cache"},
    )
    coverage = service.export_cache_coverage_report(
        [{"ticker": "AAA", "row_count": 2}],
        tmp_path,
        "coverage",
    )
    quality = service.export_data_quality_report(
        DataQualityService().generate_report(["AAA"]),
        tmp_path,
        "quality",
    )

    assert package["success"] is True
    assert coverage["count"] == 1
    assert quality["success"] is True
    assert '"provider": "local_csv"' in (tmp_path / "package.json").read_text()


def test_market_data_refresh_can_cancel_between_tickers():
    class FakeProviderFactory:
        def create(self):
            provider = SimpleNamespace(
                SOURCE="unit",
                last_warnings=[],
                last_errors=[],
                fetch_daily_ohlcv=lambda ticker, start, end: [
                    {
                        "date": "2026-01-01",
                        "open": 1,
                        "high": 2,
                        "low": 1,
                        "close": 2,
                        "volume": 10,
                    }
                ],
            )
            return SimpleNamespace(
                success=True,
                provider=provider,
                provider_name="unit",
                warnings=[],
                errors=[],
            )

    service = MarketDataRefreshService(
        repository=build_manager(),
        provider_factory=FakeProviderFactory(),
    )
    calls = {"count": 0}

    def cancel_after_first():
        calls["count"] += 1
        return calls["count"] > 1

    result = service.refresh_tickers(
        ["AAA", "BBB"],
        cancellation_callback=cancel_after_first,
    )

    assert list(result.results) == ["AAA"]
    assert "Market data refresh cancelled" in result.warnings


def test_market_data_refresh_persists_to_historical_ohlcv_cache():
    class FakeProviderFactory:
        def create(self):
            provider = SimpleNamespace(
                SOURCE="unit",
                last_warnings=[],
                last_errors=[],
                fetch_daily_ohlcv=lambda ticker, start, end: [
                    {
                        "date": "2026-01-02",
                        "open": 100,
                        "high": 105,
                        "low": 99,
                        "close": 104,
                        "volume": 1000000,
                    }
                ],
            )
            return SimpleNamespace(
                success=True,
                provider=provider,
                provider_name="unit",
                warnings=[],
                errors=[],
            )

    manager = build_manager()
    service = MarketDataRefreshService(
        repository=manager,
        provider_factory=FakeProviderFactory(),
    )

    result = service.refresh_ticker("AAPL", force_refresh=True)
    rows = manager.fetch_ohlcv("AAPL")

    assert result.success is True
    assert result.refreshed is True
    assert rows
    assert rows[0]["ticker"] == "AAPL"
    assert rows[0]["source"] == "unit"
    manager.close()


def test_screening_results_panel_market_data_controls_construct():
    app = QApplication.instance() or QApplication([])
    panel = ScreeningResultsPanel()

    assert panel.refresh_selected_ticker_button.text() == "Refresh Ticker"
    assert panel.refresh_ticker_list_button.text() == "Refresh List"
    assert panel.force_refresh_checkbox.text() == "Force"
    assert panel.cancel_data_refresh_button.isEnabled() is False

    panel.set_data_refresh_active(True, "Refreshing")

    assert panel.cancel_data_refresh_button.isEnabled() is True
    assert panel.market_data_status_label.text() == "Refreshing"
    assert app is not None


def test_screening_results_panel_ohlcv_coverage_summary_shows_cached_ratio():
    app = QApplication.instance() or QApplication([])
    panel = ScreeningResultsPanel()

    panel.set_cache_coverage_summary(
        [
            {"ticker": "AAPL", "row_count": 10},
            {"ticker": "MSFT", "row_count": 12},
        ],
        total_tickers=4,
    )

    assert panel.cache_coverage_label.text() == "OHLCV Coverage: 2 / 4 cached (50.0%)"
    assert app is not None
