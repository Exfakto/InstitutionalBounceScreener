from services.full_market_pipeline import UniverseDownloaderService
from tests.full_market_test_utils import FakeProvider, FakeProviderFactory, build_manager


def test_universe_downloader_filters_common_stocks_and_persists():
    manager = build_manager()
    provider = FakeProvider()

    result = UniverseDownloaderService(
        repository=manager,
        provider_factory=FakeProviderFactory(provider),
    ).update_universe(exchanges=("NASDAQ",))

    assert result.success is True
    assert result.processed == 4
    assert result.persisted == 1
    assert result.details["eligible_count"] == 1
    assert manager.fetch_eligible_universe_tickers() == ["AAPL"]


def test_universe_downloader_handles_provider_failures_and_missing_factory():
    manager = build_manager()
    failure = UniverseDownloaderService(
        repository=manager,
        provider_factory=FakeProviderFactory(FakeProvider(fail_universe_exchange="NASDAQ")),
    ).update_universe(exchanges=("NASDAQ",))
    missing = UniverseDownloaderService(repository=manager, provider_factory=None).update_universe()

    assert failure.success is False
    assert "NASDAQ: universe unavailable" in failure.errors
    assert missing.success is False
    assert missing.errors == ["provider factory unavailable"]


def test_universe_downloader_normalizes_inactive_string_flags():
    record = UniverseDownloaderService.normalize_symbol(
        {"ticker": "old", "exchange": "NYSE", "security_type": "Common Stock", "active": "0"}
    )

    assert record["active"] == 0
    assert UniverseDownloaderService.is_eligible(record) is False
