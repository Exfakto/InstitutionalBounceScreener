from tests.full_market_test_utils import build_manager


def test_universe_master_repository_upsert_fetch_filter_and_deactivate():
    manager = build_manager()

    inserted = manager.upsert_universe_symbols(
        [
            {"ticker": "aapl", "company_name": "Apple", "exchange": "nasdaq", "security_type": "Common Stock", "market_cap": 10},
            {"ticker": "XOM", "company_name": "Exxon", "exchange": "NYSE", "security_type": "Common Stock", "market_cap": 20},
            {"ticker": "SPY", "company_name": "ETF", "exchange": "NYSE", "security_type": "ETF", "market_cap": 30},
        ]
    )

    assert inserted == 3
    assert [row["ticker"] for row in manager.fetch_universe_symbols(exchange="NASDAQ")] == ["AAPL"]
    assert [row["ticker"] for row in manager.fetch_universe_symbols(min_market_cap=15)] == ["SPY", "XOM"]
    assert manager.fetch_eligible_universe_tickers() == ["AAPL", "XOM"]
    assert manager.deactivate_stale_universe_symbols(["AAPL"]) == 2
    assert manager.fetch_eligible_universe_tickers() == ["AAPL"]


def test_universe_master_repository_skips_invalid_records():
    manager = build_manager()

    assert manager.upsert_universe_symbols([{"ticker": "", "exchange": "NYSE"}, {"ticker": "AAPL"}]) == 0
    assert manager.fetch_universe_symbols(active_only=False) == []
