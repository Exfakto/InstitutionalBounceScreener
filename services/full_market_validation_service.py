from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter

from services.full_market_pipeline import PipelineResult


@dataclass(frozen=True)
class StageValidationResult:
    stage: str
    success: bool
    elapsed_seconds: float = 0.0
    processed: int = 0
    persisted: int = 0
    skipped: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    coverage: dict = field(default_factory=dict)
    details: dict = field(default_factory=dict)

    @property
    def throughput_per_second(self):
        return self.processed / self.elapsed_seconds if self.elapsed_seconds else 0.0


@dataclass(frozen=True)
class FullMarketValidationReport:
    stages: list[StageValidationResult] = field(default_factory=list)
    coverage: dict = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)

    @property
    def success(self):
        return all(stage.success for stage in self.stages)

    @property
    def warnings(self):
        return [warning for stage in self.stages for warning in stage.warnings]

    @property
    def errors(self):
        return [error for stage in self.stages for error in stage.errors]

    @property
    def universe_size(self):
        return int(self.coverage.get("ticker_count") or 0)


class FullMarketValidationService:
    """
    Production validation harness for the full-market data pipeline.
    """

    def __init__(
        self,
        universe_service=None,
        historical_service=None,
        fundamental_service=None,
        institutional_service=None,
        scan_runner=None,
        coverage_service=None,
        ticker_source=None,
        clock=None,
    ):
        self.universe_service = universe_service
        self.historical_service = historical_service
        self.fundamental_service = fundamental_service
        self.institutional_service = institutional_service
        self.scan_runner = scan_runner
        self.coverage_service = coverage_service
        self.ticker_source = ticker_source
        self.clock = clock or perf_counter

    def validate(self, progress_callback=None, cancellation_callback=None):
        stages = []
        coverage = self.coverage()

        stages.append(
            self.run_stage(
                "Update Universe",
                lambda: self.universe_service.update_universe(),
                service=self.universe_service,
            )
        )
        coverage = self.coverage()
        tickers = self.tickers(coverage)

        stages.append(
            self.run_stage(
                "Refresh Market Data",
                lambda: self.historical_service.update_history(
                    tickers,
                    progress_callback=progress_callback,
                    cancellation_callback=cancellation_callback,
                ),
                service=self.historical_service,
                processed_default=len(tickers),
            )
        )
        coverage = self.coverage()

        stages.append(
            self.run_stage(
                "Refresh Fundamentals",
                lambda: self.fundamental_service.update_fundamentals(
                    tickers,
                    progress_callback=progress_callback,
                    cancellation_callback=cancellation_callback,
                ),
                service=self.fundamental_service,
                processed_default=len(tickers),
                optional=True,
            )
        )
        coverage = self.coverage()

        stages.append(
            self.run_stage(
                "Refresh Institutional Data",
                lambda: self.institutional_service.update_institutional_data(
                    tickers,
                    progress_callback=progress_callback,
                    cancellation_callback=cancellation_callback,
                ),
                service=self.institutional_service,
                processed_default=len(tickers),
                optional=True,
            )
        )
        coverage = self.coverage()

        stages.append(
            self.run_stage(
                "Run Full Market Scan",
                lambda: self.scan_runner.run_scan(
                    progress_callback=progress_callback,
                    cancellation_callback=cancellation_callback,
                ),
                service=self.scan_runner,
                processed_default=len(tickers),
            )
        )
        coverage = self.coverage()

        return FullMarketValidationReport(
            stages=stages,
            coverage=coverage,
            recommendations=self.recommendations(stages, coverage),
        )

    def run_stage(
        self,
        stage,
        action,
        service=None,
        processed_default=0,
        optional=False,
    ):
        if service is None:
            return StageValidationResult(
                stage=stage,
                success=True if optional else False,
                processed=processed_default,
                warnings=[f"{stage} service not configured"],
                errors=[] if optional else [f"{stage} service unavailable"],
            )

        started = self.clock()
        try:
            result = action()
        except Exception as exc:
            elapsed = self.clock() - started
            return StageValidationResult(
                stage=stage,
                success=False,
                elapsed_seconds=elapsed,
                processed=processed_default,
                errors=[self.exception_text(stage, exc)],
            )
        elapsed = self.clock() - started
        return self.stage_result(stage, result, elapsed, processed_default)

    def stage_result(self, stage, result, elapsed, processed_default=0):
        pipeline = result if isinstance(result, PipelineResult) else self.coerce_result(result)
        details = dict(pipeline.details or {})
        processed = int(pipeline.processed or processed_default or 0)
        persisted = int(pipeline.persisted or 0)
        skipped = int(details.get("skipped", max(processed - persisted, 0)) or 0)
        return StageValidationResult(
            stage=stage,
            success=bool(pipeline.success),
            elapsed_seconds=max(float(elapsed or 0.0), 0.0),
            processed=processed,
            persisted=persisted,
            skipped=skipped,
            warnings=list(pipeline.warnings or []),
            errors=list(pipeline.errors or []),
            coverage=self.coverage(),
            details=details,
        )

    def coverage(self):
        if self.coverage_service is None:
            return {}
        try:
            return dict(self.coverage_service.report() or {})
        except Exception as exc:
            return {"warnings": [f"Coverage report failed: {exc}"]}

    def tickers(self, coverage):
        if self.ticker_source is not None:
            return list(self.ticker_source() or [])
        tickers = coverage.get("eligible_tickers")
        if tickers is not None:
            return list(tickers)
        count = int(coverage.get("ticker_count") or 0)
        return [f"TICKER{index}" for index in range(count)]

    @staticmethod
    def coerce_result(result):
        return PipelineResult(
            success=bool(getattr(result, "success", True)),
            processed=int(getattr(result, "processed", 0) or 0),
            persisted=int(getattr(result, "persisted", 0) or 0),
            warnings=list(getattr(result, "warnings", []) or []),
            errors=list(getattr(result, "errors", []) or []),
            details=dict(getattr(result, "details", {}) or {}),
        )

    @staticmethod
    def exception_text(stage, exc):
        provider = getattr(exc, "provider", None)
        endpoint = getattr(exc, "endpoint", None)
        ticker = getattr(exc, "ticker", None)
        parts = [stage]
        if provider:
            parts.append(f"provider={provider}")
        if endpoint:
            parts.append(f"endpoint={endpoint}")
        if ticker:
            parts.append(f"ticker={ticker}")
        parts.append(f"exception={exc}")
        return "; ".join(parts)

    @staticmethod
    def recommendations(stages, coverage):
        recommendations = []
        ticker_count = int(coverage.get("ticker_count") or 0)
        scan_ready = int(coverage.get("scan_ready_count") or 0)
        if ticker_count <= 25:
            recommendations.append(
                "Universe discovery still appears seed-sized; verify live provider credentials and Update Universe wiring."
            )
        if ticker_count and scan_ready / ticker_count < 0.8:
            recommendations.append(
                "Market data coverage is below 80%; refresh OHLCV before relying on full-market scan output."
            )
        for stage in stages:
            if stage.errors:
                recommendations.append(f"Resolve {stage.stage} errors before GA validation sign-off.")
        if not recommendations:
            recommendations.append("No blocking recommendations from automated validation.")
        return recommendations

    @classmethod
    def markdown(cls, report):
        lines = [
            "# Full Market Validation",
            "",
            "## Summary",
            "",
            f"- Universe size: {report.universe_size:,}",
            f"- Overall status: {'PASS' if report.success else 'REVIEW REQUIRED'}",
            f"- Warning count: {len(report.warnings):,}",
            f"- Error count: {len(report.errors):,}",
            "",
            "## Coverage",
            "",
        ]
        for key, value in sorted(report.coverage.items()):
            if isinstance(value, list):
                lines.append(f"- {key}: {len(value):,}")
            else:
                lines.append(f"- {key}: {value}")
        lines.extend(["", "## Stages", ""])
        for stage in report.stages:
            lines.extend(
                [
                    f"### {stage.stage}",
                    "",
                    f"- Status: {'PASS' if stage.success else 'FAIL'}",
                    f"- Elapsed time: {stage.elapsed_seconds:.2f}s",
                    f"- Rows processed: {stage.processed:,}",
                    f"- Rows persisted: {stage.persisted:,}",
                    f"- Skipped records: {stage.skipped:,}",
                    f"- Throughput: {stage.throughput_per_second:.2f} rows/sec",
                    f"- Warnings: {len(stage.warnings):,}",
                    f"- Errors: {len(stage.errors):,}",
                    "",
                ]
            )
            if stage.warnings:
                lines.append("Warnings:")
                lines.extend(f"- {warning}" for warning in stage.warnings)
                lines.append("")
            if stage.errors:
                lines.append("Errors:")
                lines.extend(f"- {error}" for error in stage.errors)
                lines.append("")
        lines.extend(["## Recommendations", ""])
        lines.extend(f"- {item}" for item in report.recommendations)
        lines.append("")
        return "\n".join(lines)
