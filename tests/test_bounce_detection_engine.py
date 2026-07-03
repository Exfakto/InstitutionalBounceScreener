from services.bounce_detection_engine import (
    BounceAnalysisResult,
    BounceDetectionEngine,
    BounceEvent,
)
from services.support_zone_engine import SupportTouch, SupportZone


def rows_with_bounces(count=90):
    rows = []
    touch_plan = {
        10: {"low": 100, "close": 103, "peak_index": 16, "peak": 115},
        30: {"low": 101, "close": 104, "peak_index": 35, "peak": 108},
        50: {"low": 99, "close": 102, "peak_index": 58, "peak": 120},
    }
    for index in range(count):
        low = 104 + (index % 3)
        high = low + 3
        close = low + 1
        if index in touch_plan:
            low = touch_plan[index]["low"]
            close = touch_plan[index]["close"]
            high = close + 1
        for plan in touch_plan.values():
            if index == plan["peak_index"]:
                high = plan["peak"]
                close = high - 2
                low = close - 2
        rows.append(
            {
                "date": f"2026-01-{index + 1:02d}",
                "high": high,
                "low": low,
                "close": close,
                "volume": 1_000_000 + index,
            }
        )
    return rows


def support_zone(touch_indices=(10, 30, 50), center=100.0, low=99.0, high=101.0):
    touches = [
        SupportTouch(
            date=f"2026-01-{index + 1:02d}",
            low_price=center,
            close_price=center + 2,
            volume=1_000_000,
            distance_from_zone_center=0.0,
            held_support=True,
        )
        for index in touch_indices
    ]
    return SupportZone(
        ticker="ABC",
        zone_low=low,
        zone_high=high,
        zone_center=center,
        zone_width_pct=((high - low) / center) * 100,
        touch_count=len(touches),
        first_touch_date=touches[0].date if touches else None,
        last_touch_date=touches[-1].date if touches else None,
        support_age_days=80,
        average_touch_volume=1_000_000,
        support_strength_score=80,
        confidence_score=75,
        touches=touches,
    )


def test_bounce_detection_engine_detects_successful_bounces():
    result = BounceDetectionEngine().analyze_zone_bounces(
        "ABC",
        rows_with_bounces(),
        support_zone(),
    )

    assert isinstance(result, BounceAnalysisResult)
    assert result.total_support_tests == 3
    assert result.successful_bounces == 2
    assert result.failed_bounces == 1
    assert result.failed_support_breaks == 0
    assert result.bounce_success_rate == (2 / 3) * 100
    assert result.largest_bounce_pct == 20.0
    assert result.most_recent_bounce_date == "2026-01-51"
    assert all(isinstance(event, BounceEvent) for event in result.events)
    assert result.events[0].successful is True
    assert result.events[1].successful is False


def test_bounce_detection_engine_detects_failed_support_break():
    rows = rows_with_bounces()
    rows[32]["close"] = 95.0

    result = BounceDetectionEngine().analyze_zone_bounces("ABC", rows, support_zone())

    assert result.failed_support_breaks == 1
    assert result.events[1].failed_support_break is True
    assert result.events[1].successful is False


def test_bounce_detection_engine_summary_calculations():
    result = BounceDetectionEngine().analyze_zone_bounces(
        "ABC",
        rows_with_bounces(),
        support_zone(),
    )

    assert round(result.average_bounce_pct, 4) == round((15 + 9 + 20) / 3, 4)
    assert result.median_bounce_pct == 15.0
    assert result.largest_bounce_pct == 20.0
    assert result.average_days_to_peak == (6 + 2 + 8) / 3


def test_bounce_detection_engine_days_to_peak_calculation():
    result = BounceDetectionEngine().analyze_zone_bounces(
        "ABC",
        rows_with_bounces(count=30),
        support_zone(touch_indices=(10,)),
    )

    assert result.events[0].max_future_high == 115
    assert result.events[0].bounce_percentage == 15.0
    assert result.events[0].days_to_peak == 6


def test_bounce_detection_engine_handles_insufficient_future_data():
    result = BounceDetectionEngine(lookahead_window=60).analyze_zone_bounces(
        "ABC",
        rows_with_bounces(count=65),
        support_zone(touch_indices=(60,)),
    )

    assert result.total_support_tests == 1
    assert result.events[0].in_progress is True
    assert "Insufficient future data" in result.warnings


def test_bounce_detection_engine_handles_empty_support_zones():
    results = BounceDetectionEngine().analyze_bounces("ABC", rows_with_bounces(), [])

    assert len(results) == 1
    assert results[0].events == []
    assert results[0].warnings == ["No support zones provided"]


def test_bounce_detection_engine_handles_missing_price_rows():
    rows = rows_with_bounces()
    rows[12].pop("high")

    result = BounceDetectionEngine().analyze_zone_bounces("ABC", rows, support_zone())

    assert any("Skipped row" in warning for warning in result.warnings)
    assert result.total_support_tests == 3


def test_bounce_detection_engine_multiple_zones_and_ranking():
    rows = rows_with_bounces()
    strong = support_zone(touch_indices=(10, 50), center=100, low=99, high=101)
    weak = support_zone(touch_indices=(30,), center=108, low=107, high=109)

    results = BounceDetectionEngine().analyze_bounces("ABC", rows, [weak, strong])
    ranked = BounceDetectionEngine.rank_zones_by_bounce_quality(results)

    assert len(results) == 2
    assert ranked[0].support_zone is strong
    assert ranked[0].bounce_success_rate >= ranked[1].bounce_success_rate


def test_bounce_detection_engine_missing_touch_date_warning():
    result = BounceDetectionEngine().analyze_zone_bounces(
        "ABC",
        rows_with_bounces(),
        support_zone(touch_indices=(150,)),
    )

    assert result.events == []
    assert "Touch date not found: 2026-01-151" in result.warnings
