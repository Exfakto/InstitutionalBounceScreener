from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from pathlib import Path

from config.app_metadata import VERSION
from services.app_config_service import AppConfigService
from services.data_quality_service import DataQualityService
from services.market_data_cache_service import MarketDataCacheService
from services.market_data_refresh_service import MarketDataRefreshService
from services.provider_diagnostics_service import ProviderDiagnosticsService
from services.release_diagnostics_service import ReleaseDiagnosticsService


VALIDATION_BASKET = (
    "AAPL",
    "MSFT",
    "NVDA",
    "AMZN",
    "META",
    "GOOGL",
    "JPM",
    "XOM",
    "UNH",
    "COST",
)


@dataclass(frozen=True)
class BetaValidationIssue:
    area: str
    severity: str
    message: str
    ticker: str | None = None


@dataclass(frozen=True)
class BetaValidationReport:
    timestamp: str
    app_version: str
    provider: str
    validation_basket: list[str]
    ticker_coverage: dict[str, dict]
    scan_result_count: int = 0
    backtest_result_count: int = 0
    issues: list[BetaValidationIssue] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    summary: str = "Not run"


class BetaValidationService:
    """
    Local-first beta readiness validation using the configured market-data path.
    """

    def __init__(
        self,
        repository=None,
        app_config_service=None,
        provider_diagnostics_service=None,
        release_diagnostics_service=None,
        market_data_refresh_service=None,
        cache_service=None,
        data_quality_service=None,
        screening_runner=None,
        backtest_runner=None,
        validation_basket=None,
    ):
        self.repository = repository
        self.app_config_service = app_config_service or AppConfigService()
        self.provider_diagnostics_service = (
            provider_diagnostics_service or ProviderDiagnosticsService()
        )
        self.release_diagnostics_service = (
            release_diagnostics_service or ReleaseDiagnosticsService()
        )
        self.market_data_refresh_service = (
            market_data_refresh_service or MarketDataRefreshService(repository=repository)
        )
        self.cache_service = cache_service or MarketDataCacheService(repository=repository)
        self.data_quality_service = data_quality_service or DataQualityService(repository=repository)
        self.screening_runner = screening_runner
        self.backtest_runner = backtest_runner
        self.validation_basket = tuple(validation_basket or VALIDATION_BASKET)

    def run(self, force_refresh=False, progress_callback=None):
        timestamp = datetime.now(timezone.utc).isoformat()
        issues = []
        warnings = []
        errors = []

        release_report = self.safe_call(self.release_diagnostics_service.run)
        if release_report is None:
            issues.append(BetaValidationIssue("startup", "ERROR", "Release diagnostics failed"))
        else:
            for message in getattr(release_report, "warnings", []) or []:
                issues.append(BetaValidationIssue("startup", "WARNING", str(message)))
            for message in getattr(release_report, "errors", []) or []:
                issues.append(BetaValidationIssue("startup", "ERROR", str(message)))

        provider_report = self.safe_call(self.provider_diagnostics_service.run)
        provider = getattr(provider_report, "selected_provider", None) or "unknown"
        credential_status = getattr(provider_report, "credential_status", "Unknown")
        if credential_status != "Configured":
            issues.append(
                BetaValidationIssue(
                    "provider",
                    "WARNING",
                    credential_status,
                )
            )

        refresh_result = self.market_data_refresh_service.refresh_tickers(
            self.validation_basket,
            force_refresh=force_refresh,
            progress_callback=progress_callback,
        )
        for message in getattr(refresh_result, "warnings", []) or []:
            issues.append(BetaValidationIssue("market_data", "WARNING", str(message)))
        for message in getattr(refresh_result, "errors", []) or []:
            issues.append(BetaValidationIssue("market_data", "ERROR", str(message)))

        coverage = self.coverage_by_ticker()
        ticker_coverage = {}
        for ticker in self.validation_basket:
            row = coverage.get(ticker)
            row_count = int(self.value(row, "row_count") or 0) if row else 0
            ticker_coverage[ticker] = {
                "row_count": row_count,
                "first_date": self.value(row, "first_date") if row else None,
                "last_date": self.value(row, "last_date") if row else None,
                "stale": bool(self.value(row, "stale")) if row else False,
            }
            if row_count == 0:
                issues.append(
                    BetaValidationIssue(
                        "ohlcv_cache",
                        "WARNING",
                        "No cached OHLCV coverage",
                        ticker=ticker,
                    )
                )

        quality_report = self.data_quality_service.generate_report(self.validation_basket)
        for message in getattr(quality_report, "warnings", []) or []:
            issues.append(BetaValidationIssue("data_quality", "WARNING", str(message)))

        scan_result_count = self.run_screening_validation(issues)
        backtest_result_count = self.run_backtest_validation(issues)

        warnings = [issue.message for issue in issues if issue.severity == "WARNING"]
        errors = [issue.message for issue in issues if issue.severity == "ERROR"]
        status = "FAIL" if errors else ("WARNING" if warnings else "PASS")
        return BetaValidationReport(
            timestamp=timestamp,
            app_version=VERSION,
            provider=provider,
            validation_basket=list(self.validation_basket),
            ticker_coverage=ticker_coverage,
            scan_result_count=scan_result_count,
            backtest_result_count=backtest_result_count,
            issues=issues,
            warnings=self.unique(warnings),
            errors=self.unique(errors),
            summary=(
                f"{status}: {len(self.validation_basket)} tickers, "
                f"{scan_result_count} scan result(s), "
                f"{backtest_result_count} backtest result(s), "
                f"{len(issues)} issue(s)"
            ),
        )

    def coverage_by_ticker(self):
        rows = self.cache_service.coverage()
        return {str(row.ticker).upper(): row for row in rows}

    def run_screening_validation(self, issues):
        if self.screening_runner is None:
            issues.append(
                BetaValidationIssue(
                    "screening",
                    "WARNING",
                    "No screening runner configured for beta validation",
                )
            )
            return 0
        try:
            result = self.screening_runner(self.validation_basket)
            candidates = self.value(result, "ranked_candidates") or result or []
            return len(candidates)
        except Exception as exc:
            issues.append(BetaValidationIssue("screening", "ERROR", str(exc)))
            return 0

    def run_backtest_validation(self, issues):
        if self.backtest_runner is None:
            issues.append(
                BetaValidationIssue(
                    "backtest",
                    "WARNING",
                    "No backtest runner configured for beta validation",
                )
            )
            return 0
        try:
            result = self.backtest_runner()
            trades = self.value(result, "trades") or result or []
            return len(trades)
        except Exception as exc:
            issues.append(BetaValidationIssue("backtest", "ERROR", str(exc)))
            return 0

    def export_report(self, report, output_dir=None, basename="beta_validation_report"):
        config = self.app_config_service.load()
        directory = Path(output_dir or config.export_directory)
        directory.mkdir(parents=True, exist_ok=True)
        json_path = directory / f"{basename}.json"
        csv_path = directory / f"{basename}_issues.csv"
        json_path.write_text(
            json.dumps(self.json_safe(report), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["area", "severity", "ticker", "message"],
            )
            writer.writeheader()
            for issue in report.issues:
                writer.writerow(
                    {
                        "area": issue.area,
                        "severity": issue.severity,
                        "ticker": issue.ticker,
                        "message": issue.message,
                    }
                )
        return {
            "success": True,
            "json_path": str(json_path),
            "csv_path": str(csv_path),
            "issue_count": len(report.issues),
        }

    @staticmethod
    def safe_call(callback):
        try:
            return callback()
        except Exception:
            return None

    @staticmethod
    def value(source, key):
        if source is None:
            return None
        if isinstance(source, dict):
            return source.get(key)
        return getattr(source, key, None)

    @classmethod
    def json_safe(cls, value):
        if is_dataclass(value):
            return cls.json_safe(asdict(value))
        if isinstance(value, dict):
            return {str(key): cls.json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [cls.json_safe(item) for item in value]
        return value

    @staticmethod
    def unique(values):
        result = []
        for value in values or []:
            if value and value not in result:
                result.append(value)
        return result
