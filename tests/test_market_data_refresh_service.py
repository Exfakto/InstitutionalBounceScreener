from types import SimpleNamespace

from services.market_data_refresh_service import MarketDataRefreshService


class FakeRepository:
    def __init__(self, cached=None):
        self.cached = cached or {}
        self.upserts = []

    def fetch_ohlcv(self, ticker, start_date=None, end_date=None):
        return list(self.cached.get(ticker, []))

    def upsert_ohlcv(self, ticker, rows, source):
        self.upserts.append((ticker, list(rows), source))
        self.cached[ticker] = [
            row.__dict__ if hasattr(row, "__dict__") else row
            for row in rows
        ]


class FakeProvider:
    SOURCE = "fake"

    def __init__(self, rows=None):
        self.rows = rows or [
            {
                "date": "2026-01-02",
                "open": 10,
                "high": 11,
                "low": 9,
                "close": 10.5,
                "volume": 1000,
            }
        ]
        self.calls = []
        self.last_warnings = []
        self.last_errors = []

    def fetch_daily_ohlcv(self, ticker, start_date=None, end_date=None):
        self.calls.append((ticker, start_date, end_date))
        return list(self.rows)


class FakeProviderFactory:
    def __init__(self, provider=None, success=True):
        self.provider = provider or FakeProvider()
        self.success = success
        self.calls = 0

    def create(self):
        self.calls += 1
        if not self.success:
            return SimpleNamespace(
                success=False,
                provider=None,
                provider_name=None,
                warnings=["Missing provider credentials"],
                errors=["Provider unavailable"],
            )
        return SimpleNamespace(
            success=True,
            provider=self.provider,
            provider_name="fake",
            warnings=[],
            errors=[],
        )


def test_market_data_refresh_single_ticker_from_provider():
    repository = FakeRepository()
    provider = FakeProvider()
    service = MarketDataRefreshService(
        repository=repository,
        provider_factory=FakeProviderFactory(provider),
    )

    result = service.refresh_ticker(" aaa ")

    assert result.success is True
    assert result.ticker == "AAA"
    assert result.cache_hit is False
    assert result.refreshed is True
    assert result.rows[0]["ticker"] == "AAA"
    assert provider.calls == [("AAA", None, None)]
    assert repository.upserts[0][0] == "AAA"


def test_market_data_refresh_cache_first_skips_provider():
    repository = FakeRepository(
        cached={
            "AAA": [
                {
                    "ticker": "AAA",
                    "date": "2026-01-01",
                    "open": 10,
                    "high": 11,
                    "low": 9,
                    "close": 10,
                    "volume": 1000,
                }
            ]
        }
    )
    factory = FakeProviderFactory()
    service = MarketDataRefreshService(repository=repository, provider_factory=factory)

    result = service.refresh_ticker("AAA")

    assert result.success is True
    assert result.cache_hit is True
    assert result.refreshed is False
    assert factory.calls == 0
    assert repository.upserts == []


def test_market_data_refresh_force_refresh_uses_provider():
    repository = FakeRepository(
        cached={
            "AAA": [
                {
                    "ticker": "AAA",
                    "date": "2026-01-01",
                    "open": 1,
                    "high": 1,
                    "low": 1,
                    "close": 1,
                    "volume": 100,
                }
            ]
        }
    )
    provider = FakeProvider()
    service = MarketDataRefreshService(
        repository=repository,
        provider_factory=FakeProviderFactory(provider),
    )

    result = service.refresh_ticker("AAA", force_refresh=True)

    assert result.cache_hit is False
    assert result.refreshed is True
    assert provider.calls == [("AAA", None, None)]
    assert repository.upserts


def test_market_data_refresh_multiple_tickers_reports_progress():
    provider = FakeProvider()
    progress = []
    service = MarketDataRefreshService(
        repository=FakeRepository(),
        provider_factory=FakeProviderFactory(provider),
    )

    result = service.refresh_tickers(
        ["aaa", "AAA", "bbb"],
        progress_callback=progress.append,
    )

    assert list(result.results) == ["AAA", "BBB"]
    assert provider.calls[0][0] == "AAA"
    assert provider.calls[1][0] == "BBB"
    assert progress[0]["processed_tickers"] == 0
    assert progress[-1]["processed_tickers"] == 2


def test_market_data_refresh_provider_error_returns_safe_result():
    service = MarketDataRefreshService(
        repository=FakeRepository(),
        provider_factory=FakeProviderFactory(success=False),
    )

    result = service.refresh_ticker("AAA")

    assert result.success is False
    assert result.rows == []
    assert "Missing provider credentials" in result.warnings
    assert "Provider unavailable" in result.errors
