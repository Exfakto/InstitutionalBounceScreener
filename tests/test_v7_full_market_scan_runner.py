from types import SimpleNamespace

from services.full_market_pipeline import FullMarketScanRunner
from tests.full_market_test_utils import build_manager


class FakeScreening:
    def __init__(self):
        self.calls = []

    def run(self, tickers, **kwargs):
        self.calls.append(tickers)
        return SimpleNamespace(
            tickers_processed=len(tickers),
            ranked_candidates=[{"ticker": tickers[0], "rank": 1}],
            warnings=["scan warning"],
            errors=[],
            run_id="scan-run",
        )


def test_full_market_scan_runner_uses_only_eligible_tickers_with_ohlcv():
    manager = build_manager()
    manager.upsert_universe_symbols(
        [
            {"ticker": "AAPL", "exchange": "NASDAQ", "security_type": "Common Stock"},
            {"ticker": "MSFT", "exchange": "NASDAQ", "security_type": "Common Stock"},
        ]
    )
    manager.upsert_ohlcv("AAPL", [{"date": "2026-01-01", "open": 1, "high": 2, "low": 1, "close": 2, "volume": 10}], "unit")
    fake = FakeScreening()

    result = FullMarketScanRunner(repository=manager, screening_orchestrator=fake).run_scan()

    assert fake.calls == [["AAPL"]]
    assert result.success is True
    assert result.processed == 1
    assert result.details["run_id"] == "scan-run"


def test_full_market_scan_runner_empty_cache_is_safe():
    manager = build_manager()
    manager.upsert_universe_symbols(
        [{"ticker": "AAPL", "exchange": "NASDAQ", "security_type": "Common Stock"}]
    )

    result = FullMarketScanRunner(repository=manager, screening_orchestrator=FakeScreening()).run_scan()

    assert result.success is False
    assert result.warnings == ["No eligible tickers with OHLCV coverage"]
