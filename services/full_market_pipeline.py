from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from services.market_data_refresh_service import MarketDataRefreshService
from services.screening_orchestrator import ScreeningOrchestrator


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
        provider_result = self.provider_factory.create()
        if not provider_result.success:
            return PipelineResult(False, warnings=provider_result.warnings, errors=provider_result.errors)
        provider = provider_result.provider
        symbols = []
        for exchange in exchanges or []:
            try:
                fetched = provider.fetch_universe_symbols(exchange=exchange) or []
                symbols.extend(fetched)
            except Exception as exc:
                errors.append(f"{exchange}: {exc}")
        eligible = [record for record in (self.normalize_symbol(row, provider_result.provider_name) for row in symbols) if record and self.is_eligible(record)]
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
            details={"eligible_count": len(eligible)},
        )

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
            "active": cls.value(record, "active") if cls.value(record, "active") is not None else cls.value(record, "is_active", default=1),
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

    @staticmethod
    def value(source, key, default=None):
        if isinstance(source, dict):
            return source.get(key, default)
        return getattr(source, key, default)


class HistoricalDataUpdateService:
    def __init__(self, repository=None, refresh_service=None):
        self.repository = repository
        self.refresh_service = refresh_service or MarketDataRefreshService(repository=repository)

    def update_history(self, tickers, start_date=None, end_date=None, force_refresh=False, progress_callback=None, cancellation_callback=None):
        warnings = []
        errors = []
        persisted = 0
        normalized = self.unique_tickers(tickers)
        total = len(normalized)
        for index, ticker in enumerate(normalized, start=1):
            if cancellation_callback and cancellation_callback():
                warnings.append("Historical update cancelled")
                break
            incremental_start = start_date
            if not force_refresh and incremental_start is None:
                incremental_start = self.next_start_date(ticker)
            if progress_callback:
                progress_callback({"stage": "ohlcv", "current_ticker": ticker, "processed": index - 1, "total": total})
            result = self.refresh_service.refresh_ticker(
                ticker,
                start_date=incremental_start,
                end_date=end_date,
                force_refresh=force_refresh,
            )
            persisted += len(result.rows or []) if result.refreshed else 0
            warnings.extend(f"{ticker}: {warning}" for warning in result.warnings)
            errors.extend(f"{ticker}: {error}" for error in result.errors)
        return PipelineResult(not errors, processed=total, persisted=persisted, warnings=self.unique(warnings), errors=self.unique(errors))

    def next_start_date(self, ticker):
        if self.repository is None or not hasattr(self.repository, "fetch_ohlcv_cache_coverage"):
            return None
        coverage = self.repository.fetch_ohlcv_cache_coverage(ticker) or []
        if not coverage:
            return None
        last_date = coverage[0].get("last_date")
        if not last_date:
            return None
        try:
            return (datetime.fromisoformat(str(last_date)).date() + timedelta(days=1)).isoformat()
        except ValueError:
            return None

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
