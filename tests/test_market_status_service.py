from datetime import datetime
from zoneinfo import ZoneInfo

from services.market_status_service import MarketStatusService


NY = ZoneInfo("America/New_York")
BERLIN = ZoneInfo("Europe/Berlin")


def dt(year, month, day, hour, minute=0, tzinfo=NY):
    return datetime(year, month, day, hour, minute, tzinfo=tzinfo)


def test_regular_open_hours():
    service = MarketStatusService()

    result = service.get_status(dt(2026, 7, 1, 10))

    assert result.market == "U.S. Equities"
    assert result.status == "Open"
    assert result.is_open is True
    assert result.is_premarket is False
    assert result.is_afterhours is False
    assert result.next_close == dt(2026, 7, 1, 16)
    assert result.message == "U.S. equities market is open."


def test_pre_market():
    service = MarketStatusService()

    result = service.get_status(dt(2026, 7, 1, 8))

    assert result.status == "Pre-market"
    assert result.is_premarket is True
    assert result.is_open is False
    assert result.next_open == dt(2026, 7, 1, 9, 30)
    assert result.next_close == dt(2026, 7, 1, 16)


def test_after_hours():
    service = MarketStatusService()

    result = service.get_status(dt(2026, 7, 1, 17))

    assert result.status == "After-hours"
    assert result.is_afterhours is True
    assert result.is_open is False
    assert result.next_open == dt(2026, 7, 2, 9, 30)
    assert result.next_close == dt(2026, 7, 2, 16)


def test_overnight_closed():
    service = MarketStatusService()

    result = service.get_status(dt(2026, 7, 1, 22))

    assert result.status == "Closed"
    assert result.is_open is False
    assert result.next_open == dt(2026, 7, 2, 9, 30)
    assert result.next_close == dt(2026, 7, 2, 16)


def test_weekend():
    service = MarketStatusService()

    result = service.get_status(dt(2026, 7, 5, 12))

    assert result.status == "Weekend"
    assert result.is_weekend is True
    assert result.is_holiday is False
    assert result.next_open == dt(2026, 7, 6, 9, 30)


def test_holiday():
    service = MarketStatusService()

    result = service.get_status(dt(2026, 7, 3, 10))

    assert result.status == "Holiday"
    assert result.is_holiday is True
    assert result.is_weekend is False
    assert result.next_open == dt(2026, 7, 6, 9, 30)


def test_thanksgiving_holiday():
    service = MarketStatusService()

    result = service.get_status(dt(2026, 11, 26, 10))

    assert result.status == "Holiday"
    assert result.is_holiday is True
    assert result.next_open == dt(2026, 11, 27, 9, 30)


def test_next_open_before_regular_session():
    service = MarketStatusService()

    result = service.get_status(dt(2026, 7, 1, 3, 30))

    assert result.status == "Closed"
    assert result.next_open == dt(2026, 7, 1, 9, 30)


def test_next_close_during_open_session():
    service = MarketStatusService()

    result = service.get_status(dt(2026, 7, 1, 15, 59))

    assert result.status == "Open"
    assert result.next_close == dt(2026, 7, 1, 16)


def test_timezone_aware_datetime_converted_to_new_york():
    service = MarketStatusService()

    result = service.get_status(dt(2026, 7, 1, 16, tzinfo=BERLIN))

    assert result.status == "Open"
    assert result.next_close == dt(2026, 7, 1, 16)


def test_naive_datetime_treated_as_new_york_time():
    service = MarketStatusService()

    result = service.get_status(datetime(2026, 7, 1, 10))

    assert result.status == "Open"
    assert result.next_close == dt(2026, 7, 1, 16)


def test_christmas_holiday():
    service = MarketStatusService()

    result = service.get_status(dt(2026, 12, 25, 10))

    assert result.status == "Holiday"
    assert result.next_open == dt(2026, 12, 28, 9, 30)
