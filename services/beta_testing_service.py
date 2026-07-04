from __future__ import annotations

import csv
import json
import uuid
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from pathlib import Path

from services.app_config_service import AppConfigService
from services.full_market_pipeline import DataCoverageReadinessService, FullMarketScanRunner
from services.provider_diagnostics_service import ProviderDiagnosticsService


@dataclass(frozen=True)
class BetaTestRun:
    run_id: str
    started_at: str
    completed_at: str | None = None
    provider: str = "unknown"
    universe_count: int = 0
    scanned_count: int = 0
    candidates_count: int = 0
    backtest_count: int = 0
    status: str = "STARTED"
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CandidateReviewItem:
    ticker: str
    grade: str
    score: float
    setup_label: str
    support_zone_summary: str = "N/A"
    bounce_history_summary: str = "N/A"
    institutional_summary: str = "N/A"
    chart_data_available: bool = False
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ManualReviewChecklistItem:
    ticker: str
    chart_confirms_support: str = ""
    volume_confirms_accumulation: str = ""
    no_earnings_risk: str = ""
    sector_market_trend_acceptable: str = ""
    risk_reward_acceptable: str = ""
    decision: str = ""
    notes: str = ""


@dataclass(frozen=True)
class BetaWorkflowResult:
    run: BetaTestRun
    coverage_report: dict = field(default_factory=dict)
    candidates: list = field(default_factory=list)
    review_pack: list[CandidateReviewItem] = field(default_factory=list)
    checklist: list[ManualReviewChecklistItem] = field(default_factory=list)
    exports: dict = field(default_factory=dict)


class BetaTestRepository:
    def __init__(self, repository):
        self.repository = repository

    def save(self, run):
        if self.repository is None or not hasattr(self.repository, "save_beta_test_run"):
            return None
        return self.repository.save_beta_test_run(run)

    def fetch_latest(self):
        if self.repository is None or not hasattr(self.repository, "fetch_latest_beta_test_run"):
            return None
        return self.repository.fetch_latest_beta_test_run()

    def fetch_history(self, limit=25, offset=0):
        if self.repository is None or not hasattr(self.repository, "fetch_beta_test_run_history"):
            return []
        return self.repository.fetch_beta_test_run_history(limit=limit, offset=offset)

    def clear(self, run_id):
        if self.repository is None or not hasattr(self.repository, "clear_beta_test_run"):
            return 0
        return self.repository.clear_beta_test_run(run_id)


class CandidateReviewPackService:
    def __init__(self, repository=None, chart_data_service=None):
        self.repository = repository
        self.chart_data_service = chart_data_service

    def generate(self, candidates, top_n=10):
        ranked = sorted(
            list(candidates or []),
            key=lambda item: (
                self.number_value(item, "rank", 999999),
                -self.number_value(item, "final_score", 0),
                str(self.value(item, "ticker") or ""),
            ),
        )
        return [self.review_item(candidate) for candidate in ranked[: int(top_n or 10)]]

    def review_item(self, candidate):
        ticker = str(self.value(candidate, "ticker") or "N/A").upper()
        warnings = list(self.value(candidate, "warnings") or [])
        return CandidateReviewItem(
            ticker=ticker,
            grade=str(self.value(candidate, "grade") or "N/A"),
            score=float(self.number_value(candidate, "final_score", 0)),
            setup_label=str(self.value(candidate, "setup_label") or "N/A"),
            support_zone_summary=self.support_summary(ticker),
            bounce_history_summary=self.bounce_summary(ticker),
            institutional_summary=self.institutional_summary(ticker),
            chart_data_available=self.chart_available(ticker, candidate),
            warnings=warnings,
        )

    def support_summary(self, ticker):
        if self.repository is None or not hasattr(self.repository, "get_support_levels"):
            return "N/A"
        rows = self.repository.get_support_levels(ticker) or []
        if not rows:
            return "No support zones available"
        row = rows[0]
        return (
            f"{self.value(row, 'zone_low')} - {self.value(row, 'zone_high')}; "
            f"strength {self.value(row, 'strength_score')}"
        )

    def bounce_summary(self, ticker):
        if self.repository is None or not hasattr(self.repository, "get_bounce_validations"):
            return "N/A"
        rows = self.repository.get_bounce_validations(ticker) or []
        if not rows:
            return "No bounce history available"
        row = rows[0]
        return (
            f"{self.value(row, 'successful_bounces')}/{self.value(row, 'total_touches')} "
            f"successful; {self.value(row, 'bounce_success_rate')}% rate"
        )

    def institutional_summary(self, ticker):
        if self.repository is None or not hasattr(self.repository, "get_institutional_data"):
            return "N/A"
        row = self.repository.get_institutional_data(ticker)
        if row is None:
            return "No institutional data available"
        ownership = self.value(row, "institutional_ownership_pct")
        trend = self.value(row, "institutional_ownership_change_qoq")
        return f"Ownership {ownership if ownership is not None else 'N/A'}%; QoQ {trend if trend is not None else 'N/A'}"

    def chart_available(self, ticker, candidate):
        if self.chart_data_service is not None and hasattr(self.chart_data_service, "build_candidate_chart"):
            try:
                model = self.chart_data_service.build_candidate_chart(ticker, candidate)
                return bool(model)
            except Exception:
                return False
        if self.repository is not None and hasattr(self.repository, "fetch_ohlcv"):
            return bool(self.repository.fetch_ohlcv(ticker))
        return False

    @classmethod
    def checklist(cls, review_pack):
        return [ManualReviewChecklistItem(ticker=item.ticker) for item in (review_pack or [])]

    @staticmethod
    def value(source, key):
        if source is None:
            return None
        if isinstance(source, dict):
            return source.get(key)
        return getattr(source, key, None)

    @classmethod
    def number_value(cls, source, key, default=0):
        try:
            return float(cls.value(source, key))
        except (TypeError, ValueError):
            return default


class BetaWorkflowService:
    def __init__(
        self,
        repository=None,
        provider_diagnostics_service=None,
        coverage_service=None,
        scan_runner=None,
        backtest_runner=None,
        review_pack_service=None,
        export_service=None,
        app_config_service=None,
    ):
        self.repository = repository
        self.provider_diagnostics_service = provider_diagnostics_service or ProviderDiagnosticsService()
        self.coverage_service = coverage_service or DataCoverageReadinessService(repository)
        self.scan_runner = scan_runner or FullMarketScanRunner(repository=repository)
        self.backtest_runner = backtest_runner
        self.review_pack_service = review_pack_service or CandidateReviewPackService(repository)
        self.export_service = export_service or BetaReportExportService(app_config_service=app_config_service)
        self.run_repository = BetaTestRepository(repository)

    def run_workflow(
        self,
        top_n=10,
        run_backtest=False,
        export_report=True,
        progress_callback=None,
        cancellation_callback=None,
        run_id=None,
    ):
        started_at = now_utc()
        warnings = []
        errors = []
        run_id = run_id or f"beta-{uuid.uuid4().hex[:12]}"
        self.progress(progress_callback, "started", 0, "Starting beta workflow")

        provider_report = self.safe_call(self.provider_diagnostics_service.run)
        provider = self.value(provider_report, "selected_provider") or "unknown"
        credential_status = self.value(provider_report, "credential_status")
        if credential_status and credential_status != "Configured":
            warnings.append(str(credential_status))

        if self.cancelled(cancellation_callback):
            run = self.run_model(run_id, started_at, provider, "CANCELLED", warnings, errors)
            self.run_repository.save(run)
            return BetaWorkflowResult(run=run)

        self.progress(progress_callback, "coverage", 25, "Checking universe and data coverage")
        coverage_report = self.coverage_service.report() if self.coverage_service else {}
        warnings.extend(self.value(coverage_report, "warnings") or [])
        universe_count = int(self.value(coverage_report, "ticker_count") or 0)

        self.progress(progress_callback, "scan", 50, "Running full market scan")
        scan_result = self.safe_call(
            self.scan_runner.run_scan,
            progress_callback=progress_callback,
            cancellation_callback=cancellation_callback,
        )
        if scan_result is None:
            errors.append("Full market scan failed")
            candidates = []
            scanned_count = 0
        else:
            warnings.extend(self.value(scan_result, "warnings") or [])
            errors.extend(self.value(scan_result, "errors") or [])
            scanned_count = int(self.value(scan_result, "processed") or 0)
            candidates = self.value(self.value(scan_result, "details") or {}, "ranked_candidates") or []

        self.progress(progress_callback, "review_pack", 70, "Generating candidate review pack")
        review_pack = self.review_pack_service.generate(candidates, top_n=top_n)
        checklist = self.review_pack_service.checklist(review_pack)

        backtest_count = 0
        if run_backtest and self.backtest_runner is not None:
            self.progress(progress_callback, "backtest", 85, "Running beta backtest")
            backtest_result = self.safe_call(self.backtest_runner)
            if backtest_result is None:
                errors.append("Beta backtest failed")
            else:
                backtest_count = len(self.value(backtest_result, "trades") or backtest_result or [])

        status = "FAIL" if errors else ("WARNING" if warnings else "PASS")
        run = BetaTestRun(
            run_id=run_id,
            started_at=started_at,
            completed_at=now_utc(),
            provider=str(provider),
            universe_count=universe_count,
            scanned_count=scanned_count,
            candidates_count=len(candidates),
            backtest_count=backtest_count,
            status=status,
            warnings=unique(warnings),
            errors=unique(errors),
        )
        self.run_repository.save(run)
        result = BetaWorkflowResult(
            run=run,
            coverage_report=coverage_report,
            candidates=list(candidates or []),
            review_pack=review_pack,
            checklist=checklist,
        )
        if export_report:
            result.exports.update(self.export_service.export_all(result))
        self.progress(progress_callback, "complete", 100, "Beta workflow complete")
        return result

    @staticmethod
    def progress(callback, stage, percent, message):
        if callback:
            callback({"stage": stage, "progress_percentage": percent, "status_message": message})

    @staticmethod
    def cancelled(callback):
        return bool(callback and callback())

    @staticmethod
    def safe_call(callback, *args, **kwargs):
        try:
            return callback(*args, **kwargs)
        except Exception:
            return None

    @staticmethod
    def run_model(run_id, started_at, provider, status, warnings, errors):
        return BetaTestRun(
            run_id=run_id,
            started_at=started_at,
            completed_at=now_utc(),
            provider=str(provider),
            status=status,
            warnings=unique(warnings),
            errors=unique(errors),
        )

    @staticmethod
    def value(source, key):
        return CandidateReviewPackService.value(source, key)


class BetaReportExportService:
    def __init__(self, app_config_service=None):
        self.app_config_service = app_config_service or AppConfigService()

    def export_all(self, result, output_dir=None, basename=None):
        basename = basename or result.run.run_id
        return {
            "summary_json": self.export_run_summary_json(result, output_dir, f"{basename}_summary.json")["path"],
            "review_pack_json": self.export_review_pack_json(result.review_pack, output_dir, f"{basename}_review_pack.json")["path"],
            "review_pack_csv": self.export_review_pack_csv(result.review_pack, output_dir, f"{basename}_review_pack.csv")["path"],
            "checklist_csv": self.export_manual_checklist_csv(result.checklist, output_dir, f"{basename}_manual_checklist.csv")["path"],
        }

    def export_run_summary_json(self, result, output_dir=None, filename="beta_run_summary.json"):
        path = self.destination(output_dir, filename)
        payload = json_safe(result)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return {"success": True, "path": str(path)}

    def export_review_pack_json(self, review_pack, output_dir=None, filename="candidate_review_pack.json"):
        path = self.destination(output_dir, filename)
        path.write_text(json.dumps(json_safe(review_pack), indent=2, sort_keys=True), encoding="utf-8")
        return {"success": True, "path": str(path), "count": len(review_pack or [])}

    def export_review_pack_csv(self, review_pack, output_dir=None, filename="candidate_review_pack.csv"):
        path = self.destination(output_dir, filename)
        fields = [
            "ticker",
            "grade",
            "score",
            "setup_label",
            "support_zone_summary",
            "bounce_history_summary",
            "institutional_summary",
            "chart_data_available",
            "warnings",
        ]
        rows = []
        for item in review_pack or []:
            row = json_safe(item)
            row["warnings"] = "; ".join(str(value) for value in row.get("warnings") or [])
            rows.append(row)
        self.write_csv(path, fields, rows)
        return {"success": True, "path": str(path), "count": len(rows)}

    def export_manual_checklist_csv(self, checklist, output_dir=None, filename="manual_review_checklist.csv"):
        path = self.destination(output_dir, filename)
        fields = [
            "ticker",
            "chart_confirms_support",
            "volume_confirms_accumulation",
            "no_earnings_risk",
            "sector_market_trend_acceptable",
            "risk_reward_acceptable",
            "decision",
            "notes",
        ]
        rows = [json_safe(item) for item in (checklist or [])]
        self.write_csv(path, fields, rows)
        return {"success": True, "path": str(path), "count": len(rows)}

    def destination(self, output_dir, filename):
        directory = Path(output_dir or self.app_config_service.load().export_directory)
        directory.mkdir(parents=True, exist_ok=True)
        safe = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in str(filename))
        return directory / safe

    @staticmethod
    def write_csv(path, fields, rows):
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)


class BetaReadinessDiagnosticsService:
    def __init__(self, repository=None, provider_diagnostics_service=None, coverage_service=None, app_config_service=None):
        self.repository = repository
        self.provider_diagnostics_service = provider_diagnostics_service or ProviderDiagnosticsService()
        self.coverage_service = coverage_service or DataCoverageReadinessService(repository)
        self.app_config_service = app_config_service or AppConfigService()

    def run(self):
        items = []
        provider = BetaWorkflowService.safe_call(self.provider_diagnostics_service.run)
        credential_status = CandidateReviewPackService.value(provider, "credential_status")
        items.append(self.item("provider_configured", credential_status == "Configured", credential_status or "Unknown"))
        coverage = self.coverage_service.report() if self.coverage_service else {}
        universe_count = int(CandidateReviewPackService.value(coverage, "ticker_count") or 0)
        ohlcv_count = int(CandidateReviewPackService.value(coverage, "ohlcv_covered_count") or 0)
        missing_fundamentals = CandidateReviewPackService.value(coverage, "missing_fundamentals") or []
        missing_institutional = CandidateReviewPackService.value(coverage, "missing_institutional") or []
        items.append(self.item("universe_available", universe_count > 0, f"{universe_count} ticker(s)"))
        items.append(self.item("ohlcv_coverage", ohlcv_count > 0, f"{ohlcv_count} ticker(s) with OHLCV"))
        items.append(self.item("fundamentals_coverage", universe_count > len(missing_fundamentals), f"{len(missing_fundamentals)} missing"))
        items.append(self.item("institutional_coverage", universe_count > len(missing_institutional), f"{len(missing_institutional)} missing"))
        export_dir = self.app_config_service.load().export_directory
        writable = self.app_config_service.is_writable_directory(export_dir)
        items.append(self.item("export_path_writable", writable, str(export_dir)))
        status = "FAIL" if any(item["status"] == "FAIL" for item in items) else (
            "WARNING" if any(item["status"] == "WARNING" for item in items) else "PASS"
        )
        return {"status": status, "items": items}

    @staticmethod
    def item(name, passed, message):
        return {"name": name, "status": "PASS" if passed else "WARNING", "message": message}


def now_utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def unique(values):
    result = []
    for value in values or []:
        if value and value not in result:
            result.append(str(value))
    return result


def json_safe(value):
    if is_dataclass(value):
        return json_safe(asdict(value))
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value
