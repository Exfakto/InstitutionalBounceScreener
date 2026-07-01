from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class MarketStatusResult:
    market: str
    status: str
    is_open: bool
    is_premarket: bool
    is_afterhours: bool
    is_weekend: bool
    is_holiday: bool
    next_open: datetime | None
    next_close: datetime | None
    message: str


class MarketStatusService:
    """
    Determines the current U.S. equities market session.
    """

    MARKET = "U.S. Equities"
    TIMEZONE = ZoneInfo("America/New_York")
    PREMARKET_OPEN = time(4, 0)
    REGULAR_OPEN = time(9, 30)
    REGULAR_CLOSE = time(16, 0)
    AFTERHOURS_CLOSE = time(20, 0)

    def get_status(self, now=None):
        current = self.normalize_datetime(now)
        current_date = current.date()
        is_weekend = self.is_weekend(current_date)
        is_holiday = self.is_market_holiday(current_date)
        current_time = current.time()

        if is_weekend:
            status = "Weekend"
        elif is_holiday:
            status = "Holiday"
        elif self.PREMARKET_OPEN <= current_time < self.REGULAR_OPEN:
            status = "Pre-market"
        elif self.REGULAR_OPEN <= current_time < self.REGULAR_CLOSE:
            status = "Open"
        elif self.REGULAR_CLOSE <= current_time < self.AFTERHOURS_CLOSE:
            status = "After-hours"
        else:
            status = "Closed"

        next_open = self.next_open_after(current)
        next_close = (
            self.session_datetime(current_date, self.REGULAR_CLOSE)
            if status == "Open"
            else self.next_close_after(current)
        )

        return MarketStatusResult(
            market=self.MARKET,
            status=status,
            is_open=status == "Open",
            is_premarket=status == "Pre-market",
            is_afterhours=status == "After-hours",
            is_weekend=is_weekend,
            is_holiday=is_holiday,
            next_open=next_open,
            next_close=next_close,
            message=self.message_for(status),
        )

    def next_open_after(self, current):
        current_date = current.date()

        if self.is_trading_day(current_date) and current.time() < self.REGULAR_OPEN:
            return self.session_datetime(current_date, self.REGULAR_OPEN)

        next_date = current_date + timedelta(days=1)

        while not self.is_trading_day(next_date):
            next_date += timedelta(days=1)

        return self.session_datetime(next_date, self.REGULAR_OPEN)

    def next_close_after(self, current):
        current_date = current.date()

        if self.is_trading_day(current_date) and current.time() < self.REGULAR_CLOSE:
            return self.session_datetime(current_date, self.REGULAR_CLOSE)

        next_open = self.next_open_after(current)
        return self.session_datetime(next_open.date(), self.REGULAR_CLOSE)

    def is_trading_day(self, value):
        return not self.is_weekend(value) and not self.is_market_holiday(value)

    @staticmethod
    def is_weekend(value):
        return value.weekday() >= 5

    def is_market_holiday(self, value):
        holidays = self.market_holidays(value.year)
        return value in holidays

    @classmethod
    def market_holidays(cls, year):
        return {
            cls.observed_fixed_holiday(year, 1, 1),
            cls.observed_fixed_holiday(year, 7, 4),
            cls.observed_fixed_holiday(year, 12, 25),
            cls.thanksgiving_day(year),
        }

    @staticmethod
    def observed_fixed_holiday(year, month, day):
        holiday = date(year, month, day)

        if holiday.weekday() == 5:
            return holiday - timedelta(days=1)

        if holiday.weekday() == 6:
            return holiday + timedelta(days=1)

        return holiday

    @staticmethod
    def thanksgiving_day(year):
        current = date(year, 11, 1)
        thursdays = 0

        while True:
            if current.weekday() == 3:
                thursdays += 1

                if thursdays == 4:
                    return current

            current += timedelta(days=1)

    def normalize_datetime(self, value):
        if value is None:
            return datetime.now(self.TIMEZONE)

        if value.tzinfo is None:
            return value.replace(tzinfo=self.TIMEZONE)

        return value.astimezone(self.TIMEZONE)

    def session_datetime(self, value, session_time):
        return datetime.combine(value, session_time, tzinfo=self.TIMEZONE)

    @staticmethod
    def message_for(status):
        messages = {
            "Open": "U.S. equities market is open.",
            "Pre-market": "U.S. equities market is in pre-market.",
            "After-hours": "U.S. equities market is in after-hours.",
            "Closed": "U.S. equities market is closed.",
            "Weekend": "U.S. equities market is closed for the weekend.",
            "Holiday": "U.S. equities market is closed for a market holiday.",
        }
        return messages.get(status, "U.S. equities market status is unavailable.")
