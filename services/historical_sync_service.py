from __future__ import annotations

import math
import time
from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd

from database.manager import DatabaseManager
from providers.provider_result import ProviderResult
from services.live_data_service import LiveDataService


class HistoricalSyncService:
    """
    Synchronize provider price history into the canonical OHLCV cache.
    """

    REQUIRED_FIELDS = ("date", "Open", "High", "Low", "Close", "Volume")

    def __init__(
        self,
        live_data_service: LiveDataService | None = None,
        database_manager: DatabaseManager | None = None,
    ) -> None:
        self.live_data_service = live_data_service or LiveDataService()
        self.database_manager = database_manager or DatabaseManager()

    def sync_ticker(
        self,
        ticker: str | None,
        start: Any = None,
        end: Any = None,
        force_update: bool = False,
        lookback_days: int | None = None,
    ) -> dict[str, Any]:
        started_at = time.perf_counter()
        normalized_ticker = self.normalize_ticker(ticker)
        summary = self.summary(normalized_ticker)
        start = self.resolve_start_date(start, end=end, lookback_days=lookback_days)

        if normalized_ticker is None:
            summary["failed"] = 1
            summary["warnings"].append("Ticker is required.")
            return self.finish_summary(summary, started_at)

        provider_result = self.live_data_service.fetch_daily_ohlcv(
            normalized_ticker,
            start=start,
            end=end,
        )

        if not provider_result.success:
            summary["failed"] = 1
            summary["provider"] = provider_result.source or None
            summary["warnings"].extend(provider_result.warnings or [])
            summary["warnings"].append(provider_result.message or "Provider failed.")
            return self.finish_summary(summary, started_at)

        summary["provider"] = provider_result.source or None
        rows = self.price_rows(provider_result.data)
        if not rows:
            summary["warnings"].append("Provider returned no price history rows.")
            return self.finish_summary(summary, started_at)

        for row in rows:
            summary["processed"] += 1
            normalized_row = self.normalize_price_row(row)

            if normalized_row is None:
                summary["skipped"] += 1
                summary["warnings"].append("Invalid price history row skipped.")
                continue

            action = self.store_price_row(
                normalized_ticker,
                normalized_row,
                source=summary["provider"],
                force_update=force_update,
            )

            if action == "inserted":
                summary["inserted"] += 1
            elif action == "updated":
                summary["updated"] += 1
            else:
                summary["skipped"] += 1

        self.commit()

        return self.finish_summary(summary, started_at)

    def sync_tickers(
        self,
        tickers: list[str] | tuple[str, ...],
        start: Any = None,
        end: Any = None,
        force_update: bool = False,
        lookback_days: int | None = None,
    ) -> dict[str, Any]:
        started_at = time.perf_counter()
        summaries = [
            self.sync_ticker(
                ticker,
                start=start,
                end=end,
                force_update=force_update,
                lookback_days=lookback_days,
            )
            for ticker in (tickers or [])
        ]
        aggregate = self.summary("MULTIPLE")
        aggregate["tickers"] = summaries
        aggregate["provider"] = self.aggregate_provider(summaries)

        for item in summaries:
            aggregate["processed"] += item.get("processed", 0)
            aggregate["inserted"] += item.get("inserted", 0)
            aggregate["updated"] += item.get("updated", 0)
            aggregate["skipped"] += item.get("skipped", 0)
            aggregate["failed"] += item.get("failed", 0)
            aggregate["warnings"].extend(item.get("warnings", []))

        return self.finish_summary(aggregate, started_at)

    def store_price_row(
        self,
        ticker: str,
        row: dict[str, Any],
        source: str | None = None,
        force_update: bool = False,
    ) -> str:
        existing = self.existing_price_row(ticker, row["date"])

        if existing is None:
            self.store_ohlcv_cache_rows(ticker, [row], source=source)
            return "inserted"

        if not force_update and self.rows_match(existing, row):
            return "skipped"

        self.store_ohlcv_cache_rows(ticker, [row], source=source)
        return "updated"

    def existing_price_row(self, ticker: str, row_date: str) -> dict[str, Any] | None:
        fetch = getattr(self.database_manager, "fetch_ohlcv", None)
        if not callable(fetch):
            return None

        rows = fetch(ticker, start_date=row_date, end_date=row_date) or []
        return dict(rows[0]) if rows else None

    def store_ohlcv_cache_rows(
        self,
        ticker: str,
        rows: list[dict[str, Any]],
        source: str | None = None,
    ) -> int:
        if not rows:
            return 0
        upsert = getattr(self.database_manager, "upsert_ohlcv", None)
        if not callable(upsert):
            return 0
        return upsert(ticker, rows, source=source or "historical_sync")

    def commit(self) -> None:
        commit = getattr(self.database_manager, "commit", None)

        if callable(commit):
            commit()
            return

        connection = getattr(self.database_manager, "connection", None)

        if connection is not None:
            connection.commit()

    @classmethod
    def price_rows(cls, data: Any) -> list[dict[str, Any]]:
        if data is None:
            return []

        if isinstance(data, pd.DataFrame):
            rows = []

            for row_date, row in data.iterrows():
                record = row.to_dict()
                record["date"] = row_date
                rows.append(record)

            return rows

        if isinstance(data, list):
            return [row for row in data if isinstance(row, dict)]

        if isinstance(data, dict):
            if "prices" in data and isinstance(data["prices"], list):
                return [row for row in data["prices"] if isinstance(row, dict)]

            if "date" in data:
                return [data]

        return []

    @classmethod
    def normalize_price_row(cls, row: dict[str, Any]) -> dict[str, Any] | None:
        try:
            row_date = cls.normalize_date(row.get("date"))
            normalized = {
                "date": row_date,
                "open": cls.float_value(row.get("Open", row.get("open"))),
                "high": cls.float_value(row.get("High", row.get("high"))),
                "low": cls.float_value(row.get("Low", row.get("low"))),
                "close": cls.float_value(row.get("Close", row.get("close"))),
                "volume": cls.int_value(row.get("Volume", row.get("volume"))),
            }
        except (TypeError, ValueError, OverflowError):
            return None

        if not row_date:
            return None

        if any(value is None for key, value in normalized.items() if key != "date"):
            return None

        return normalized

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

        parsed = pd.to_datetime(value, errors="coerce")

        if pd.isna(parsed):
            return None

        return parsed.date().isoformat()

    @classmethod
    def resolve_start_date(
        cls,
        start: Any = None,
        end: Any = None,
        lookback_days: int | None = None,
    ) -> Any:
        if start is not None or lookback_days is None:
            return start

        try:
            days = int(lookback_days)
        except (TypeError, ValueError):
            return start

        if days <= 0:
            return start

        end_date_text = cls.normalize_date(end) if end is not None else None
        end_date = (
            datetime.strptime(end_date_text, "%Y-%m-%d").date()
            if end_date_text is not None
            else date.today()
        )

        return (end_date - timedelta(days=days)).isoformat()

    @staticmethod
    def float_value(value: Any) -> float | None:
        if value is None or pd.isna(value):
            return None

        result = float(value)

        if not math.isfinite(result):
            return None

        return result

    @staticmethod
    def int_value(value: Any) -> int | None:
        if value is None or pd.isna(value):
            return None

        result = int(value)

        if result < 0:
            return None

        return result

    @staticmethod
    def rows_match(existing: dict[str, Any], row: dict[str, Any]) -> bool:
        return (
            math.isclose(float(existing["open"]), row["open"])
            and math.isclose(float(existing["high"]), row["high"])
            and math.isclose(float(existing["low"]), row["low"])
            and math.isclose(float(existing["close"]), row["close"])
            and int(existing["volume"]) == row["volume"]
        )

    @staticmethod
    def normalize_ticker(ticker: str | None) -> str | None:
        if ticker is None:
            return None

        normalized = str(ticker).strip().upper()

        return normalized or None

    @staticmethod
    def summary(ticker: str | None) -> dict[str, Any]:
        return {
            "ticker": ticker,
            "provider": None,
            "processed": 0,
            "inserted": 0,
            "updated": 0,
            "skipped": 0,
            "failed": 0,
            "warnings": [],
            "elapsed_seconds": 0.0,
        }

    @staticmethod
    def finish_summary(
        summary: dict[str, Any],
        started_at: float,
    ) -> dict[str, Any]:
        summary["elapsed_seconds"] = round(time.perf_counter() - started_at, 4)

        return summary

    @staticmethod
    def aggregate_provider(summaries: list[dict[str, Any]]) -> str | None:
        providers = [
            item.get("provider")
            for item in summaries
            if item.get("provider")
        ]

        unique = []

        for provider in providers:
            if provider not in unique:
                unique.append(provider)

        if not unique:
            return None

        if len(unique) == 1:
            return unique[0]

        return ", ".join(unique)
