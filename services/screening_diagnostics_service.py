from __future__ import annotations

from dataclasses import dataclass, field

from services.screening_performance_analytics_service import (
    STAGES,
    ScreeningPerformanceAnalyticsService,
)


SLOW_STAGE_SECONDS = 30.0


@dataclass(frozen=True)
class ScreeningDiagnosticMessage:
    severity: str
    message: str
    recommended_action: str


@dataclass(frozen=True)
class ScreeningStageDiagnostic:
    stage_key: str
    stage_name: str
    status: str
    timing_seconds: float = 0.0
    cache_usage: str = "N/A"
    warning_count: int = 0
    error_count: int = 0
    messages: list[ScreeningDiagnosticMessage] = field(default_factory=list)


@dataclass(frozen=True)
class ScreeningDiagnosticsResult:
    run_id: str | None = None
    overall_status: str = "warning"
    symbol_count: int = 0
    total_time_seconds: float = 0.0
    warning_count: int = 0
    error_count: int = 0
    stages: list[ScreeningStageDiagnostic] = field(default_factory=list)
    messages: list[ScreeningDiagnosticMessage] = field(default_factory=list)


class ScreeningDiagnosticsService:
    """Build production diagnostics for screening pipeline health."""

    def __init__(self, repository=None, performance_analytics_service=None, slow_stage_seconds=SLOW_STAGE_SECONDS):
        self.repository = repository
        self.performance_analytics_service = (
            performance_analytics_service
            or ScreeningPerformanceAnalyticsService(repository=repository)
        )
        self.slow_stage_seconds = float(slow_stage_seconds or SLOW_STAGE_SECONDS)

    def get_latest_diagnostics(self):
        run = self.latest_run()
        if run is None:
            message = ScreeningDiagnosticMessage(
                severity="warning",
                message="No screening run diagnostics available.",
                recommended_action="Run a screening job before reviewing diagnostics.",
            )
            return ScreeningDiagnosticsResult(messages=[message])
        analytics = self.performance_analytics_service.analyze_latest()
        return self.build_diagnostics(run, analytics)

    def build_diagnostics(self, run, analytics=None):
        analytics = analytics or self.performance_analytics_service.analyze_run(run)
        run_warnings = list(value(run, "warnings") or [])
        run_errors = list(value(run, "errors") or [])
        stage_statuses = value(run, "stage_statuses") or {}
        cache_usage = value(run, "cache_usage") or {}
        stages = []
        messages = []
        for timing in analytics.stages:
            explicit_status = normalize_status(value(stage_statuses, timing.stage_key))
            status = explicit_status or "passed"
            stage_messages = []
            if timing.duration_seconds > self.slow_stage_seconds and status != "failed":
                status = "warning"
                stage_messages.append(
                    ScreeningDiagnosticMessage(
                        severity="warning",
                        message=f"{timing.stage_name} is unusually slow ({timing.duration_seconds:.2f}s).",
                        recommended_action="Review provider latency, cache coverage, and batch sizing.",
                    )
                )
            if explicit_status == "failed":
                stage_messages.append(
                    ScreeningDiagnosticMessage(
                        severity="failed",
                        message=f"{timing.stage_name} failed during the latest screening run.",
                        recommended_action="Inspect run errors and retry after fixing the failed stage.",
                    )
                )
            stages.append(
                ScreeningStageDiagnostic(
                    stage_key=timing.stage_key,
                    stage_name=timing.stage_name,
                    status=status,
                    timing_seconds=timing.duration_seconds,
                    cache_usage=str(value(cache_usage, timing.stage_key, "N/A")),
                    warning_count=len(run_warnings),
                    error_count=len(run_errors) if status == "failed" else 0,
                    messages=stage_messages,
                )
            )
            messages.extend(stage_messages)
        for warning in run_warnings:
            messages.append(
                ScreeningDiagnosticMessage(
                    severity="warning",
                    message=str(warning),
                    recommended_action="Review warning details before relying on the run output.",
                )
            )
        for error in run_errors:
            messages.append(
                ScreeningDiagnosticMessage(
                    severity="failed",
                    message=str(error),
                    recommended_action="Resolve the screening error and rerun the pipeline.",
                )
            )
        overall = overall_status(stages, run_errors, messages)
        return ScreeningDiagnosticsResult(
            run_id=value(run, "run_id"),
            overall_status=overall,
            symbol_count=int(value(analytics, "symbol_count") or 0),
            total_time_seconds=float(value(analytics, "total_screening_time_seconds") or 0.0),
            warning_count=len(run_warnings),
            error_count=len(run_errors),
            stages=stages,
            messages=messages,
        )

    def latest_run(self):
        if self.repository is None:
            return None
        if hasattr(self.repository, "fetch_latest_screening_run"):
            return self.repository.fetch_latest_screening_run()
        if hasattr(self.repository, "fetch_screening_run_history"):
            rows = self.repository.fetch_screening_run_history(limit=1) or []
            return rows[0] if rows else None
        return None


def normalize_status(raw):
    text = str(raw or "").strip().lower()
    if text in {"pass", "passed", "complete", "completed", "success"}:
        return "passed"
    if text in {"warn", "warning", "partial"}:
        return "warning"
    if text in {"fail", "failed", "error"}:
        return "failed"
    return None


def overall_status(stages, errors, messages):
    if errors or any(stage.status == "failed" for stage in stages):
        return "failed"
    if any(stage.status == "warning" for stage in stages) or any(
        message.severity == "warning" for message in messages
    ):
        return "warning"
    return "passed"


def value(source, key, default=None):
    if source is None:
        return default
    if isinstance(source, dict):
        return source.get(key, default)
    return getattr(source, key, default)
