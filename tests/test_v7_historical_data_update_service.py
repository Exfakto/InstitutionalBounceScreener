from types import SimpleNamespace
from datetime import date, timedelta

from services.full_market_pipeline import HistoricalDataUpdateService
from tests.full_market_test_utils import build_manager


def five_year_start(end_date=None):
    end = end_date or date.today()
    try:
        return end.replace(year=end.year - 5).isoformat()
    except ValueError:
        return (end - timedelta(days=365 * 5)).isoformat()


class RefreshService:
    def __init__(self, fail=None, empty=None):
        self.fail = fail or set()
        self.empty = empty or set()
        self.calls = []

    def refresh_ticker(self, ticker, start_date=None, end_date=None, force_refresh=False):
        self.calls.append((ticker, start_date, end_date, force_refresh))
        if ticker in self.fail:
            raise RuntimeError("refresh failed")
        if ticker in self.empty:
            return SimpleNamespace(
                refreshed=False,
                cache_hit=False,
                rows=[],
                persisted=0,
                warnings=[f"No OHLCV rows returned for {ticker}"],
                errors=[],
            )
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
    assert ("AAPL", "2026-01-02", None, False) in refresh.calls
    assert ("MSFT", five_year_start(), None, True) in refresh.calls
    assert result.details["coverage_before"] == 1
    assert result.details["uncached_tickers"] == ["MSFT"]
    assert result.details["stale_tickers"] == ["AAPL"]
    assert result.details["refreshed_tickers"] == 2


def test_historical_update_skips_current_cached_ticker_and_refreshes_missing():
    manager = build_manager()
    today = date.today().isoformat()
    manager.upsert_ohlcv(
        "AAPL",
        [{"date": today, "open": 1, "high": 2, "low": 1, "close": 2, "volume": 10}],
        "unit",
    )
    refresh = RefreshService()

    result = HistoricalDataUpdateService(manager, refresh).update_history(["AAPL", "MSFT"])

    assert refresh.calls == [("MSFT", five_year_start(), None, True)]
    assert result.details["cache_hit_tickers"] == 1
    assert result.details["refreshed_tickers"] == 1


def test_historical_update_skips_latest_trading_day_cached_ticker():
    manager = build_manager()
    latest_trading_day = HistoricalDataUpdateService.latest_trading_day().isoformat()
    manager.upsert_ohlcv(
        "AAPL",
        [{"date": latest_trading_day, "open": 1, "high": 2, "low": 1, "close": 2, "volume": 10}],
        "unit",
    )
    refresh = RefreshService()

    result = HistoricalDataUpdateService(manager, refresh).update_history(["AAPL"])

    assert refresh.calls == []
    assert result.details["skipped_current_tickers"] == 1


def test_historical_update_uses_configured_lookback_for_uncached_ticker():
    manager = build_manager()
    refresh = RefreshService()

    HistoricalDataUpdateService(manager, refresh, lookback_years=3).update_history(
        ["AAPL"],
        end_date="2026-07-05",
    )

    assert refresh.calls == [("AAPL", "2023-07-05", "2026-07-05", True)]


def test_historical_update_does_not_replace_explicit_early_start_date():
    manager = build_manager()
    refresh = RefreshService()

    HistoricalDataUpdateService(manager, refresh).update_history(
        ["AAPL"],
        start_date="1900-01-01",
        end_date="2026-07-05",
    )

    assert refresh.calls == [("AAPL", "1900-01-01", "2026-07-05", True)]


def test_historical_update_refreshes_stale_cached_ticker_incrementally():
    manager = build_manager()
    stale = HistoricalDataUpdateService.latest_trading_day() - timedelta(days=2)
    stale_date = stale.isoformat()
    expected_start = (stale + timedelta(days=1)).isoformat()
    manager.upsert_ohlcv(
        "AAPL",
        [{"date": stale_date, "open": 1, "high": 2, "low": 1, "close": 2, "volume": 10}],
        "unit",
    )
    refresh = RefreshService()

    HistoricalDataUpdateService(manager, refresh).update_history(["AAPL"])

    assert refresh.calls == [("AAPL", expected_start, None, False)]


def test_historical_update_resumes_from_remaining_tickers():
    manager = build_manager()
    refresh = RefreshService()
    service = HistoricalDataUpdateService(manager, refresh, lookback_years=2)
    service.save_sync_metadata(
        ["AAPL", "MSFT", "NVDA"],
        ["MSFT", "NVDA"],
        ["AAPL"],
        last_downloaded_ticker="AAPL",
        status="cancelled",
    )

    result = service.update_history(
        ["AAPL", "MSFT", "NVDA"],
        end_date="2026-07-05",
    )
    metadata = service.load_sync_metadata()

    assert [call[0] for call in refresh.calls] == ["MSFT", "NVDA"]
    assert result.details["download_tickers"] == ["MSFT", "NVDA"]
    assert metadata["status"] == "complete"
    assert metadata["last_downloaded_ticker"] == "NVDA"
    assert metadata["remaining_tickers"] == []
    assert metadata["completed_tickers"] == ["AAPL", "MSFT", "NVDA"]


def test_historical_update_progress_includes_download_position_and_eta():
    manager = build_manager()
    refresh = RefreshService()
    progress = []

    HistoricalDataUpdateService(manager, refresh).update_history(
        ["AAPL", "MSFT"],
        progress_callback=progress.append,
    )

    assert progress
    assert progress[0]["stage"] == "ohlcv"
    assert progress[0]["current_ticker"] == "AAPL"
    assert progress[0]["universe_total"] == 2
    assert "Downloading 1 of 2" in progress[0]["status_message"]
    assert "Ticker: AAPL" in progress[0]["status_message"]
    assert "estimated_remaining_seconds" in progress[0]


def test_historical_update_force_refresh_clears_only_requested_ticker():
    manager = build_manager()
    manager.upsert_ohlcv(
        "AAPL",
        [{"date": "2026-01-01", "open": 1, "high": 2, "low": 1, "close": 2, "volume": 10}],
        "unit",
    )
    manager.upsert_ohlcv(
        "MSFT",
        [{"date": "2026-01-01", "open": 1, "high": 2, "low": 1, "close": 2, "volume": 10}],
        "unit",
    )
    refresh = RefreshService()

    HistoricalDataUpdateService(manager, refresh, lookback_years=2).update_history(
        ["AAPL"],
        end_date="2026-07-05",
        force_refresh=True,
    )

    assert refresh.calls == [("AAPL", "2024-07-05", "2026-07-05", True)]
    assert manager.fetch_ohlcv("AAPL") == []
    assert manager.fetch_ohlcv("MSFT")


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


def test_historical_update_records_no_data_and_skips_on_next_incremental_run():
    manager = build_manager()
    refresh = RefreshService(empty={"DEAD"})

    first = HistoricalDataUpdateService(manager, refresh).update_history(["DEAD"])
    metadata = manager.get_ohlcv_sync_metadata("DEAD")

    assert first.details["no_data_tickers"] == 1
    assert metadata["status"] == "no_data"
    assert metadata["empty_response_count"] == 1

    second_refresh = RefreshService()
    second = HistoricalDataUpdateService(manager, second_refresh).update_history(["DEAD"])

    assert second_refresh.calls == []
    assert second.details["skipped_no_data_tickers"] == 1
    assert second.details["download_tickers"] == []


def test_historical_update_records_error_and_skips_on_next_incremental_run():
    manager = build_manager()
    refresh = RefreshService(fail={"FAIL"})

    first = HistoricalDataUpdateService(manager, refresh).update_history(["FAIL"])
    metadata = manager.get_ohlcv_sync_metadata("FAIL")

    assert first.success is False
    assert first.details["failed_tickers"] == 1
    assert metadata["status"] == "error"
    assert metadata["last_error"] == "refresh failed"

    second_refresh = RefreshService()
    second = HistoricalDataUpdateService(manager, second_refresh).update_history(["FAIL"])

    assert second_refresh.calls == []
    assert second.details["skipped_error_tickers"] == 1
    assert second.details["download_tickers"] == []


def test_historical_update_force_refresh_retries_no_data_ticker():
    manager = build_manager()
    manager.upsert_ohlcv_sync_metadata(
        "DEAD",
        status="no_data",
        empty_response_count=1,
    )
    refresh = RefreshService()

    result = HistoricalDataUpdateService(manager, refresh).update_history(
        ["DEAD"],
        force_refresh=True,
    )

    assert refresh.calls
    assert result.details["refreshed_tickers"] == 1
