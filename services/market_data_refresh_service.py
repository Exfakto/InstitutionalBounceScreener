from __future__ import annotations

from dataclasses import dataclass, field

from market_data.provider_factory import ProviderFactory
from services.market_data_service import MarketDataService


@dataclass(frozen=True)
class MarketDataRefreshResult:
    ticker: str | None = None
    success: bool = False
    rows: list = field(default_factory=list)
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

    def __init__(self, repository=None, provider_factory=None, market_data_service_factory=None):
        self.repository = repository
        self.provider_factory = provider_factory or ProviderFactory()
        self.market_data_service_factory = market_data_service_factory or MarketDataService

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

        if (
            not force_refresh
            and self.repository is not None
            and hasattr(self.repository, "fetch_ohlcv")
        ):
            cached = self.repository.fetch_ohlcv(normalized, start_date, end_date) or []
            if cached:
                return MarketDataRefreshResult(
                    ticker=normalized,
                    success=True,
                    rows=cached,
                    cache_hit=True,
                    refreshed=False,
                )

        factory_result = self.provider_factory.create()
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
            start_date=start_date,
            end_date=end_date,
            use_cache=False,
        )
        rows = result.rows
        if rows and self.repository is not None and hasattr(self.repository, "upsert_ohlcv"):
            self.repository.upsert_ohlcv(normalized, rows, factory_result.provider_name)

        return MarketDataRefreshResult(
            ticker=normalized,
            success=result.success,
            rows=[row.__dict__ if hasattr(row, "__dict__") else row for row in rows],
            cache_hit=False,
            refreshed=bool(rows),
            warnings=[*factory_result.warnings, *result.warnings],
            errors=[*factory_result.errors, *result.errors],
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
