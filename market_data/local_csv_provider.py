from __future__ import annotations

import csv
from pathlib import Path

from market_data.models import OhlcvRow
from market_data.provider import MarketDataProvider
from market_data.validation import MarketDataValidator


class LocalCsvMarketDataProvider(MarketDataProvider):
    """
    Local CSV-backed provider for OHLCV, fundamentals, and universe symbols.
    """

    SOURCE = "local_csv"

    def __init__(self, data_directory):
        self.data_directory = Path(data_directory)
        self.last_warnings = []
        self.last_errors = []

    def fetch_daily_ohlcv(self, ticker, start_date=None, end_date=None):
        self.last_warnings = []
        self.last_errors = []
        normalized = self.normalize_ticker(ticker)
        if not normalized:
            self.last_errors.append("Ticker is required")
            return []

        path = self.data_directory / f"{normalized}.csv"
        if not path.exists():
            self.last_errors.append(f"OHLCV CSV not found: {path}")
            return []

        rows = []
        try:
            with path.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                for raw in reader:
                    normalized_row = {str(key).strip().lower(): value for key, value in raw.items()}
                    warnings = self.validate_raw_row(normalized_row)
                    if warnings:
                        self.last_warnings.extend(warnings)
                        continue
                    row = self.row_from_dict(normalized, normalized_row)
                    if start_date and row.date < str(start_date):
                        continue
                    if end_date and row.date > str(end_date):
                        continue
                    rows.append(row)
        except OSError as exc:
            self.last_errors.append(f"Unable to read OHLCV CSV: {exc}")
            return []

        duplicates = MarketDataValidator.duplicate_dates(rows)
        if duplicates:
            self.last_warnings.append("Duplicate OHLCV dates: " + ", ".join(duplicates))
        return rows

    def fetch_fundamentals(self, ticker):
        return self.get_fundamentals(ticker)

    def fetch_universe_symbols(self, exchange=None):
        provider = LocalCsvUniverseProvider(self.data_directory / "universe.csv")
        return provider.fetch_universe_symbols(exchange=exchange)

    def get_market_universe(self):
        return [symbol.__dict__ for symbol in self.fetch_universe_symbols()]

    def get_company_profile(self, ticker):
        return None

    def get_quote(self, ticker):
        rows = self.fetch_daily_ohlcv(ticker)
        if not rows:
            return None
        latest = rows[-1]
        return {"ticker": latest.ticker, "price": latest.close, "last_updated": latest.date}

    def get_bulk_quotes(self, tickers):
        return {
            quote["ticker"]: quote
            for quote in (self.get_quote(ticker) for ticker in (tickers or []))
            if quote is not None
        }

    def get_fundamentals(self, ticker):
        return None

    def get_last_updated(self):
        return None

    def validate_raw_row(self, row):
        warnings = []
        missing = MarketDataValidator.missing_ohlcv_fields(row)
        if missing:
            warnings.append("Missing OHLCV fields: " + ", ".join(missing))
            return warnings
        invalid_prices = MarketDataValidator.invalid_prices(row)
        if invalid_prices:
            warnings.append("Invalid OHLCV prices: " + ", ".join(invalid_prices))
        if MarketDataValidator.invalid_volume(row):
            warnings.append("Invalid OHLCV volume")
        return warnings

    @classmethod
    def row_from_dict(cls, ticker, row):
        return OhlcvRow(
            ticker=ticker,
            date=str(row.get("date")),
            open=float(row.get("open")),
            high=float(row.get("high")),
            low=float(row.get("low")),
            close=float(row.get("close")),
            volume=int(float(row.get("volume"))),
            source=cls.SOURCE,
        )

    @staticmethod
    def normalize_ticker(ticker):
        return str(ticker or "").strip().upper()


class UniverseSymbolProvider:
    def fetch_universe_symbols(self, exchange=None, security_type=None):
        raise NotImplementedError


class LocalCsvUniverseProvider(UniverseSymbolProvider):
    def __init__(self, csv_path):
        self.csv_path = Path(csv_path)
        self.last_warnings = []
        self.last_errors = []

    def fetch_universe_symbols(self, exchange=None, security_type=None):
        from market_data.models import UniverseSymbol

        self.last_warnings = []
        self.last_errors = []
        if not self.csv_path.exists():
            self.last_errors.append(f"Universe CSV not found: {self.csv_path}")
            return []

        exchange_filter = str(exchange or "").strip().upper()
        security_filter = str(security_type or "").strip().lower()
        symbols = []
        try:
            with self.csv_path.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                for raw in reader:
                    row = {str(key).strip().lower(): value for key, value in raw.items()}
                    ticker = str(row.get("ticker") or row.get("symbol") or "").strip().upper()
                    row_exchange = str(row.get("exchange") or "").strip().upper()
                    row_security = str(row.get("security_type") or "").strip()
                    if not ticker:
                        self.last_warnings.append("Skipping universe row without ticker")
                        continue
                    if exchange_filter and row_exchange != exchange_filter:
                        continue
                    if security_filter and row_security.lower() != security_filter:
                        continue
                    symbols.append(
                        UniverseSymbol(
                            ticker=ticker,
                            exchange=row_exchange or None,
                            security_type=row_security or None,
                            company_name=str(row.get("company_name") or "").strip() or None,
                        )
                    )
        except OSError as exc:
            self.last_errors.append(f"Unable to read universe CSV: {exc}")
            return []

        return symbols
