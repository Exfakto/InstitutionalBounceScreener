from services.universe_scan_adapter import UniverseScanAdapter


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
