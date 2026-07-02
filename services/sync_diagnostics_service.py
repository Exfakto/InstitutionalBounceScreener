from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd

from database.manager import DatabaseManager


class SyncDiagnosticsService:
    """
    Read-only diagnostics for local SQLite price history freshness.
    """

    STATUSES = {"Current", "Stale", "Incomplete", "Missing", "Error"}

    def __init__(self, database_manager: DatabaseManager | None = None) -> None:
        self.database_manager = database_manager or DatabaseManager()

    def diagnose_ticker(
        self,
        ticker: str | None,
        start: Any = None,
        end: Any = None,
        stale_threshold_days: int = 3,
        today: Any = None,
    ) -> dict[str, Any]:
        normalized_ticker = self.normalize_ticker(ticker)
        expected_start = self.normalize_date(start)
        expected_end = self.normalize_date(end)
        reference_date = self.normalize_date(today) or date.today().isoformat()

        result = self.empty_result(
            normalized_ticker,
            expected_start=expected_start,
            expected_end=expected_end,
        )

        if normalized_ticker is None:
            result["status"] = "Error"
            result["warnings"].append("Ticker is required.")
            return result

        if start is not None and expected_start is None:
            result["status"] = "Error"
            result["warnings"].append("Invalid start date.")
            return result

        if end is not None and expected_end is None:
            result["status"] = "Error"
            result["warnings"].append("Invalid end date.")
            return result

        if expected_start is not None and expected_end is not None:
            if pd.to_datetime(expected_start) > pd.to_datetime(expected_end):
                result["status"] = "Error"
                result["warnings"].append("Start date must be before end date.")
                return result

        try:
            history = self.database_manager.get_price_history(normalized_ticker)
        except Exception as exc:
            result["status"] = "Error"
            result["warnings"].append(f"Price history read failed: {exc}")
            return result

        if history is None or getattr(history, "empty", True):
            result["status"] = "Missing"
            result["warnings"].append("No local price history rows found.")
            return result

        frame = self.filter_frame(history.sort_index(), expected_start, expected_end)

        if frame.empty:
            result["status"] = "Missing"
            result["warnings"].append("No local price history rows found for expected range.")
            return result

        first_date = self.index_date(frame.index.min())
        last_date = self.index_date(frame.index.max())
        result["row_count"] = int(len(frame))
        result["first_date"] = first_date
        result["last_date"] = last_date
        result["stale_days"] = self.business_days_between(last_date, reference_date)

        missing_days = []

        if expected_start is not None and expected_end is not None:
            missing_days = self.missing_business_days(
                frame,
                expected_start,
                expected_end,
            )

        result["missing_days_count"] = len(missing_days)

        if missing_days:
            result["status"] = "Incomplete"
            result["warnings"].append(
                f"Missing {len(missing_days)} expected business day rows."
            )
            return result

        if result["stale_days"] > stale_threshold_days:
            result["status"] = "Stale"
            result["warnings"].append(
                f"Last price row is {result['stale_days']} business days old."
            )
            return result

        result["status"] = "Current"
        return result

    def diagnose_tickers(
        self,
        tickers: list[str] | tuple[str, ...],
        start: Any = None,
        end: Any = None,
        stale_threshold_days: int = 3,
        today: Any = None,
    ) -> dict[str, Any]:
        results = [
            self.diagnose_ticker(
                ticker,
                start=start,
                end=end,
                stale_threshold_days=stale_threshold_days,
                today=today,
            )
            for ticker in (tickers or [])
        ]

        return {
            "ticker": "MULTIPLE",
            "results": results,
            "row_count": sum(item.get("row_count", 0) for item in results),
            "first_date": None,
            "last_date": None,
            "expected_start": self.normalize_date(start),
            "expected_end": self.normalize_date(end),
            "missing_days_count": sum(
                item.get("missing_days_count", 0) for item in results
            ),
            "stale_days": max(
                [item.get("stale_days", 0) for item in results] or [0]
            ),
            "status": self.aggregate_status(results),
            "warnings": [
                warning
                for item in results
                for warning in item.get("warnings", [])
            ],
        }

    @classmethod
    def missing_business_days(
        cls,
        frame: pd.DataFrame,
        start: str | None,
        end: str | None,
    ) -> list[str]:
        if start is None or end is None:
            return []

        expected_days = [
            value
            for value in pd.bdate_range(start=start, end=end)
            if cls.is_expected_trading_day(value)
        ]
        existing_days = {
            cls.index_date(value)
            for value in frame.index
        }

        return [
            value.date().isoformat()
            for value in expected_days
            if value.date().isoformat() not in existing_days
        ]

    @classmethod
    def filter_frame(
        cls,
        frame: pd.DataFrame,
        start: str | None = None,
        end: str | None = None,
    ) -> pd.DataFrame:
        filtered = frame

        if start is not None:
            filtered = filtered[filtered.index >= pd.to_datetime(start)]

        if end is not None:
            filtered = filtered[filtered.index <= pd.to_datetime(end)]

        return filtered

    @classmethod
    def is_expected_trading_day(cls, value: Any) -> bool:
        day = pd.to_datetime(value).date()

        if day.weekday() >= 5:
            return False

        return not cls.is_market_holiday(day)

    @staticmethod
    def is_market_holiday(value: date) -> bool:
        """
        Small placeholder holiday calendar for sync diagnostics.

        This intentionally stays isolated so a fuller exchange calendar can be
        wired later without changing callers.
        """

        year = value.year
        thanksgiving = SyncDiagnosticsService.nth_weekday(year, 11, 3, 4)
        holidays = {
            date(year, 1, 1),
            date(year, 7, 4),
            date(year, 12, 25),
            thanksgiving,
        }
        observed = set()

        for holiday in holidays:
            if holiday.weekday() == 5:
                observed.add(holiday - timedelta(days=1))
            elif holiday.weekday() == 6:
                observed.add(holiday + timedelta(days=1))

        return value in holidays or value in observed

    @staticmethod
    def nth_weekday(year: int, month: int, weekday: int, occurrence: int) -> date:
        days = [
            candidate.date()
            for candidate in pd.date_range(
                start=date(year, month, 1),
                end=date(year, month, 28) + pd.offsets.MonthEnd(0),
            )
            if candidate.weekday() == weekday
        ]

        return days[occurrence - 1]

    @staticmethod
    def business_days_between(start: str | None, end: str | None) -> int:
        if start is None or end is None:
            return 0

        start_date = pd.to_datetime(start)
        end_date = pd.to_datetime(end)

        if pd.isna(start_date) or pd.isna(end_date) or start_date >= end_date:
            return 0

        days = pd.bdate_range(
            start=start_date + pd.Timedelta(days=1),
            end=end_date,
        )

        return int(len(days))

    @staticmethod
    def aggregate_status(results: list[dict[str, Any]]) -> str:
        if not results:
            return "Missing"

        for status in ["Error", "Missing", "Incomplete", "Stale"]:
            if any(item.get("status") == status for item in results):
                return status

        return "Current"

    @staticmethod
    def empty_result(
        ticker: str | None,
        expected_start: str | None = None,
        expected_end: str | None = None,
    ) -> dict[str, Any]:
        return {
            "ticker": ticker,
            "row_count": 0,
            "first_date": None,
            "last_date": None,
            "expected_start": expected_start,
            "expected_end": expected_end,
            "missing_days_count": 0,
            "stale_days": 0,
            "status": "Missing",
            "warnings": [],
        }

    @staticmethod
    def normalize_ticker(ticker: str | None) -> str | None:
        normalized = str(ticker or "").strip().upper()

        return normalized or None

    @staticmethod
    def normalize_date(value: Any) -> str | None:
        if value is None:
            return None

        if isinstance(value, pd.Timestamp):
            return value.date().isoformat()

        if isinstance(value, datetime):
            return value.date().isoformat()

        if isinstance(value, date):
            return value.isoformat()

        if isinstance(value, str):
            try:
                return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
            except ValueError:
                return None

        parsed = pd.to_datetime(value, errors="coerce")

        if pd.isna(parsed):
            return None

        return parsed.date().isoformat()

    @staticmethod
    def index_date(value: Any) -> str | None:
        return SyncDiagnosticsService.normalize_date(value)
