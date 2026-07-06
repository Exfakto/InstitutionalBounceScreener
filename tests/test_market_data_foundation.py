import sqlite3

import pandas as pd

from database.manager import DatabaseManager
from market_data.local_csv_provider import LocalCsvMarketDataProvider, LocalCsvUniverseProvider
from market_data.validation import MarketDataValidator
from services.market_data_service import MarketDataService


def build_manager():
    manager = DatabaseManager.__new__(DatabaseManager)
    manager.connection = sqlite3.connect(":memory:")
    manager.connection.row_factory = sqlite3.Row
    manager.cursor = manager.connection.cursor()
    manager.initialize()
    return manager


def write_csv(path, text):
    path.write_text(text, encoding="utf-8")
    return path


def test_local_csv_market_data_provider_loads_ohlcv(tmp_path):
    write_csv(
        tmp_path / "AAPL.csv",
        "date,open,high,low,close,volume\n"
        "2026-01-02,100,105,99,104,1000000\n"
        "2026-01-03,104,106,103,105,1100000\n",
    )
    provider = LocalCsvMarketDataProvider(tmp_path)

    rows = provider.fetch_daily_ohlcv("aapl", "2026-01-03", "2026-01-03")

    assert len(rows) == 1
    assert rows[0].ticker == "AAPL"
    assert rows[0].close == 105
    assert provider.last_errors == []


def test_local_csv_market_data_provider_invalid_csv_handling(tmp_path):
    write_csv(
        tmp_path / "BAD.csv",
        "date,open,high,low,close,volume\n"
        "2026-01-02,0,105,99,104,100\n"
        "2026-01-03,104,106,103,105,-1\n",
    )
    provider = LocalCsvMarketDataProvider(tmp_path)

    rows = provider.fetch_daily_ohlcv("BAD")

    assert rows == []
    assert any("Invalid OHLCV prices" in warning for warning in provider.last_warnings)
    assert any("Invalid OHLCV volume" in warning for warning in provider.last_warnings)
    assert LocalCsvMarketDataProvider(tmp_path).fetch_daily_ohlcv("MISSING") == []


def test_ohlcv_cache_insert_fetch_clear():
    manager = build_manager()

    count = manager.upsert_ohlcv(
        "aapl",
        [
            {
                "date": "2026-01-02",
                "open": 100,
                "high": 105,
                "low": 99,
                "close": 104,
                "volume": 1000000,
            }
        ],
        source="unit",
    )
    rows = manager.fetch_ohlcv("AAPL", "2026-01-01", "2026-01-31")

    assert count == 1
    assert rows[0]["ticker"] == "AAPL"
    assert rows[0]["source"] == "unit"
    assert manager.clear_ohlcv("AAPL") == 1
    assert manager.fetch_ohlcv("AAPL") == []
    manager.close()


def test_save_price_history_also_populates_ohlcv_cache():
    manager = build_manager()
    history = pd.DataFrame(
        [
            {
                "Open": 100,
                "High": 105,
                "Low": 99,
                "Close": 104,
                "Volume": 1000000,
            }
        ],
        index=pd.to_datetime(["2026-01-02"]),
    )
    revised_history = pd.DataFrame(
        [
            {
                "Open": 101,
                "High": 106,
                "Low": 100,
                "Close": 105,
                "Volume": 1100000,
            }
        ],
        index=pd.to_datetime(["2026-01-02"]),
    )

    inserted = manager.save_price_history("AAPL", history)
    duplicate_inserted = manager.save_price_history("AAPL", revised_history)
    cache_rows = manager.fetch_ohlcv("AAPL")

    assert inserted == 1
    assert duplicate_inserted == 0
    assert cache_rows[0]["date"] == "2026-01-02"
    assert cache_rows[0]["close"] == 105
    assert cache_rows[0]["volume"] == 1100000
    assert cache_rows[0]["source"] == "legacy_price_history"
    manager.close()


def test_local_csv_universe_provider_loading_and_filters(tmp_path):
    path = write_csv(
        tmp_path / "universe.csv",
        "ticker,company_name,exchange,security_type\n"
        " aapl ,Apple Inc.,NASDAQ,Common Stock\n"
        "IBM,IBM,NYSE,Common Stock\n"
        "SPY,SPDR,NASDAQ,ETF\n",
    )
    provider = LocalCsvUniverseProvider(path)

    symbols = provider.fetch_universe_symbols(exchange="NASDAQ", security_type="Common Stock")

    assert [symbol.ticker for symbol in symbols] == ["AAPL"]
    assert symbols[0].exchange == "NASDAQ"


def test_market_data_service_ticker_and_date_validation(tmp_path):
    provider = LocalCsvMarketDataProvider(tmp_path)
    service = MarketDataService(provider=provider)

    assert service.fetch_daily_ohlcv(" ").errors == ["Ticker is required"]
    result = service.fetch_daily_ohlcv("AAPL", "2026-02-01", "2026-01-01")

    assert result.success is False
    assert "start_date must be before or equal to end_date" in result.errors


def test_market_data_service_fetches_and_caches_csv_rows(tmp_path):
    write_csv(
        tmp_path / "AAPL.csv",
        "date,open,high,low,close,volume\n"
        "2026-01-02,100,105,99,104,1000000\n",
    )
    manager = build_manager()
    service = MarketDataService(
        provider=LocalCsvMarketDataProvider(tmp_path),
        cache_repository=manager,
        stale_days=99999,
    )

    result = service.fetch_daily_ohlcv("aapl", "2026-01-01", "2026-01-31")
    cached = service.fetch_daily_ohlcv("AAPL", "2026-01-01", "2026-01-31")

    assert result.success is True
    assert result.rows[0].source == "local_csv"
    assert cached.success is True
    assert cached.rows[0].close == 104
    manager.close()


def test_market_data_validation_utilities():
    rows = [
        {"date": "2026-01-02", "open": 1, "high": 2, "low": 1, "close": 2, "volume": 10},
        {"date": "2026-01-02", "open": -1, "high": 2, "low": 3, "close": 2, "volume": -1},
    ]

    assert MarketDataValidator.duplicate_dates(rows) == ["2026-01-02"]
    assert "open" in MarketDataValidator.invalid_prices(rows[1])
    assert "high_low_range" in MarketDataValidator.invalid_prices(rows[1])
    assert MarketDataValidator.invalid_volume(rows[1]) is True
    assert MarketDataValidator.stale_data_warnings([], today=MarketDataValidator.parse_date("2026-01-03"))
