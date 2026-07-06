from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from market_data.provider_factory import ProviderFactory
from services.market_data_service import MarketDataService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MarketDataRefreshResult:
    ticker: str | None = None
    success: bool = False
    rows: list = field(default_factory=list)
    persisted: int = 0
    cache_hit: bool = False
    refreshed: bool = False
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MarketDataBatchRefreshResult:
    results: dict[str, MarketDataRefreshResult] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class MarketDataRefreshService:
    """
    Cache-first OHLCV refresh workflow for screening and future UI actions.
    """

    def __init__(
        self,
        repository=None,
        provider_factory=None,
        market_data_service_factory=None,
        lookback_years=5,
    ):
        self.repository = repository
        self.provider_factory = provider_factory or ProviderFactory()
        self.market_data_service_factory = market_data_service_factory or MarketDataService
        self.lookback_years = max(1, int(lookback_years or 5))

    def refresh_ticker(
        self,
        ticker,
        start_date=None,
        end_date=None,
        force_refresh=False,
    ):
        normalized = self.normalize_ticker(ticker)
        if not normalized:
            return MarketDataRefreshResult(success=False, errors=["Ticker is required"])

        logger.info(
            "Refresh Market Data repository: class=%s database_path=%s",
            self.repository_class_name(self.repository),
            self.repository_database_path(self.repository),
        )

        requested_start = start_date
        requested_end = end_date or date.today().isoformat()
        coverage = self.coverage_for_ticker(normalized)
        if (
            not force_refresh
            and start_date is None
            and coverage is not None
        ):
            requested_start = self.next_start_date(coverage)
            if (
                requested_start is not None
                and not self.refresh_window_available(requested_start, requested_end)
            ):
                logger.info(
                    "Refresh Market Data skipped current ticker=%s cached_first_date=%s cached_last_date=%s requested_start_date=%s requested_end_date=%s rows_returned=0 rows_persisted=0",
                    normalized,
                    coverage.get("first_date"),
                    coverage.get("last_date"),
                    requested_start,
                    requested_end,
                )
                return MarketDataRefreshResult(
                    ticker=normalized,
                    success=True,
                    rows=[],
                    persisted=0,
                    cache_hit=True,
                    refreshed=False,
                )
        if requested_start is None:
            requested_start = self.default_start_date(requested_end)
        logger.info(
            "Refresh Market Data request window: ticker=%s cached_first_date=%s cached_last_date=%s requested_start_date=%s requested_end_date=%s force_refresh=%s",
            normalized,
            (coverage or {}).get("first_date"),
            (coverage or {}).get("last_date"),
            requested_start,
            requested_end,
            force_refresh,
        )

        factory_result = self.provider_factory.create()
        logger.info(
            "Refresh Market Data provider: provider_name=%s provider_class=%s",
            getattr(factory_result, "provider_name", None),
            self.repository_class_name(getattr(factory_result, "provider", None)),
        )
        if not factory_result.success:
            return MarketDataRefreshResult(
                ticker=normalized,
                success=False,
                warnings=factory_result.warnings,
                errors=factory_result.errors,
            )

        service = self.market_data_service_factory(
            provider=factory_result.provider,
            cache_repository=None,
        )
        result = service.fetch_daily_ohlcv(
            normalized,
            start_date=requested_start,
            end_date=requested_end,
            use_cache=False,
        )
        rows = result.rows
        written = 0
        if rows and self.repository is not None and hasattr(self.repository, "upsert_ohlcv"):
            logger.info(
                "Refresh Market Data upsert_ohlcv invoking: ticker=%s rows=%s database_path=%s",
                normalized,
                len(rows),
                self.repository_database_path(self.repository),
            )
            written = self.repository.upsert_ohlcv(
                normalized,
                rows,
                factory_result.provider_name,
            )
            logger.info(
                "Refresh Market Data upsert_ohlcv complete: ticker=%s rows_written=%s database_path=%s",
                normalized,
                written,
                self.repository_database_path(self.repository),
            )
        elif rows:
            logger.warning(
                "Refresh Market Data fetched rows but repository cannot persist OHLCV: "
                "ticker=%s rows=%s repository_class=%s",
                normalized,
                len(rows),
                self.repository_class_name(self.repository),
            )
        warnings = [*factory_result.warnings, *result.warnings]
        errors = [*factory_result.errors, *result.errors]
        has_cached_coverage = (
            not force_refresh
            and coverage is not None
            and int((coverage or {}).get("row_count") or 0) > 0
        )
        zero_row_incremental_success = has_cached_coverage and not rows and not errors
        if zero_row_incremental_success:
            warnings.append(f"No new OHLCV rows available for {normalized}")
        elif not rows and not errors:
            warnings.append(f"No OHLCV rows returned for {normalized}")
        logger.info(
            "Refresh Market Data completed: ticker=%s requested_start_date=%s requested_end_date=%s rows_returned=%s rows_persisted=%s",
            normalized,
            requested_start,
            requested_end,
            len(rows or []),
            written,
        )

        return MarketDataRefreshResult(
            ticker=normalized,
            success=(bool(rows) or zero_row_incremental_success) and not errors,
            rows=[row.__dict__ if hasattr(row, "__dict__") else row for row in rows],
            persisted=written,
            cache_hit=zero_row_incremental_success,
            refreshed=bool(rows),
            warnings=warnings,
            errors=errors,
        )

    def refresh_tickers(
        self,
        tickers,
        start_date=None,
        end_date=None,
        force_refresh=False,
        progress_callback=None,
        cancellation_callback=None,
    ):
        normalized = []
        for ticker in tickers or []:
            value = self.normalize_ticker(ticker)
            if value and value not in normalized:
                normalized.append(value)

        results = {}
        warnings = []
        errors = []
        total = len(normalized)
        for index, ticker in enumerate(normalized, start=1):
            if cancellation_callback is not None and cancellation_callback():
                warnings.append("Market data refresh cancelled")
                break
            if progress_callback is not None:
                progress_callback(
                    {
                        "total_tickers": total,
                        "processed_tickers": index - 1,
                        "current_ticker": ticker,
                        "status_message": f"Refreshing {ticker}",
                    }
                )
            result = self.refresh_ticker(
                ticker,
                start_date=start_date,
                end_date=end_date,
                force_refresh=force_refresh,
            )
            results[ticker] = result
            warnings.extend(result.warnings)
            errors.extend(result.errors)
            if progress_callback is not None:
                progress_callback(
                    {
                        "total_tickers": total,
                        "processed_tickers": index,
                        "current_ticker": ticker,
                        "status_message": f"Refreshed {ticker}",
                    }
                )

        return MarketDataBatchRefreshResult(
            results=results,
            warnings=self.unique(warnings),
            errors=self.unique(errors),
        )

    @staticmethod
    def normalize_ticker(ticker):
        return str(ticker or "").strip().upper()

    @staticmethod
    def unique(values):
        unique_values = []
        for value in values or []:
            if value and value not in unique_values:
                unique_values.append(value)
        return unique_values

    @staticmethod
    def repository_class_name(repository):
        if repository is None:
            return "None"
        return repository.__class__.__name__

    @staticmethod
    def repository_database_path(repository):
        if repository is None:
            return None
        value = getattr(repository, "database_path", None)
        if value is None:
            manager = getattr(repository, "manager", None)
            value = getattr(manager, "database_path", None)
        return str(value) if value is not None else None

    def coverage_for_ticker(self, ticker):
        if self.repository is None or not hasattr(self.repository, "fetch_ohlcv_cache_coverage"):
            return None
        rows = self.repository.fetch_ohlcv_cache_coverage(ticker) or []
        return rows[0] if rows else None

    @staticmethod
    def next_start_date(coverage):
        last_date = (coverage or {}).get("last_date")
        if not last_date:
            return None
        try:
            return (datetime.fromisoformat(str(last_date)).date() + timedelta(days=1)).isoformat()
        except ValueError:
            return None

    def default_start_date(self, end_date=None):
        end = self.parse_date(end_date) or date.today()
        try:
            return end.replace(year=end.year - self.lookback_years).isoformat()
        except ValueError:
            return (end - timedelta(days=365 * self.lookback_years)).isoformat()

    @staticmethod
    def parse_date(value):
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        try:
            return datetime.fromisoformat(str(value)).date()
        except ValueError:
            return None

    @staticmethod
    def refresh_window_available(start_date, end_date=None):
        start = MarketDataRefreshService.parse_date(start_date)
        if start is None:
            return True
        return start <= MarketDataRefreshService.latest_trading_day(end_date)

    @staticmethod
    def latest_trading_day(end_date=None):
        end = MarketDataRefreshService.parse_date(end_date) or date.today()
        while end.weekday() >= 5:
            end -= timedelta(days=1)
        return end
