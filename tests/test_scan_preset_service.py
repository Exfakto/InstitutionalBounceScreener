from services.scan_preset_service import ScanPreset, ScanPresetService


def test_scan_preset_creation():
    preset = ScanPreset(
        name="Test",
        description="Test preset",
        min_market_cap=1_000_000_000,
        min_price=10,
        min_avg_volume=500_000,
        min_avg_dollar_volume=5_000_000,
        exchanges=["NASDAQ"],
        security_types=["Common Stock"],
    )

    assert preset.name == "Test"
    assert preset.min_market_cap == 1_000_000_000
    assert preset.exchanges == ["NASDAQ"]


def test_scan_preset_service_lists_default_presets():
    service = ScanPresetService()

    names = [preset.name for preset in service.list_presets()]

    assert names == [
        "Institutional Quality",
        "Liquid Large Cap",
        "Growth Bounce Watchlist",
        "Conservative Quality",
    ]


def test_scan_preset_service_get_and_apply_preset():
    service = ScanPresetService()

    preset = service.get_preset("Liquid Large Cap")
    applied = service.apply_preset("Liquid Large Cap")

    assert preset is applied
    assert applied.description
    assert applied.min_market_cap == 10_000_000_000
    assert service.get_preset("Missing") is None
