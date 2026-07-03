from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ScanPreset:
    name: str
    description: str
    min_market_cap: float | None = None
    min_price: float | None = None
    min_avg_volume: float | None = None
    min_avg_dollar_volume: float | None = None
    exchanges: list[str] = field(default_factory=list)
    security_types: list[str] = field(default_factory=list)


DEFAULT_SCAN_PRESETS = [
    ScanPreset(
        name="Institutional Quality",
        description="Common stocks with meaningful liquidity and institutional-scale size.",
        min_market_cap=2_000_000_000,
        min_price=10,
        min_avg_volume=500_000,
        min_avg_dollar_volume=10_000_000,
        exchanges=["NYSE", "NASDAQ"],
        security_types=["Common Stock"],
    ),
    ScanPreset(
        name="Liquid Large Cap",
        description="Large, highly liquid stocks suitable for repeatable screening.",
        min_market_cap=10_000_000_000,
        min_price=20,
        min_avg_volume=1_000_000,
        min_avg_dollar_volume=50_000_000,
        exchanges=["NYSE", "NASDAQ"],
        security_types=["Common Stock"],
    ),
    ScanPreset(
        name="Growth Bounce Watchlist",
        description="Liquid mid and large cap stocks broad enough for growth-style setups.",
        min_market_cap=1_000_000_000,
        min_price=5,
        min_avg_volume=300_000,
        min_avg_dollar_volume=5_000_000,
        exchanges=["NYSE", "NASDAQ"],
        security_types=["Common Stock"],
    ),
    ScanPreset(
        name="Conservative Quality",
        description="Higher-priced, larger-cap common stocks with stronger liquidity filters.",
        min_market_cap=5_000_000_000,
        min_price=15,
        min_avg_volume=750_000,
        min_avg_dollar_volume=25_000_000,
        exchanges=["NYSE", "NASDAQ"],
        security_types=["Common Stock"],
    ),
]


class ScanPresetService:
    def __init__(self, presets=None):
        self.presets = list(presets or DEFAULT_SCAN_PRESETS)

    def list_presets(self):
        return list(self.presets)

    def get_preset(self, name):
        for preset in self.presets:
            if preset.name == name:
                return preset
        return None

    def apply_preset(self, name):
        return self.get_preset(name)
