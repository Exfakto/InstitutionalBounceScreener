from types import SimpleNamespace
from datetime import date

from services.market_data_refresh_service import MarketDataRefreshService


class FakeRepository:
    def __init__(self, cached=None):
        self.cached = cached or {}
        self.upserts = []

    def fetch_ohlcv(self, ticker, start_date=None, end_date=None):
        rows = list(self.cached.get(ticker, []))
        if start_date is not None:
            rows = [row for row in rows if str(row.get("date")) >= str(start_date)]
        if end_date is not None:
            rows = [row for row in rows if str(row.get("date")) <= str(end_date)]
        return rows

    def fetch_ohlcv_cache_coverage(self, ticker=None):
        tickers = [ticker] if ticker else list(self.cached)
        rows = []
        for value in tickers:
            cached_rows = list(self.cached.get(value, []))
            if not cached_rows:
                continue
            dates = sorted(str(row.get("date")) for row in cached_rows if row.get("date"))
            rows.append(
                {
                    "ticker": value,
                    "row_count": len(cached_rows),
                    "first_date": dates[0],
                    "last_date": dates[-1],
                }
            )
        return rows

    def upsert_ohlcv(self, ticker, rows, source):
        self.upserts.append((ticker, list(rows), source))
        existing = {
            row.get("date"): row
            for row in self.cached.get(ticker, [])
            if row.get("date")
        }
        for row in (
            row.__dict__ if hasattr(row, "__dict__") else row
            for row in rows
        ):
            existing[row.get("date")] = row
        self.cached[ticker] = [existing[key] for key in sorted(existing)]
        return len(list(rows or []))


class FakeProvider:
    SOURCE = "fake"

    def __init__(self, rows=None):
        self.rows = rows if rows is not None else [
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
    assert provider.calls == [
        ("AAA", service.default_start_date(), date.today().isoformat())
    ]
    assert repository.upserts[0][0] == "AAA"


def test_market_data_refresh_cache_first_skips_provider():
    latest_trading_day = MarketDataRefreshService.latest_trading_day().isoformat()
    repository = FakeRepository(
        cached={
            "AAA": [
                {
                    "ticker": "AAA",
                    "date": latest_trading_day,
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
    assert result.rows == []
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
    assert provider.calls == [
        ("AAA", service.default_start_date(), date.today().isoformat())
    ]
    assert repository.upserts


def test_market_data_refresh_second_refresh_skips_current_cached_ticker():
    today = MarketDataRefreshService.latest_trading_day().isoformat()
    repository = FakeRepository(
        cached={
            "AAA": [
                {
                    "ticker": "AAA",
                    "date": today,
                    "open": 10,
                    "high": 11,
                    "low": 9,
                    "close": 10,
                    "volume": 1000,
                }
            ]
        }
    )
    provider = FakeProvider()
    service = MarketDataRefreshService(
        repository=repository,
        provider_factory=FakeProviderFactory(provider),
    )

    result = service.refresh_ticker("AAA")

    assert result.success is True
    assert result.cache_hit is True
    assert result.refreshed is False
    assert result.rows == []
    assert provider.calls == []


def test_market_data_refresh_cached_ticker_requests_only_missing_days():
    repository = FakeRepository(
        cached={
            "AAA": [
                {
                    "ticker": "AAA",
                    "date": "2026-07-01",
                    "open": 10,
                    "high": 11,
                    "low": 9,
                    "close": 10,
                    "volume": 1000,
                }
            ]
        }
    )
    provider = FakeProvider()
    service = MarketDataRefreshService(
        repository=repository,
        provider_factory=FakeProviderFactory(provider),
    )

    result = service.refresh_ticker("AAA", end_date="2026-07-05")

    assert result.refreshed is True
    assert provider.calls == [("AAA", "2026-07-02", "2026-07-05")]


def test_market_data_refresh_cached_zero_new_rows_is_success():
    repository = FakeRepository(
        cached={
            "AAA": [
                {
                    "ticker": "AAA",
                    "date": "2026-07-02",
                    "open": 10,
                    "high": 11,
                    "low": 9,
                    "close": 10,
                    "volume": 1000,
                }
            ]
        }
    )
    provider = FakeProvider(rows=[])
    service = MarketDataRefreshService(
        repository=repository,
        provider_factory=FakeProviderFactory(provider),
    )

    result = service.refresh_ticker("AAA", end_date="2026-07-05")

    assert result.success is True
    assert result.cache_hit is True
    assert result.refreshed is False
    assert result.rows == []
    assert result.persisted == 0
    assert provider.calls == [("AAA", "2026-07-03", "2026-07-05")]
    assert "No new OHLCV rows available for AAA" in result.warnings
    assert "No OHLCV rows returned for AAA" not in result.warnings
    assert repository.upserts == []


def test_market_data_refresh_uncached_ticker_uses_configured_lookback():
    repository = FakeRepository()
    provider = FakeProvider()
    service = MarketDataRefreshService(
        repository=repository,
        provider_factory=FakeProviderFactory(provider),
        lookback_years=2,
    )

    service.refresh_ticker("AAA", end_date="2026-07-05")

    assert provider.calls == [("AAA", "2024-07-05", "2026-07-05")]
    assert provider.calls[0][1] != "1900-01-01"


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


def test_market_data_refresh_empty_provider_rows_warns_without_persisting():
    provider = FakeProvider(rows=[])
    repository = FakeRepository()
    service = MarketDataRefreshService(
        repository=repository,
        provider_factory=FakeProviderFactory(provider),
    )

    result = service.refresh_ticker("AAA")

    assert result.success is False
    assert result.refreshed is False
    assert result.rows == []
    assert "No OHLCV rows returned for AAA" in result.warnings
    assert repository.upserts == []
