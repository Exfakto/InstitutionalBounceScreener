from __future__ import annotations

from datetime import date, datetime

from market_data.models import MarketDataResult, OhlcvRow, UniverseSymbolResult
from market_data.validation import MarketDataValidator


class MarketDataService:
    """
    Safe market data facade for provider-backed historical data and symbols.
    """

    def __init__(self, provider=None, cache_repository=None, stale_days=10):
        self.provider = provider
        self.cache_repository = cache_repository
        self.stale_days = stale_days

    def fetch_daily_ohlcv(self, ticker, start_date=None, end_date=None, use_cache=True):
        normalized = self.normalize_ticker(ticker)
        warnings = []
        errors = []
        if not normalized:
            return MarketDataResult(False, ticker=None, errors=["Ticker is required"])

        start, end, date_errors = self.validate_date_range(start_date, end_date)
        if date_errors:
            return MarketDataResult(False, ticker=normalized, errors=date_errors)

        cached_rows = []
        if use_cache and self.cache_repository is not None and hasattr(self.cache_repository, "fetch_ohlcv"):
            cached_rows = self.cache_repository.fetch_ohlcv(normalized, start, end) or []
            if cached_rows:
                rows = [self.normalize_row(normalized, row, source=row.get("source")) for row in cached_rows]
                warnings.extend(MarketDataValidator.stale_data_warnings(rows, self.stale_days))
                return MarketDataResult(True, ticker=normalized, rows=rows, warnings=warnings)

        if self.provider is None or not hasattr(self.provider, "fetch_daily_ohlcv"):
            return MarketDataResult(False, ticker=normalized, errors=["No market data provider configured"])

        try:
            raw_rows = self.provider.fetch_daily_ohlcv(normalized, start, end) or []
        except Exception as exc:
            return MarketDataResult(False, ticker=normalized, errors=[str(exc)])

        rows = []
        for raw in raw_rows:
            row_warnings = self.row_warnings(raw)
            if row_warnings:
                warnings.extend(row_warnings)
                continue
            rows.append(self.normalize_row(normalized, raw, source=self.provider_source()))

        provider_warnings = getattr(self.provider, "last_warnings", []) or []
        provider_errors = getattr(self.provider, "last_errors", []) or []
        warnings.extend(provider_warnings)
        errors.extend(provider_errors)
        warnings.extend(MarketDataValidator.stale_data_warnings(rows, self.stale_days))

        if rows and self.cache_repository is not None and hasattr(self.cache_repository, "upsert_ohlcv"):
            self.cache_repository.upsert_ohlcv(normalized, rows, self.provider_source())

        return MarketDataResult(
            success=bool(rows) and not errors,
            ticker=normalized,
            rows=rows,
            warnings=self.unique(warnings),
            errors=self.unique(errors),
        )

    def fetch_fundamentals(self, ticker):
        normalized = self.normalize_ticker(ticker)
        if not normalized:
            return MarketDataResult(False, ticker=None, errors=["Ticker is required"])
        if self.provider is None or not hasattr(self.provider, "fetch_fundamentals"):
            return MarketDataResult(False, ticker=normalized, errors=["No market data provider configured"])
        try:
            return MarketDataResult(True, ticker=normalized, data=self.provider.fetch_fundamentals(normalized))
        except Exception as exc:
            return MarketDataResult(False, ticker=normalized, errors=[str(exc)])

    def fetch_universe_symbols(self, exchange=None):
        if self.provider is None or not hasattr(self.provider, "fetch_universe_symbols"):
            return UniverseSymbolResult(False, errors=["No market data provider configured"])
        try:
            symbols = self.provider.fetch_universe_symbols(exchange=exchange) or []
            warnings = getattr(self.provider, "last_warnings", []) or []
            errors = getattr(self.provider, "last_errors", []) or []
            return UniverseSymbolResult(
                success=not errors,
                symbols=list(symbols),
                warnings=self.unique(warnings),
                errors=self.unique(errors),
            )
        except Exception as exc:
            return UniverseSymbolResult(False, errors=[str(exc)])

    def get_price_history(self, ticker, start=None, end=None):
        result = self.fetch_daily_ohlcv(ticker, start, end)
        return [row.__dict__ for row in result.rows]

    @classmethod
    def row_warnings(cls, row):
        warnings = []
        missing = MarketDataValidator.missing_ohlcv_fields(row)
        if missing:
            warnings.append("Missing OHLCV fields: " + ", ".join(missing))
        invalid_prices = MarketDataValidator.invalid_prices(row)
        if invalid_prices:
            warnings.append("Invalid OHLCV prices: " + ", ".join(invalid_prices))
        if MarketDataValidator.invalid_volume(row):
            warnings.append("Invalid OHLCV volume")
        return warnings

    @classmethod
    def normalize_row(cls, ticker, row, source=None):
        return OhlcvRow(
            ticker=ticker,
            date=str(cls.value(row, "date")),
            open=float(cls.value(row, "open")),
            high=float(cls.value(row, "high")),
            low=float(cls.value(row, "low")),
            close=float(cls.value(row, "close")),
            volume=int(float(cls.value(row, "volume"))),
            source=source or cls.value(row, "source"),
        )

    @staticmethod
    def normalize_ticker(ticker):
        return str(ticker or "").strip().upper()

    @staticmethod
    def validate_date_range(start_date=None, end_date=None):
        errors = []
        start = MarketDataService.date_text(start_date)
        end = MarketDataService.date_text(end_date)
        if start_date is not None and start is None:
            errors.append("Invalid start_date")
        if end_date is not None and end is None:
            errors.append("Invalid end_date")
        if start and end and start > end:
            errors.append("start_date must be before or equal to end_date")
        return start, end, errors

    @staticmethod
    def date_text(value):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date().isoformat()
        if isinstance(value, date):
            return value.isoformat()
        try:
            return datetime.fromisoformat(str(value)).date().isoformat()
        except (TypeError, ValueError):
            return None

    @staticmethod
    def value(source, key):
        if isinstance(source, dict):
            return source.get(key)
        return getattr(source, key, None)

    def provider_source(self):
        return getattr(self.provider, "SOURCE", self.provider.__class__.__name__ if self.provider else None)

    @staticmethod
    def unique(values):
        result = []
        for value in values or []:
            if value and value not in result:
                result.append(value)
        return result
