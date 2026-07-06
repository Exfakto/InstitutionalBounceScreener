from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
import time

from providers.provider_result import ProviderResult
from services.market_data_refresh_service import MarketDataRefreshService
from services.screening_orchestrator import ScreeningOrchestrator


logger = logging.getLogger(__name__)

EXCLUDED_SECURITY_KEYWORDS = (
    "ETF",
    "ADR",
    "SPAC",
    "PREFERRED",
    "PREFERENCE",
    "WARRANT",
    "RIGHT",
    "UNIT",
    "FUND",
    "TRUST",
    "NOTE",
)


@dataclass(frozen=True)
class PipelineResult:
    success: bool = True
    processed: int = 0
    persisted: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)


class UniverseDownloaderService:
    def __init__(self, repository=None, provider_factory=None):
        self.repository = repository
        self.provider_factory = provider_factory

    def update_universe(self, exchanges=("NYSE", "NASDAQ"), deactivate_stale=True):
        warnings = []
        errors = []
        if self.provider_factory is None or not hasattr(self.provider_factory, "create"):
            return PipelineResult(
                False,
                warnings=["Market data provider factory is not configured"],
                errors=["provider factory unavailable"],
            )
        configured_provider = self.selected_provider_name()
        provider_result = self.provider_factory.create()
        provider = provider_result.provider
        provider_class = type(provider).__name__ if provider is not None else None
        logger.info(
            "Update Universe provider resolution: selected_market_data_provider=%s; "
            "provider_factory.create().provider_name=%s; provider_class=%s",
            configured_provider,
            provider_result.provider_name,
            provider_class,
        )
        if not provider_result.success:
            return PipelineResult(False, warnings=provider_result.warnings, errors=provider_result.errors)
        symbols = []
        fetched_by_exchange = {}
        for exchange in exchanges or []:
            try:
                fetched = provider.fetch_universe_symbols(exchange=exchange)
                rows, fetched_warnings, fetched_errors = self.unpack_provider_symbols(
                    fetched,
                    exchange,
                )
                symbols.extend(rows)
                fetched_by_exchange[exchange] = len(rows)
                warnings.extend(fetched_warnings)
                errors.extend(fetched_errors)
                logger.info(
                    "Update Universe fetch_universe_symbols: provider=%s; "
                    "provider_class=%s; exchange=%s; rows=%s; warnings=%s; errors=%s",
                    provider_result.provider_name,
                    provider_class,
                    exchange,
                    len(rows),
                    len(fetched_warnings),
                    len(fetched_errors),
                )
            except Exception as exc:
                errors.append(f"{exchange}: {exc}")
                fetched_by_exchange[exchange] = 0
                logger.exception(
                    "Update Universe fetch_universe_symbols failed: provider=%s; "
                    "provider_class=%s; exchange=%s",
                    provider_result.provider_name,
                    provider_class,
                    exchange,
                )
        eligible = self.unique_records(
            record
            for record in (
                self.normalize_symbol(row, provider_result.provider_name)
                for row in symbols
            )
            if record and self.is_eligible(record)
        )
        persisted = 0
        if self.repository is not None and hasattr(self.repository, "upsert_universe_symbols"):
            persisted = self.repository.upsert_universe_symbols(eligible)
            if deactivate_stale and hasattr(self.repository, "deactivate_stale_universe_symbols"):
                self.repository.deactivate_stale_universe_symbols([row["ticker"] for row in eligible])
        return PipelineResult(
            success=not errors,
            processed=len(symbols),
            persisted=persisted,
            warnings=warnings,
            errors=errors,
            details={
                "eligible_count": len(eligible),
                "selected_market_data_provider": configured_provider,
                "provider_name": provider_result.provider_name,
                "provider_class": provider_class,
                "fetched_by_exchange": fetched_by_exchange,
            },
        )

    def selected_provider_name(self):
        settings_service = getattr(self.provider_factory, "settings_service", None)
        if settings_service is None or not hasattr(settings_service, "get_preferences"):
            return None
        try:
            preferences = settings_service.get_preferences()
        except Exception:
            logger.exception("Unable to read selected market data provider preference")
            return None
        return getattr(preferences, "selected_market_data_provider", None)

    @classmethod
    def normalize_symbol(cls, record, source=None):
        ticker = cls.value(record, "ticker") or cls.value(record, "symbol")
        exchange = cls.value(record, "exchange")
        if not ticker or not exchange:
            return None
        return {
            "ticker": str(ticker).strip().upper(),
            "company_name": cls.value(record, "company_name") or cls.value(record, "name") or cls.value(record, "company"),
            "exchange": str(exchange).strip().upper(),
            "security_type": cls.value(record, "security_type") or cls.value(record, "type") or "Common Stock",
            "sector": cls.value(record, "sector"),
            "industry": cls.value(record, "industry"),
            "market_cap": cls.value(record, "market_cap"),
            "price": cls.value(record, "price"),
            "average_volume": cls.value(record, "average_volume"),
            "average_dollar_volume": cls.value(record, "average_dollar_volume"),
            "active": cls.active_flag(
                cls.value(record, "active")
                if cls.value(record, "active") is not None
                else cls.value(record, "is_active", default=1)
            ),
            "source": source or cls.value(record, "source"),
        }

    @classmethod
    def is_eligible(cls, record):
        if not record.get("active", 1):
            return False
        if record.get("exchange") not in {"NYSE", "NASDAQ"}:
            return False
        security_type = str(record.get("security_type") or "").upper()
        name = str(record.get("company_name") or "").upper()
        text = f"{security_type} {name}"
        if any(keyword in text for keyword in EXCLUDED_SECURITY_KEYWORDS):
            return False
        return "COMMON" in security_type or security_type in {"STOCK", "COMMON STOCK", "EQUITY"}

    @classmethod
    def unpack_provider_symbols(cls, fetched, exchange=None):
        if isinstance(fetched, ProviderResult):
            warnings = [f"{exchange}: {warning}" for warning in fetched.warnings]
            if not fetched.success:
                return [], warnings, [f"{exchange}: {fetched.message}"]
            return list(fetched.data or []), warnings, []
        return list(fetched or []), [], []

    @staticmethod
    def unique_records(records):
        unique = {}
        for record in records or []:
            ticker = record.get("ticker")
            exchange = record.get("exchange")
            if not ticker or not exchange:
                continue
            unique[(ticker, exchange)] = record
        return list(unique.values())

    @staticmethod
    def value(source, key, default=None):
        if isinstance(source, dict):
            return source.get(key, default)
        return getattr(source, key, default)

    @staticmethod
    def active_flag(value):
        if value in (False, 0, "0"):
            return 0
        if str(value).strip().lower() in {"false", "inactive", "no", "n"}:
            return 0
        return 1


class HistoricalDataUpdateService:
    SYNC_METADATA_KEY = "ohlcv_sync_metadata"
    SKIPPABLE_SYNC_STATUSES = {"no_data", "inactive", "error"}

    def __init__(self, repository=None, refresh_service=None, lookback_years=5):
        self.repository = repository
        self.refresh_service = refresh_service or MarketDataRefreshService(repository=repository)
        self.lookback_years = max(1, int(lookback_years or 5))

    def update_history(self, tickers, start_date=None, end_date=None, force_refresh=False, progress_callback=None, cancellation_callback=None):
        warnings = []
        errors = []
        persisted = 0
        normalized = self.unique_tickers(tickers)
        original_total = len(normalized)
        logger.info(
            "HistoricalDataUpdateService.update_history: repository_class=%s database_path=%s tickers=%s force_refresh=%s",
            MarketDataRefreshService.repository_class_name(self.repository),
            MarketDataRefreshService.repository_database_path(self.repository),
            original_total,
            force_refresh,
        )
        coverage = self.coverage_by_ticker()
        sync_status = self.sync_metadata_by_ticker(normalized)
        plan = self.build_sync_plan(
            normalized,
            coverage=coverage,
            sync_status=sync_status,
            force_refresh=force_refresh,
            start_date=start_date,
            end_date=end_date,
        )
        target_tickers = plan["target_tickers"]
        completed = []
        metadata_completed = []
        existing_metadata = self.load_sync_metadata()
        if not force_refresh and start_date is None:
            remaining = [
                ticker
                for ticker in (existing_metadata.get("remaining_tickers") or [])
                if ticker in target_tickers
            ]
            if remaining:
                metadata_completed = [
                    ticker
                    for ticker in (existing_metadata.get("completed_tickers") or [])
                    if ticker in normalized and ticker not in remaining
                ]
                target_tickers = remaining
        total = len(target_tickers)
        self.save_sync_metadata(
            normalized,
            target_tickers,
            metadata_completed,
            last_downloaded_ticker=existing_metadata.get("last_downloaded_ticker"),
            status="running",
        )
        refreshed = 0
        cache_hits = len(plan["current_tickers"])
        no_data = 0
        failed = 0
        skipped_current = len(plan["current_tickers"])
        skipped_no_data = len(plan["skipped_no_data_tickers"])
        skipped_error = len(plan["skipped_error_tickers"])
        skipped_inactive = len(plan["skipped_inactive_tickers"])
        cancelled = False
        started_at = time.perf_counter()
        for ticker in plan["current_tickers"]:
            cached = coverage.get(ticker, {})
            logger.info(
                "Historical OHLCV refresh skipped current ticker=%s cached_first_date=%s cached_last_date=%s requested_start_date=%s requested_end_date=%s rows_returned=0 rows_persisted=0 skipped_current=True",
                ticker,
                cached.get("first_date"),
                cached.get("last_date"),
                self.next_start_date(ticker, coverage),
                end_date or date.today().isoformat(),
            )
        for index, ticker in enumerate(target_tickers, start=1):
            if cancellation_callback and cancellation_callback():
                warnings.append("Historical update cancelled")
                cancelled = True
                self.save_sync_metadata(
                    normalized,
                    target_tickers[index - 1 :],
                    [*metadata_completed, *completed],
                    last_downloaded_ticker=completed[-1] if completed else None,
                    status="cancelled",
                )
                break
            cached = coverage.get(ticker, {})
            incremental_start = start_date
            if not force_refresh and incremental_start is None:
                incremental_start = self.next_start_date(ticker, coverage)
            if incremental_start is None:
                incremental_start = self.default_start_date(end_date=end_date)
            if progress_callback:
                progress_callback(
                    self.progress_event(
                        ticker,
                        index,
                        total,
                        original_total,
                        started_at,
                    )
                )
            try:
                if force_refresh:
                    self.clear_cached_ticker(ticker)
                result = self.refresh_service.refresh_ticker(
                    ticker,
                    start_date=incremental_start,
                    end_date=end_date,
                    force_refresh=force_refresh or ticker not in coverage,
                )
                if result.refreshed:
                    refreshed += 1
                    persisted += len(result.rows or [])
                    self.record_ticker_sync_success(ticker, status="current")
                elif getattr(result, "cache_hit", False):
                    cache_hits += 1
                    self.record_ticker_sync_success(ticker, status="current")
                elif not result.rows and not result.errors:
                    no_data += 1
                    self.record_ticker_sync_empty(ticker, result)
                rows_returned = len(result.rows or [])
                rows_persisted = getattr(result, "persisted", rows_returned if result.refreshed else 0)
                logger.info(
                    "Historical OHLCV refresh ticker=%s cached_first_date=%s cached_last_date=%s requested_start_date=%s requested_end_date=%s rows_returned=%s rows_persisted=%s skipped_current=False",
                    ticker,
                    cached.get("first_date"),
                    cached.get("last_date"),
                    incremental_start,
                    end_date or date.today().isoformat(),
                    rows_returned,
                    rows_persisted,
                )
                warnings.extend(f"{ticker}: {warning}" for warning in result.warnings)
                errors.extend(f"{ticker}: {error}" for error in result.errors)
                if result.errors:
                    failed += 1
                    self.record_ticker_sync_error(ticker, "; ".join(result.errors))
                completed.append(ticker)
                self.save_sync_metadata(
                    normalized,
                    target_tickers[index:],
                    [*metadata_completed, *completed],
                    last_downloaded_ticker=ticker,
                    status="running" if index < total else "complete",
                )
            except Exception as exc:
                errors.append(f"{ticker}: {exc}")
                failed += 1
                self.record_ticker_sync_error(ticker, str(exc))
                completed.append(ticker)
                self.save_sync_metadata(
                    normalized,
                    target_tickers[index:],
                    [*metadata_completed, *completed],
                    last_downloaded_ticker=ticker,
                    status="running" if index < total else "complete",
                )
        if not cancelled:
            self.save_sync_metadata(
                normalized,
                [],
                [*metadata_completed, *completed],
                last_downloaded_ticker=completed[-1] if completed else None,
                status="complete",
            )
        result = PipelineResult(
            not errors,
            processed=original_total,
            persisted=persisted,
            warnings=self.unique(warnings),
            errors=self.unique(errors),
            details={
                "refreshed_tickers": refreshed,
                "cache_hit_tickers": cache_hits,
                "no_data_tickers": no_data,
                "failed_tickers": failed,
                "skipped_current_tickers": skipped_current,
                "skipped_no_data_tickers": skipped_no_data,
                "skipped_error_tickers": skipped_error,
                "skipped_inactive_tickers": skipped_inactive,
                "cached_tickers": plan["cached_tickers"],
                "uncached_tickers": plan["uncached_tickers"],
                "stale_tickers": plan["stale_tickers"],
                "download_tickers": target_tickers,
                "coverage_before": len(coverage),
            },
        )
        logger.info(
            "HistoricalDataUpdateService.update_history complete: persisted=%s refreshed=%s cache_hits=%s no_data=%s errors=%s",
            persisted,
            refreshed,
            cache_hits,
            no_data,
            len(result.errors),
        )
        return result

    def build_sync_plan(
        self,
        tickers,
        coverage=None,
        sync_status=None,
        force_refresh=False,
        start_date=None,
        end_date=None,
    ):
        coverage = coverage if coverage is not None else self.coverage_by_ticker()
        sync_status = sync_status if sync_status is not None else self.sync_metadata_by_ticker(tickers)
        skippable_tickers = [] if force_refresh else [
            ticker
            for ticker in tickers
            if (sync_status.get(ticker, {}) or {}).get("status") in self.SKIPPABLE_SYNC_STATUSES
        ]
        skipped_no_data_tickers = [
            ticker
            for ticker in skippable_tickers
            if (sync_status.get(ticker, {}) or {}).get("status") == "no_data"
        ]
        skipped_error_tickers = [
            ticker
            for ticker in skippable_tickers
            if (sync_status.get(ticker, {}) or {}).get("status") == "error"
        ]
        skipped_inactive_tickers = [
            ticker
            for ticker in skippable_tickers
            if (sync_status.get(ticker, {}) or {}).get("status") == "inactive"
        ]
        active_tickers = [ticker for ticker in tickers if ticker not in skippable_tickers]
        cached_tickers = [
            ticker
            for ticker in active_tickers
            if int((coverage.get(ticker, {}) or {}).get("row_count") or 0) > 0
        ]
        uncached_tickers = [ticker for ticker in active_tickers if ticker not in cached_tickers]
        current_tickers = []
        stale_tickers = []
        for ticker in cached_tickers:
            next_start = self.next_start_date(ticker, coverage)
            if (
                not force_refresh
                and start_date is None
                and next_start is not None
                and not self.refresh_window_available(next_start, end_date)
            ):
                current_tickers.append(ticker)
            else:
                stale_tickers.append(ticker)
        target_tickers = list(tickers) if force_refresh else [*uncached_tickers, *stale_tickers]
        return {
            "cached_tickers": cached_tickers,
            "uncached_tickers": uncached_tickers,
            "stale_tickers": stale_tickers,
            "current_tickers": current_tickers,
            "skipped_no_data_tickers": skipped_no_data_tickers,
            "skipped_error_tickers": skipped_error_tickers,
            "skipped_inactive_tickers": skipped_inactive_tickers,
            "target_tickers": target_tickers,
        }

    def sync_metadata_by_ticker(self, tickers=None):
        if self.repository is None or not hasattr(self.repository, "fetch_ohlcv_sync_metadata"):
            return {}
        try:
            rows = self.repository.fetch_ohlcv_sync_metadata(tickers) or []
        except Exception:
            return {}
        return {
            str(row.get("ticker") or "").strip().upper(): dict(row)
            for row in rows
            if row.get("ticker")
        }

    def record_ticker_sync_success(self, ticker, status="current"):
        self.upsert_ticker_sync_metadata(
            ticker,
            last_attempted_at=self.timestamp(),
            last_success_at=self.timestamp(),
            last_error="",
            empty_response_count=0,
            status=status,
        )

    def record_ticker_sync_empty(self, ticker, result=None):
        current = self.sync_metadata_by_ticker([ticker]).get(str(ticker or "").strip().upper(), {})
        self.upsert_ticker_sync_metadata(
            ticker,
            last_attempted_at=self.timestamp(),
            last_success_at=current.get("last_success_at"),
            last_error="",
            empty_response_count=int(current.get("empty_response_count") or 0) + 1,
            status="no_data",
        )

    def record_ticker_sync_error(self, ticker, error):
        current = self.sync_metadata_by_ticker([ticker]).get(str(ticker or "").strip().upper(), {})
        self.upsert_ticker_sync_metadata(
            ticker,
            last_attempted_at=self.timestamp(),
            last_success_at=current.get("last_success_at"),
            last_error=error,
            empty_response_count=current.get("empty_response_count"),
            status="error",
        )

    def upsert_ticker_sync_metadata(self, ticker, **values):
        if self.repository is None or not hasattr(self.repository, "upsert_ohlcv_sync_metadata"):
            return 0
        try:
            return self.repository.upsert_ohlcv_sync_metadata(ticker, **values)
        except Exception:
            return 0

    @staticmethod
    def timestamp():
        return datetime.now(timezone.utc).isoformat()

    def next_start_date(self, ticker, coverage=None):
        coverage = coverage if coverage is not None else self.coverage_by_ticker(ticker)
        row = coverage.get(str(ticker or "").strip().upper())
        if row is None:
            return None
        last_date = row.get("last_date")
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

    def clear_cached_ticker(self, ticker):
        if self.repository is None or not hasattr(self.repository, "clear_ohlcv"):
            return 0
        deleted = self.repository.clear_ohlcv(ticker)
        logger.info("Historical OHLCV force refresh cleared ticker=%s rows=%s", ticker, deleted)
        return deleted

    def load_sync_metadata(self):
        if self.repository is None or not hasattr(self.repository, "cursor"):
            return {}
        try:
            self.repository.cursor.execute(
                "SELECT value_json FROM app_settings WHERE key = ?",
                (self.SYNC_METADATA_KEY,),
            )
            row = self.repository.cursor.fetchone()
        except Exception:
            logger.exception("Unable to load OHLCV sync metadata")
            return {}
        if row is None:
            return {}
        try:
            import json

            return json.loads(row["value_json"]) or {}
        except Exception:
            return {}

    def save_sync_metadata(
        self,
        all_tickers,
        remaining_tickers,
        completed_tickers,
        last_downloaded_ticker=None,
        status="running",
    ):
        if self.repository is None or not hasattr(self.repository, "cursor"):
            return {}
        now = datetime.now().isoformat(timespec="seconds")
        previous = self.load_sync_metadata()
        completed_unique = self.unique_tickers(completed_tickers)
        remaining_unique = self.unique_tickers(remaining_tickers)
        metadata = {
            "status": status,
            "updated_at": now,
            "last_full_sync": previous.get("last_full_sync"),
            "last_incremental_sync": previous.get("last_incremental_sync"),
            "last_downloaded_ticker": last_downloaded_ticker,
            "completed_tickers": completed_unique,
            "remaining_tickers": remaining_unique,
            "requested_tickers": self.unique_tickers(all_tickers),
        }
        if status == "complete":
            metadata["last_incremental_sync"] = now
            if not remaining_unique:
                metadata["last_full_sync"] = now
        try:
            import json

            self.repository.cursor.execute(
                """
                INSERT INTO app_settings (key, value_json, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET
                    value_json = excluded.value_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (self.SYNC_METADATA_KEY, json.dumps(metadata, sort_keys=True)),
            )
            self.repository.connection.commit()
        except Exception:
            logger.exception("Unable to save OHLCV sync metadata")
        return metadata

    @staticmethod
    def progress_event(ticker, index, total, original_total, started_at):
        elapsed = max(0.0, time.perf_counter() - started_at)
        processed = max(0, index - 1)
        average = elapsed / processed if processed else 0
        remaining = max(0, total - processed)
        eta = int(average * remaining) if average else None
        return {
            "stage": "ohlcv",
            "current_ticker": ticker,
            "processed": processed,
            "total": total,
            "universe_total": original_total,
            "estimated_remaining_seconds": eta,
            "status_message": (
                f"Downloading {index} of {original_total}; "
                f"Ticker: {ticker}; "
                f"ETA: {HistoricalDataUpdateService.format_eta(eta)}"
            ),
        }

    @staticmethod
    def format_eta(seconds):
        if seconds is None:
            return "calculating"
        minutes, sec = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}h {minutes}m"
        if minutes:
            return f"{minutes}m {sec}s"
        return f"{sec}s"

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

    def coverage_by_ticker(self, ticker=None):
        if self.repository is None or not hasattr(self.repository, "fetch_ohlcv_cache_coverage"):
            return {}
        rows = self.repository.fetch_ohlcv_cache_coverage(ticker) or []
        return {
            str(row.get("ticker") or "").strip().upper(): row
            for row in rows
            if row.get("ticker")
        }

    @staticmethod
    def refresh_window_available(start_date, end_date=None):
        try:
            start = datetime.fromisoformat(str(start_date)).date()
        except ValueError:
            return True
        end = HistoricalDataUpdateService.latest_trading_day(end_date)
        return start <= end

    @staticmethod
    def latest_trading_day(end_date=None):
        end = HistoricalDataUpdateService.parse_date(end_date) or date.today()
        while end.weekday() >= 5:
            end -= timedelta(days=1)
        return end

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


class FundamentalDownloaderService:
    def __init__(self, repository=None, provider_factory=None):
        self.repository = repository
        self.provider_factory = provider_factory

    def update_fundamentals(self, tickers, progress_callback=None, cancellation_callback=None):
        if self.provider_factory is None or not hasattr(self.provider_factory, "create"):
            return PipelineResult(
                False,
                warnings=["Market data provider factory is not configured"],
                errors=["provider factory unavailable"],
            )
        provider_result = self.provider_factory.create()
        if not provider_result.success:
            return PipelineResult(False, warnings=provider_result.warnings, errors=provider_result.errors)
        warnings = []
        errors = []
        records = []
        unique = HistoricalDataUpdateService.unique_tickers(tickers)
        for index, ticker in enumerate(unique, start=1):
            if cancellation_callback and cancellation_callback():
                warnings.append("Fundamental update cancelled")
                break
            if progress_callback:
                progress_callback({"stage": "fundamentals", "current_ticker": ticker, "processed": index - 1, "total": len(unique)})
            try:
                raw = provider_result.provider.fetch_fundamentals(ticker)
                record = self.normalize_fundamentals(ticker, raw, provider_result.provider_name)
                if record:
                    records.append(record)
            except Exception as exc:
                errors.append(f"{ticker}: {exc}")
        persisted = self.repository.upsert_fundamental_data(records) if self.repository is not None and hasattr(self.repository, "upsert_fundamental_data") else 0
        return PipelineResult(not errors, processed=len(unique), persisted=persisted, warnings=warnings, errors=errors)

    @staticmethod
    def normalize_fundamentals(ticker, raw, source=None):
        if raw is None:
            return None
        value = UniverseDownloaderService.value
        return {
            "ticker": ticker,
            "company_name": value(raw, "company_name") or value(raw, "company"),
            "sector": value(raw, "sector"),
            "industry": value(raw, "industry"),
            "market_cap": value(raw, "market_cap"),
            "revenue_growth_ttm": value(raw, "revenue_growth_ttm"),
            "eps_growth_ttm": value(raw, "eps_growth_ttm"),
            "roe": value(raw, "roe"),
            "gross_margin": value(raw, "gross_margin"),
            "free_cash_flow": value(raw, "free_cash_flow"),
            "debt_to_equity": value(raw, "debt_to_equity"),
            "current_ratio": value(raw, "current_ratio"),
            "bankruptcy_risk": value(raw, "bankruptcy_risk"),
            "going_concern_warning": value(raw, "going_concern_warning", 0),
            "last_earnings_date": value(raw, "last_earnings_date"),
            "source": source or value(raw, "source"),
        }


class InstitutionalDataRefreshService:
    def __init__(self, repository=None, provider_factory=None):
        self.repository = repository
        self.provider_factory = provider_factory

    def update_institutional_data(self, tickers, progress_callback=None, cancellation_callback=None):
        if self.provider_factory is None or not hasattr(self.provider_factory, "create"):
            return PipelineResult(
                False,
                warnings=["Market data provider factory is not configured"],
                errors=["provider factory unavailable"],
            )
        provider_result = self.provider_factory.create()
        if not provider_result.success:
            return PipelineResult(False, warnings=provider_result.warnings, errors=provider_result.errors)
        provider = provider_result.provider
        if not hasattr(provider, "fetch_institutional_data"):
            return PipelineResult(True, processed=len(tickers or []), warnings=["Provider does not expose institutional data"])
        warnings = []
        errors = []
        persisted = 0
        unique = HistoricalDataUpdateService.unique_tickers(tickers)
        for index, ticker in enumerate(unique, start=1):
            if cancellation_callback and cancellation_callback():
                warnings.append("Institutional update cancelled")
                break
            if progress_callback:
                progress_callback({"stage": "institutional", "current_ticker": ticker, "processed": index - 1, "total": len(unique)})
            try:
                raw = provider.fetch_institutional_data(ticker)
                record = self.normalize_institutional(ticker, raw, provider_result.provider_name)
                if record and self.repository is not None and hasattr(self.repository, "upsert_institutional_data"):
                    self.repository.upsert_institutional_data(record)
                    persisted += 1
            except Exception as exc:
                errors.append(f"{ticker}: {exc}")
        return PipelineResult(not errors, processed=len(unique), persisted=persisted, warnings=warnings, errors=errors)

    @staticmethod
    def normalize_institutional(ticker, raw, source=None):
        if raw is None:
            return None
        value = UniverseDownloaderService.value
        return {
            "ticker": ticker,
            "institutional_ownership_pct": value(raw, "institutional_ownership_pct"),
            "institutional_ownership_change_qoq": value(raw, "institutional_ownership_change_qoq"),
            "net_institutional_buying": value(raw, "net_institutional_buying"),
            "insider_buying_flag": value(raw, "insider_buying_flag", 0),
            "insider_selling_flag": value(raw, "insider_selling_flag", 0),
            "source": source or value(raw, "source"),
            "as_of_date": value(raw, "as_of_date") or date.today().isoformat(),
        }


class FullMarketRefreshOrchestrator:
    def __init__(self, repository=None, universe_service=None, historical_service=None, fundamental_service=None, institutional_service=None):
        self.repository = repository
        self.universe_service = universe_service
        self.historical_service = historical_service
        self.fundamental_service = fundamental_service
        self.institutional_service = institutional_service

    def refresh_all(self, progress_callback=None, cancellation_callback=None):
        warnings = []
        errors = []
        details = {}
        if self.universe_service is None:
            universe_result = PipelineResult(
                False,
                warnings=["universe service not configured"],
                errors=["universe service unavailable"],
            )
        else:
            universe_result = self.universe_service.update_universe()
        details["universe"] = universe_result
        warnings.extend(universe_result.warnings)
        errors.extend(universe_result.errors)
        tickers = self.eligible_tickers()
        if cancellation_callback and cancellation_callback():
            warnings.append("Full market refresh cancelled")
            return PipelineResult(False, processed=0, persisted=universe_result.persisted, warnings=warnings, errors=errors, details=details)
        for name, service, method_name in [
            ("ohlcv", self.historical_service, "update_history"),
            ("fundamentals", self.fundamental_service, "update_fundamentals"),
            ("institutional", self.institutional_service, "update_institutional_data"),
        ]:
            if service is None:
                warnings.append(f"{name} service not configured")
                continue
            result = getattr(service, method_name)(tickers, progress_callback=progress_callback, cancellation_callback=cancellation_callback)
            details[name] = result
            warnings.extend(result.warnings)
            errors.extend(result.errors)
        return PipelineResult(not errors, processed=len(tickers), persisted=sum(getattr(item, "persisted", 0) for item in details.values()), warnings=HistoricalDataUpdateService.unique(warnings), errors=HistoricalDataUpdateService.unique(errors), details=details)

    def eligible_tickers(self):
        if self.repository is not None and hasattr(self.repository, "fetch_eligible_universe_tickers"):
            return self.repository.fetch_eligible_universe_tickers()
        if self.repository is not None and hasattr(self.repository, "fetch_universe_symbols"):
            return [row["ticker"] for row in self.repository.fetch_universe_symbols(active_only=True)]
        return []

class FullMarketScanRunner:
    def __init__(self, repository=None, screening_orchestrator=None):
        self.repository = repository
        self.screening_orchestrator = screening_orchestrator or ScreeningOrchestrator(repository=repository)

    def run_scan(self, progress_callback=None, cancellation_callback=None):
        tickers = self.eligible_tickers_with_ohlcv()
        if not tickers:
            return PipelineResult(False, warnings=["No eligible tickers with OHLCV coverage"])
        result = self.screening_orchestrator.run(tickers, progress_callback=progress_callback, cancellation_callback=cancellation_callback)
        return PipelineResult(
            success=not result.errors,
            processed=result.tickers_processed,
            persisted=len(result.ranked_candidates),
            warnings=result.warnings,
            errors=result.errors,
            details={"run_id": result.run_id, "ranked_candidates": result.ranked_candidates},
        )

    def eligible_tickers_with_ohlcv(self):
        tickers = self.repository.fetch_eligible_universe_tickers() if self.repository is not None and hasattr(self.repository, "fetch_eligible_universe_tickers") else []
        result = []
        for ticker in tickers:
            rows = self.repository.fetch_ohlcv(ticker) if hasattr(self.repository, "fetch_ohlcv") else []
            if rows:
                result.append(ticker)
        return result


class DataCoverageReadinessService:
    def __init__(self, repository=None, stale_days=10):
        self.repository = repository
        self.stale_days = stale_days

    def report(self):
        tickers = self.repository.fetch_eligible_universe_tickers() if self.repository is not None and hasattr(self.repository, "fetch_eligible_universe_tickers") else []
        coverage_rows = self.repository.fetch_ohlcv_cache_coverage() if self.repository is not None and hasattr(self.repository, "fetch_ohlcv_cache_coverage") else []
        coverage_by_ticker = {row["ticker"]: row for row in coverage_rows}
        missing_ohlcv = [ticker for ticker in tickers if ticker not in coverage_by_ticker]
        stale = [ticker for ticker, row in coverage_by_ticker.items() if self.is_stale(row.get("last_date"))]
        missing_fundamentals = self.repository.fetch_missing_fundamental_tickers(tickers) if self.repository is not None and hasattr(self.repository, "fetch_missing_fundamental_tickers") else []
        institutional = self.repository.get_institutional_data_for_tickers(tickers) if self.repository is not None and hasattr(self.repository, "get_institutional_data_for_tickers") else {}
        missing_institutional = [ticker for ticker in tickers if ticker not in institutional]
        ready = [ticker for ticker in tickers if ticker not in missing_ohlcv and ticker not in missing_fundamentals]
        return {
            "ticker_count": len(tickers),
            "ohlcv_covered_count": len(tickers) - len(missing_ohlcv),
            "stale_data": stale,
            "missing_ohlcv": missing_ohlcv,
            "missing_fundamentals": missing_fundamentals,
            "missing_institutional": missing_institutional,
            "scan_ready_count": len(ready),
            "scan_ready": len(ready) > 0,
            "warnings": self.warnings(missing_ohlcv, missing_fundamentals, missing_institutional, stale),
        }

    def is_stale(self, last_date):
        if not last_date:
            return True
        try:
            value = datetime.fromisoformat(str(last_date)).date()
        except ValueError:
            return True
        return (date.today() - value).days > self.stale_days

    @staticmethod
    def warnings(missing_ohlcv, missing_fundamentals, missing_institutional, stale):
        result = []
        if missing_ohlcv:
            result.append(f"Missing OHLCV for {len(missing_ohlcv)} ticker(s)")
        if missing_fundamentals:
            result.append(f"Missing fundamentals for {len(missing_fundamentals)} ticker(s)")
        if missing_institutional:
            result.append(f"Missing institutional data for {len(missing_institutional)} ticker(s)")
        if stale:
            result.append(f"Stale OHLCV data for {len(stale)} ticker(s)")
        return result
