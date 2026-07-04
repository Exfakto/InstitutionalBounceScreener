from services.full_market_pipeline import DataCoverageReadinessService
from tests.full_market_test_utils import build_manager


def test_data_coverage_readiness_reports_missing_and_ready_counts():
    manager = build_manager()
    manager.upsert_universe_symbols(
        [
            {"ticker": "AAPL", "exchange": "NASDAQ", "security_type": "Common Stock"},
            {"ticker": "MSFT", "exchange": "NASDAQ", "security_type": "Common Stock"},
        ]
    )
    manager.upsert_ohlcv("AAPL", [{"date": "2026-01-01", "open": 1, "high": 2, "low": 1, "close": 2, "volume": 10}], "unit")
    manager.upsert_fundamental_data([{"ticker": "AAPL", "revenue_growth_ttm": 0.1}])
    manager.upsert_institutional_data({"ticker": "AAPL", "institutional_ownership_pct": 60})

    report = DataCoverageReadinessService(repository=manager, stale_days=99999).report()

    assert report["ticker_count"] == 2
    assert report["ohlcv_covered_count"] == 1
    assert report["missing_ohlcv"] == ["MSFT"]
    assert report["missing_fundamentals"] == ["MSFT"]
    assert report["missing_institutional"] == ["MSFT"]
    assert report["scan_ready_count"] == 1
    assert report["scan_ready"] is True
    assert len(report["warnings"]) == 3


def test_data_coverage_readiness_handles_empty_repository():
    report = DataCoverageReadinessService(repository=None).report()

    assert report["ticker_count"] == 0
    assert report["scan_ready"] is False
    assert report["warnings"] == []
