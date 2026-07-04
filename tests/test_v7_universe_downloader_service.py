from services.full_market_pipeline import UniverseDownloaderService
from providers.provider_result import ProviderResult
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


class ProviderResultUniverseProvider:
    def __init__(self, rows_by_exchange):
        self.rows_by_exchange = rows_by_exchange

    def fetch_universe_symbols(self, exchange=None):
        rows = self.rows_by_exchange.get(exchange, [])
        if isinstance(rows, ProviderResult):
            return rows
        return ProviderResult.ok(
            data=rows,
            source="mock",
            warnings=[f"{exchange} partial warning"] if exchange == "NYSE" else [],
        )


def common_record(ticker, exchange="NASDAQ", security_type="Common Stock"):
    return {
        "ticker": ticker,
        "company_name": f"{ticker} Corp",
        "exchange": exchange,
        "security_type": security_type,
        "active": True,
    }


def test_universe_downloader_persists_thousands_style_records_and_deactivates_stale():
    manager = build_manager()
    manager.upsert_universe_symbols([common_record("STALE")])
    rows = [common_record(f"T{i:04d}") for i in range(1200)]
    rows.append(common_record("T0001"))
    provider = ProviderResultUniverseProvider({"NASDAQ": rows})

    result = UniverseDownloaderService(
        repository=manager,
        provider_factory=FakeProviderFactory(provider),
    ).update_universe(exchanges=("NASDAQ",))

    assert result.success is True
    assert result.processed == 1201
    assert result.details["eligible_count"] == 1200
    assert len(manager.fetch_eligible_universe_tickers()) == 1200
    stale = manager.fetch_universe_symbols(active_only=False, exchange="NASDAQ")
    assert next(row for row in stale if row["ticker"] == "STALE")["active"] == 0


def test_universe_downloader_filters_non_common_security_types():
    manager = build_manager()
    excluded = [
        "ETF",
        "ADR",
        "SPAC",
        "Preferred Stock",
        "Warrant",
        "Right",
        "Unit",
        "Fund",
        "Trust",
        "Note",
    ]
    rows = [common_record("GOOD")]
    rows.extend(common_record(f"BAD{index}", security_type=value) for index, value in enumerate(excluded))
    provider = ProviderResultUniverseProvider({"NASDAQ": rows})

    result = UniverseDownloaderService(
        repository=manager,
        provider_factory=FakeProviderFactory(provider),
    ).update_universe(exchanges=("NASDAQ",))

    assert result.success is True
    assert manager.fetch_eligible_universe_tickers() == ["GOOD"]


def test_universe_downloader_handles_partial_provider_result_failure():
    manager = build_manager()
    provider = ProviderResultUniverseProvider(
        {
            "NASDAQ": [common_record("AAPL")],
            "NYSE": ProviderResult.fail(
                "planned failure",
                source="mock",
                warnings=["rate limited"],
            ),
        }
    )

    result = UniverseDownloaderService(
        repository=manager,
        provider_factory=FakeProviderFactory(provider),
    ).update_universe(exchanges=("NASDAQ", "NYSE"))

    assert result.success is False
    assert result.persisted == 1
    assert result.warnings == ["NYSE: rate limited"]
    assert result.errors == ["NYSE: planned failure"]
    assert manager.fetch_eligible_universe_tickers() == ["AAPL"]
