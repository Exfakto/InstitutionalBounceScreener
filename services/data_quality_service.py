from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from market_data.validation import MarketDataValidator


@dataclass(frozen=True)
class DataQualityTickerReport:
    ticker: str
    row_count: int = 0
    missing_dates: list[str] = field(default_factory=list)
    duplicate_dates: list[str] = field(default_factory=list)
    invalid_ohlcv_values: list[str] = field(default_factory=list)
    stale_data: list[str] = field(default_factory=list)
    insufficient_history: bool = False
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DataQualityReport:
    ticker_reports: dict[str, DataQualityTickerReport] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


class DataQualityService:
    def __init__(self, repository=None, stale_days=10, minimum_history_rows=120):
        self.repository = repository
        self.stale_days = stale_days
        self.minimum_history_rows = minimum_history_rows

    def generate_report(self, tickers, today=None):
        reports = {}
        warnings = []
        for ticker in self.unique_tickers(tickers):
            rows = self.fetch_rows(ticker)
            report = self.ticker_report(ticker, rows, today=today)
            reports[ticker] = report
            warnings.extend(f"{ticker}: {warning}" for warning in report.warnings)
        return DataQualityReport(ticker_reports=reports, warnings=self.unique(warnings))

    def ticker_report(self, ticker, rows, today=None):
        rows = list(rows or [])
        duplicate_dates = self.duplicate_dates(rows)
        invalid_values = self.invalid_values(rows)
        stale_data = self.stale_warnings(rows, today=today)
        missing_dates = self.missing_business_dates(rows)
        insufficient_history = len(rows) < self.minimum_history_rows
        warnings = []
        if not rows:
            warnings.append("No OHLCV rows available")
        if duplicate_dates:
            warnings.append("Duplicate OHLCV dates detected")
        if invalid_values:
            warnings.append("Invalid OHLCV values detected")
        if stale_data:
            warnings.extend(stale_data)
        if insufficient_history:
            warnings.append("Insufficient price history")
        if missing_dates:
            warnings.append("Missing trading dates detected")
        return DataQualityTickerReport(
            ticker=str(ticker or "").upper(),
            row_count=len(rows),
            missing_dates=missing_dates,
            duplicate_dates=duplicate_dates,
            invalid_ohlcv_values=invalid_values,
            stale_data=stale_data,
            insufficient_history=insufficient_history,
            warnings=self.unique(warnings),
        )

    def fetch_rows(self, ticker):
        if self.repository is None or not hasattr(self.repository, "fetch_ohlcv"):
            return []
        return self.repository.fetch_ohlcv(ticker) or []

    def export_report_csv(self, report, output_dir, filename="data_quality_report.csv"):
        destination = Path(str(output_dir or ".")) / str(filename or "data_quality_report.csv")
        if destination.suffix.lower() != ".csv":
            destination = destination.with_suffix(".csv")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "ticker",
                    "row_count",
                    "missing_dates",
                    "duplicate_dates",
                    "invalid_ohlcv_values",
                    "stale_data",
                    "insufficient_history",
                    "warnings",
                ],
            )
            writer.writeheader()
            for row in (report.ticker_reports or {}).values():
                writer.writerow(
                    {
                        "ticker": row.ticker,
                        "row_count": row.row_count,
                        "missing_dates": "; ".join(row.missing_dates),
                        "duplicate_dates": "; ".join(row.duplicate_dates),
                        "invalid_ohlcv_values": "; ".join(row.invalid_ohlcv_values),
                        "stale_data": "; ".join(row.stale_data),
                        "insufficient_history": row.insufficient_history,
                        "warnings": "; ".join(row.warnings),
                    }
                )
        return {
            "success": True,
            "path": str(destination),
            "count": len(report.ticker_reports or {}),
        }

    def duplicate_dates(self, rows):
        seen = set()
        duplicates = []
        for row in rows:
            row_date = str(self.value(row, "date") or "")
            if row_date in seen and row_date not in duplicates:
                duplicates.append(row_date)
            seen.add(row_date)
        return duplicates

    def invalid_values(self, rows):
        invalid = []
        for row in rows:
            date_text = str(self.value(row, "date") or "unknown")
            row_warnings = []
            row_warnings.extend(MarketDataValidator.invalid_prices(row))
            if MarketDataValidator.invalid_volume(row):
                row_warnings.append("volume")
            if row_warnings:
                invalid.append(f"{date_text}: {', '.join(row_warnings)}")
        return invalid

    def stale_warnings(self, rows, today=None):
        if not rows:
            return []
        latest = max((str(self.value(row, "date") or "") for row in rows), default="")
        age = self.age_days(latest, today=today)
        if age is not None and age > self.stale_days:
            return [f"Stale OHLCV data: latest row is {age} days old"]
        return []

    def missing_business_dates(self, rows):
        dates = sorted(
            self.parse_date(self.value(row, "date"))
            for row in rows
            if self.parse_date(self.value(row, "date")) is not None
        )
        if len(dates) < 2:
            return []
        known = {item.isoformat() for item in dates}
        missing = []
        current = dates[0]
        while current < dates[-1]:
            current = date.fromordinal(current.toordinal() + 1)
            if current.weekday() < 5 and current.isoformat() not in known:
                missing.append(current.isoformat())
        return missing

    @staticmethod
    def parse_date(value):
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        try:
            return datetime.fromisoformat(str(value)).date()
        except (TypeError, ValueError):
            return None

    @classmethod
    def age_days(cls, value, today=None):
        row_date = cls.parse_date(value)
        if row_date is None:
            return None
        today_date = today or date.today()
        if isinstance(today_date, datetime):
            today_date = today_date.date()
        elif not isinstance(today_date, date):
            today_date = cls.parse_date(today_date) or date.today()
        return (today_date - row_date).days

    @staticmethod
    def value(source, key):
        if isinstance(source, dict):
            return source.get(key)
        return getattr(source, key, None)

    @staticmethod
    def unique_tickers(tickers):
        result = []
        for ticker in tickers or []:
            value = str(ticker or "").strip().upper()
            if value and value not in result:
                result.append(value)
        return result

    @staticmethod
    def unique(values):
        result = []
        for value in values or []:
            if value and value not in result:
                result.append(value)
        return result
