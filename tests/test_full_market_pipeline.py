import sqlite3
from types import SimpleNamespace

from PySide6.QtWidgets import QApplication

from database.manager import DatabaseManager
from services.full_market_pipeline import (
    DataCoverageReadinessService,
    FullMarketRefreshOrchestrator,
    FullMarketScanRunner,
    FundamentalDownloaderService,
    HistoricalDataUpdateService,
    InstitutionalDataRefreshService,
    PipelineResult,
    UniverseDownloaderService,
)
from services.results_export_service import ResultsExportService
from ui.widgets.screening_results_panel import ScreeningResultsPanel


def build_manager():
    manager = DatabaseManager.__new__(DatabaseManager)
    manager.connection = sqlite3.connect(":memory:")
    manager.connection.row_factory = sqlite3.Row
    manager.cursor = manager.connection.cursor()
    manager.initialize()
    return manager


class FakeProvider:
    def __init__(self):
        self.universe_calls = []

    def fetch_universe_symbols(self, exchange=None):
        self.universe_calls.append(exchange)
        return [
            {"ticker": "aapl", "company_name": "Apple Inc.", "exchange": exchange, "security_type": "Common Stock", "market_cap": 1_000_000},
            {"ticker": "SPY", "company_name": "SPDR ETF", "exchange": exchange, "security_type": "ETF"},
            {"ticker": "ABCW", "company_name": "ABC Warrant", "exchange": exchange, "security_type": "Warrant"},
            {"ticker": "OLD", "company_name": "Inactive", "exchange": exchange, "security_type": "Common Stock", "active": 0},
        ]

    def fetch_fundamentals(self, ticker):
        return {
            "ticker": ticker,
            "revenue_growth_ttm": 0.12,
            "eps_growth_ttm": 0.2,
            "roe": 0.3,
            "gross_margin": 0.4,
            "free_cash_flow": 1000,
            "debt_to_equity": 0.5,
            "current_ratio": 1.6,
            "bankruptcy_risk": 0.1,
            "going_concern_warning": 0,
            "last_earnings_date": "2026-01-01",
        }

    def fetch_institutional_data(self, ticker):
        return {
            "institutional_ownership_pct": 70,
            "institutional_ownership_change_qoq": 2,
            "net_institutional_buying": 1_000_000,
            "insider_buying_flag": 1,
            "insider_selling_flag": 0,
        }


class FakeProviderFactory:
    def __init__(self, provider=None, success=True):
        self.provider = provider or FakeProvider()
        self.success = success

    def create(self):
        if not self.success:
            return SimpleNamespace(success=False, provider=None, provider_name="fake", warnings=["missing config"], errors=["provider unavailable"])
        return SimpleNamespace(success=True, provider=self.provider, provider_name="fake", warnings=[], errors=[])


class FakeRefreshService:
    def __init__(self):
        self.calls = []

    def refresh_ticker(self, ticker, start_date=None, end_date=None, force_refresh=False):
        self.calls.append((ticker, start_date, end_date, force_refresh))
        return SimpleNamespace(
            ticker=ticker,
            success=True,
            rows=[{"date": "2026-01-02", "open": 1, "high": 2, "low": 1, "close": 2, "volume": 10}],
            refreshed=True,
            warnings=[],
            errors=[],
        )


def test_universe_symbols_repository_methods():
    manager = build_manager()

    inserted = manager.upsert_universe_symbols([
        {"ticker": "aapl", "company_name": "Apple", "exchange": "nasdaq", "security_type": "Common Stock", "market_cap": 10},
        {"ticker": "XOM", "exchange": "NYSE", "security_type": "Common Stock", "market_cap": 20},
    ])
    rows = manager.fetch_universe_symbols(exchange="NASDAQ")

    assert inserted == 2
    assert rows[0]["ticker"] == "AAPL"
    assert manager.fetch_eligible_universe_tickers() == ["AAPL", "XOM"]
    assert manager.deactivate_stale_universe_symbols(["AAPL"]) == 1
    assert manager.fetch_eligible_universe_tickers() == ["AAPL"]
    manager.close()


def test_universe_downloader_filters_and_persists_common_stocks():
    manager = build_manager()
    provider = FakeProvider()
    service = UniverseDownloaderService(
        repository=manager,
        provider_factory=FakeProviderFactory(provider),
    )

    result = service.update_universe(exchanges=("NASDAQ",))

    assert result.success is True
    assert result.processed == 4
    assert result.persisted == 1
    assert manager.fetch_eligible_universe_tickers() == ["AAPL"]
    manager.close()


def test_historical_data_update_incremental_and_continue():
    manager = build_manager()
    manager.upsert_ohlcv("AAPL", [{"date": "2026-01-01", "open": 1, "high": 2, "low": 1, "close": 2, "volume": 10}], "unit")
    refresh = FakeRefreshService()

    result = HistoricalDataUpdateService(repository=manager, refresh_service=refresh).update_history(["AAPL", "MSFT"])

    assert result.processed == 2
    assert ("AAPL", "2026-01-02", None, False) in refresh.calls
    assert any(call[0] == "MSFT" for call in refresh.calls)
    manager.close()


def test_fundamental_downloader_persists_v7_fields():
    manager = build_manager()
    result = FundamentalDownloaderService(
        repository=manager,
        provider_factory=FakeProviderFactory(),
    ).update_fundamentals(["AAPL"])
    record = manager.fetch_fundamental_data("AAPL")

    assert result.persisted == 1
    assert record["revenue_growth_ttm"] == 0.12
    assert record["bankruptcy_risk"] == 0.1
    assert record["last_earnings_date"] == "2026-01-01"
    manager.close()


def test_institutional_refresh_integration_persists_existing_repository():
    manager = build_manager()
    result = InstitutionalDataRefreshService(
        repository=manager,
        provider_factory=FakeProviderFactory(),
    ).update_institutional_data(["AAPL"])
    record = manager.get_institutional_data("AAPL")

    assert result.persisted == 1
    assert record.institutional_ownership_pct == 70
    manager.close()


def test_full_market_refresh_orchestrator_coordinates_services():
    manager = build_manager()
    manager.upsert_universe_symbols([
        {"ticker": "AAPL", "exchange": "NASDAQ", "security_type": "Common Stock"}
    ])
    orchestrator = FullMarketRefreshOrchestrator(
        repository=manager,
        universe_service=SimpleNamespace(update_universe=lambda: PipelineResult(persisted=1)),
        historical_service=SimpleNamespace(update_history=lambda tickers, **kwargs: PipelineResult(processed=len(tickers), persisted=2)),
        fundamental_service=SimpleNamespace(update_fundamentals=lambda tickers, **kwargs: PipelineResult(processed=len(tickers), persisted=1)),
        institutional_service=SimpleNamespace(update_institutional_data=lambda tickers, **kwargs: PipelineResult(processed=len(tickers), persisted=1, warnings=["limited institutional data"])),
    )

    result = orchestrator.refresh_all()

    assert result.success is True
    assert result.processed == 1
    assert result.persisted == 5
    assert "limited institutional data" in result.warnings
    manager.close()


def test_full_market_scan_runner_uses_eligible_cached_tickers():
    manager = build_manager()
    manager.upsert_universe_symbols([
        {"ticker": "AAPL", "exchange": "NASDAQ", "security_type": "Common Stock"},
        {"ticker": "MSFT", "exchange": "NASDAQ", "security_type": "Common Stock"},
    ])
    manager.upsert_ohlcv("AAPL", [{"date": "2026-01-01", "open": 1, "high": 2, "low": 1, "close": 2, "volume": 10}], "unit")

    class FakeScreening:
        def run(self, tickers, **kwargs):
            assert tickers == ["AAPL"]
            return SimpleNamespace(tickers_processed=1, ranked_candidates=[object()], warnings=[], errors=[], run_id="run")

    result = FullMarketScanRunner(repository=manager, screening_orchestrator=FakeScreening()).run_scan()

    assert result.success is True
    assert result.persisted == 1
    assert result.details["run_id"] == "run"
    manager.close()


def test_data_coverage_readiness_report():
    manager = build_manager()
    manager.upsert_universe_symbols([
        {"ticker": "AAPL", "exchange": "NASDAQ", "security_type": "Common Stock"},
        {"ticker": "MSFT", "exchange": "NASDAQ", "security_type": "Common Stock"},
    ])
    manager.upsert_ohlcv("AAPL", [{"date": "2026-01-01", "open": 1, "high": 2, "low": 1, "close": 2, "volume": 10}], "unit")
    manager.upsert_fundamental_data([{"ticker": "AAPL", "revenue_growth_ttm": 0.1}])
    report = DataCoverageReadinessService(repository=manager, stale_days=99999).report()

    assert report["ticker_count"] == 2
    assert report["ohlcv_covered_count"] == 1
    assert report["missing_ohlcv"] == ["MSFT"]
    assert "MSFT" in report["missing_fundamentals"]
    assert report["scan_ready_count"] == 1
    manager.close()


def test_full_market_export_enhancements(tmp_path):
    service = ResultsExportService()
    universe = service.export_universe_list_csv([
        {"ticker": "AAPL", "exchange": "NASDAQ", "security_type": "Common Stock"}
    ], tmp_path, "universe")
    report = {"missing_ohlcv": ["MSFT"], "missing_fundamentals": [], "missing_institutional": [], "stale_data": []}
    report_json = service.export_coverage_readiness_report_json(report, tmp_path, "coverage")
    report_csv = service.export_coverage_readiness_report_csv(report, tmp_path, "coverage")
    package = service.export_full_run_package({}, [], tmp_path, "package", coverage_metadata=report)

    assert universe["count"] == 1
    assert report_json["success"] is True
    assert report_csv["count"] == 1
    assert package["success"] is True
    assert "coverage_metadata" in (tmp_path / "package.json").read_text(encoding="utf-8")


def test_full_market_panel_construction_and_behavior():
    app = QApplication.instance() or QApplication([])
    panel = ScreeningResultsPanel()

    assert panel.update_full_market_universe_button.text() == "Update Universe"
    assert panel.refresh_full_market_data_button.text() == "Refresh Market Data"
    assert panel.run_full_market_scan_button.text() == "Run Full Market Scan"

    panel.set_full_market_active(True, "Running")
    assert panel.cancel_full_market_button.isEnabled() is True
    assert panel.update_full_market_universe_button.isEnabled() is False

    panel.set_full_market_coverage_report({"ticker_count": 2, "scan_ready_count": 1, "ohlcv_covered_count": 1, "warnings": ["Missing data"]})
    assert "1/2" in panel.full_market_coverage_label.text()
    assert "Missing data" in panel.full_market_issues_label.text()
    assert app is not None
