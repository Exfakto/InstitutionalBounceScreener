from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path


@dataclass(frozen=True)
class CacheCoverageRow:
    ticker: str
    row_count: int = 0
    first_date: str | None = None
    last_date: str | None = None
    last_updated: str | None = None
    sources: list[str] = field(default_factory=list)
    age_days: int | None = None
    stale: bool = False


class MarketDataCacheService:
    def __init__(self, repository=None, stale_days=10):
        self.repository = repository
        self.stale_days = stale_days

    def coverage(self, ticker=None, today=None):
        if self.repository is None or not hasattr(self.repository, "fetch_ohlcv_cache_coverage"):
            return []
        rows = self.repository.fetch_ohlcv_cache_coverage(ticker) or []
        return [self.coverage_row(row, today=today) for row in rows]

    def clear_ticker(self, ticker):
        if self.repository is None or not hasattr(self.repository, "clear_ohlcv"):
            return 0
        return self.repository.clear_ohlcv(ticker)

    def clear_all(self):
        if self.repository is None:
            return 0
        if hasattr(self.repository, "clear_all_ohlcv"):
            return self.repository.clear_all_ohlcv()
        coverage = self.coverage()
        return sum(self.clear_ticker(row.ticker) for row in coverage)

    def export_coverage_csv(self, output_dir, filename="cache_coverage.csv", ticker=None):
        destination = self.destination(output_dir, filename, "csv")
        destination.parent.mkdir(parents=True, exist_ok=True)
        rows = self.coverage(ticker=ticker)
        with destination.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "ticker",
                    "row_count",
                    "first_date",
                    "last_date",
                    "last_updated",
                    "sources",
                    "age_days",
                    "stale",
                ],
            )
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {
                        "ticker": row.ticker,
                        "row_count": row.row_count,
                        "first_date": row.first_date,
                        "last_date": row.last_date,
                        "last_updated": row.last_updated,
                        "sources": "; ".join(row.sources),
                        "age_days": row.age_days,
                        "stale": row.stale,
                    }
                )
        return {"success": True, "path": str(destination), "count": len(rows)}

    def coverage_row(self, row, today=None):
        last_date = self.value(row, "last_date")
        age_days = self.age_days(last_date, today=today)
        sources = self.value(row, "sources") or ""
        if isinstance(sources, str):
            source_list = [source for source in sources.split(",") if source]
        else:
            source_list = list(sources or [])
        return CacheCoverageRow(
            ticker=str(self.value(row, "ticker") or "").upper(),
            row_count=int(self.value(row, "row_count") or 0),
            first_date=self.value(row, "first_date"),
            last_date=last_date,
            last_updated=self.value(row, "last_updated"),
            sources=source_list,
            age_days=age_days,
            stale=age_days is not None and age_days > self.stale_days,
        )

    @staticmethod
    def age_days(value, today=None):
        if value in (None, ""):
            return None
        today_date = today or date.today()
        if isinstance(today_date, datetime):
            today_date = today_date.date()
        elif not isinstance(today_date, date):
            try:
                today_date = datetime.fromisoformat(str(today_date)).date()
            except ValueError:
                today_date = date.today()
        if isinstance(value, datetime):
            row_date = value.date()
        elif isinstance(value, date):
            row_date = value
        else:
            try:
                row_date = datetime.fromisoformat(str(value)).date()
            except ValueError:
                return None
        return (today_date - row_date).days

    @staticmethod
    def destination(output_dir, filename, extension):
        directory = Path(str(output_dir or "."))
        path = directory / str(filename or "cache_coverage")
        suffix = f".{extension}"
        return path if path.suffix.lower() == suffix else path.with_suffix(suffix)

    @staticmethod
    def value(source, key):
        if isinstance(source, dict):
            return source.get(key)
        return getattr(source, key, None)
