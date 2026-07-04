from services.full_market_pipeline import FundamentalDownloaderService
from tests.full_market_test_utils import FakeProviderFactory, build_manager


def test_fundamental_repository_upsert_fetch_and_missing_tickers():
    manager = build_manager()

    inserted = manager.upsert_fundamental_data(
        [
            {
                "ticker": "aapl",
                "revenue_growth_ttm": 0.12,
                "bankruptcy_risk": 0.1,
                "going_concern_warning": 0,
                "last_earnings_date": "2026-01-01",
            }
        ]
    )
    record = manager.fetch_fundamental_data("AAPL")

    assert inserted == 1
    assert record["revenue_growth_ttm"] == 0.12
    assert record["bankruptcy_risk"] == 0.1
    assert manager.fetch_missing_fundamental_tickers(["AAPL", "MSFT"]) == ["MSFT"]


def test_fundamental_downloader_persists_and_continues_on_error():
    manager = build_manager()

    result = FundamentalDownloaderService(
        repository=manager,
        provider_factory=FakeProviderFactory(),
    ).update_fundamentals(["AAPL", "FAIL"])

    assert result.success is False
    assert result.persisted == 1
    assert "FAIL: fundamentals unavailable" in result.errors
    assert manager.fetch_fundamental_data("AAPL")["last_earnings_date"] == "2026-01-01"


def test_fundamental_downloader_missing_factory_is_safe():
    result = FundamentalDownloaderService(repository=None, provider_factory=None).update_fundamentals(["AAPL"])

    assert result.success is False
    assert result.errors == ["provider factory unavailable"]
