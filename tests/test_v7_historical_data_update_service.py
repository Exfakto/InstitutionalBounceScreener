from types import SimpleNamespace

from services.full_market_pipeline import HistoricalDataUpdateService
from tests.full_market_test_utils import build_manager


class RefreshService:
    def __init__(self, fail=None):
        self.fail = fail or set()
        self.calls = []

    def refresh_ticker(self, ticker, start_date=None, end_date=None, force_refresh=False):
        self.calls.append((ticker, start_date, end_date, force_refresh))
        if ticker in self.fail:
            raise RuntimeError("refresh failed")
        return SimpleNamespace(
            refreshed=True,
            rows=[{"date": "2026-01-02", "open": 1, "high": 2, "low": 1, "close": 2, "volume": 10}],
            warnings=[],
            errors=[],
        )


def test_historical_update_uses_incremental_start_and_dedupes_tickers():
    manager = build_manager()
    manager.upsert_ohlcv("AAPL", [{"date": "2026-01-01", "open": 1, "high": 2, "low": 1, "close": 2, "volume": 10}], "unit")
    refresh = RefreshService()

    result = HistoricalDataUpdateService(manager, refresh).update_history(["aapl", "AAPL", "MSFT"])

    assert result.processed == 2
    assert refresh.calls[0] == ("AAPL", "2026-01-02", None, False)
    assert refresh.calls[1][0] == "MSFT"


def test_historical_update_continues_after_per_ticker_failure_and_cancels():
    manager = build_manager()
    refresh = RefreshService(fail={"FAIL"})
    progress = []
    result = HistoricalDataUpdateService(manager, refresh).update_history(
        ["AAPL", "FAIL", "MSFT"],
        progress_callback=progress.append,
    )

    assert result.success is False
    assert "FAIL: refresh failed" in result.errors
    assert refresh.calls[-1][0] == "MSFT"
    assert progress

    cancelled = HistoricalDataUpdateService(manager, refresh).update_history(
        ["AAPL"],
        cancellation_callback=lambda: True,
    )
    assert "Historical update cancelled" in cancelled.warnings
