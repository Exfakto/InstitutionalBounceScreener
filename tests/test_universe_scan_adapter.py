from services.universe_scan_adapter import UniverseScanAdapter
from services.scan_preset_service import ScanPreset


class FakeUniverseSource:
    def __init__(self, records):
        self.records = records

    def get_active_market_universe_records(self):
        return list(self.records)


def test_universe_scan_adapter_loads_tickers_from_universe():
    adapter = UniverseScanAdapter(
        FakeUniverseSource(
            [
                {"ticker": "AAPL"},
                {"ticker": "MSFT"},
            ]
        )
    )

    assert adapter.load_tickers() == ["AAPL", "MSFT"]


def test_universe_scan_adapter_normalizes_and_deduplicates_tickers():
    adapter = UniverseScanAdapter(
        FakeUniverseSource(
            [
                {"ticker": " aapl "},
                {"ticker": "AAPL"},
                {"ticker": ""},
                {"ticker": None},
                {"ticker": "msft"},
            ]
        )
    )

    assert adapter.load_tickers() == ["AAPL", "MSFT"]


def test_universe_scan_adapter_applies_disabled_universe_filter():
    adapter = UniverseScanAdapter(FakeUniverseSource([{"ticker": "AAPL"}]))

    assert adapter.load_tickers({"Universe": {"enabled": False}}) == []


def test_universe_scan_adapter_supports_object_records():
    record = type("Record", (), {"ticker": "nvda"})()
    adapter = UniverseScanAdapter(FakeUniverseSource([record]))

    assert adapter.load_tickers() == ["NVDA"]


def test_universe_scan_adapter_applies_scan_preset_thresholds():
    preset = ScanPreset(
        name="Preset",
        description="Preset",
        min_market_cap=1_000_000_000,
        min_price=10,
        min_avg_volume=500_000,
        min_avg_dollar_volume=10_000_000,
        exchanges=["NASDAQ"],
        security_types=["Common Stock"],
    )
    adapter = UniverseScanAdapter(
        FakeUniverseSource(
            [
                {
                    "ticker": "PASS",
                    "market_cap": 2_000_000_000,
                    "price": 25,
                    "average_volume": 800_000,
                    "average_dollar_volume": 20_000_000,
                    "exchange": "NASDAQ",
                    "security_type": "Common Stock",
                },
                {
                    "ticker": "FAILCAP",
                    "market_cap": 500_000_000,
                    "price": 25,
                    "average_volume": 800_000,
                    "average_dollar_volume": 20_000_000,
                    "exchange": "NASDAQ",
                    "security_type": "Common Stock",
                },
                {
                    "ticker": "FAILTYPE",
                    "market_cap": 2_000_000_000,
                    "price": 25,
                    "average_volume": 800_000,
                    "average_dollar_volume": 20_000_000,
                    "exchange": "NASDAQ",
                    "security_type": "ETF",
                },
            ]
        )
    )

    assert adapter.load_tickers({"scan_preset": preset}) == ["PASS"]
