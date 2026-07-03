from types import SimpleNamespace

from services.support_zone_engine import (
    SupportTouch,
    SupportZone,
    SupportZoneEngine,
    SupportZoneResult,
)


def support_rows(touch_indices=None, touch_lows=None, count=80, base_low=100.0):
    touch_indices = touch_indices or [10, 25, 40, 60]
    touch_lows = touch_lows or [100.0, 101.0, 99.5, 100.5]
    low_by_index = dict(zip(touch_indices, touch_lows))
    rows = []
    for index in range(count):
        if index in low_by_index:
            low = low_by_index[index]
            close = low + 4
        else:
            low = base_low + 18 + index * 0.25
            close = low + 2
        rows.append(
            {
                "date": f"2026-01-{index + 1:02d}",
                "open": close + 0.5,
                "high": close + 2,
                "low": low,
                "close": close,
                "volume": 1_000_000 + index * 1000,
            }
        )
    return rows


def test_support_zone_engine_detects_repeated_support():
    result = SupportZoneEngine().detect_support_zones("ABC", support_rows())

    assert isinstance(result, SupportZoneResult)
    assert result.ticker == "ABC"
    assert result.warnings == []
    assert len(result.zones) == 1
    zone = result.primary_zone
    assert isinstance(zone, SupportZone)
    assert zone.ticker == "ABC"
    assert zone.touch_count == 4
    assert zone.zone_low == 99.5
    assert zone.zone_high == 101.0
    assert 99.5 <= zone.zone_center <= 101.0
    assert zone.zone_width_pct <= 7.0
    assert zone.first_touch_date == "2026-01-11"
    assert zone.last_touch_date == "2026-01-61"
    assert zone.average_touch_volume is not None
    assert zone.support_strength_score > 70
    assert zone.confidence_score > 50
    assert all(isinstance(touch, SupportTouch) for touch in zone.touches)
    assert all(touch.held_support for touch in zone.touches)


def test_support_zone_engine_handles_insufficient_history():
    result = SupportZoneEngine().detect_support_zones("SHORT", support_rows(count=10))

    assert result.zones == []
    assert result.primary_zone is None
    assert "Insufficient price history" in result.warnings


def test_support_zone_engine_returns_no_support_found():
    rows = []
    for index in range(40):
        low = 50 + index
        rows.append(
            {
                "date": f"2026-02-{index + 1:02d}",
                "high": low + 3,
                "low": low,
                "close": low + 2,
                "volume": 1000,
            }
        )

    result = SupportZoneEngine().detect_support_zones("NONE", rows)

    assert result.zones == []
    assert result.primary_zone is None
    assert "No support zones found" in result.warnings


def test_support_zone_engine_groups_nearby_lows():
    rows = support_rows(
        touch_indices=[8, 20, 35, 50],
        touch_lows=[98.8, 100.0, 101.2, 99.5],
    )

    zone = SupportZoneEngine(max_zone_width_pct=4).get_primary_support_zone("GRP", rows)

    assert zone is not None
    assert zone.touch_count == 4
    assert zone.zone_width_pct <= 4


def test_support_zone_engine_rejects_zones_wider_than_max_width():
    rows = support_rows(
        touch_indices=[8, 20, 35, 50],
        touch_lows=[90.0, 100.0, 110.0, 120.0],
    )

    result = SupportZoneEngine(max_zone_width_pct=3).detect_support_zones("WIDE", rows)

    assert result.zones == []
    assert "No support zones found" in result.warnings


def test_support_zone_engine_enforces_touch_separation():
    rows = support_rows(
        touch_indices=[10, 12, 14, 16, 40],
        touch_lows=[100.0, 100.1, 100.2, 100.0, 100.3],
    )

    result = SupportZoneEngine(min_touch_separation_days=10).detect_support_zones(
        "SEP",
        rows,
    )

    assert result.zones == []
    assert "No support zones found" in result.warnings


def test_support_zone_engine_support_strength_ranking():
    rows = support_rows(
        touch_indices=[8, 20, 32, 44, 60, 70],
        touch_lows=[100, 100.2, 100.1, 100.3, 111, 111.2],
        count=90,
    )
    rows[75]["low"] = 111.1
    rows[75]["close"] = 113

    result = SupportZoneEngine(min_touches=3).detect_support_zones("RANK", rows)

    assert len(result.zones) >= 1
    assert result.zones == SupportZoneEngine.rank_support_zones(result.zones)
    assert result.primary_zone.support_strength_score >= result.zones[-1].support_strength_score


def test_support_zone_engine_ignores_one_day_outlier():
    rows = support_rows()
    rows[30]["low"] = 60.0
    rows[30]["close"] = 61.0

    result = SupportZoneEngine(outlier_threshold_pct=20).detect_support_zones("OUT", rows)

    assert result.primary_zone is not None
    assert all(touch.low_price > 90 for touch in result.primary_zone.touches)


def test_support_zone_engine_accepts_object_rows():
    rows = [
        SimpleNamespace(**row)
        for row in support_rows(touch_indices=[10, 25, 40], touch_lows=[50, 50.4, 49.8])
    ]

    result = SupportZoneEngine(min_touches=3).detect_support_zones("OBJ", rows)

    assert result.primary_zone is not None
    assert result.primary_zone.touch_count == 3
