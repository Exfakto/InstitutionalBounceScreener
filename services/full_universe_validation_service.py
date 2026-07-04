from __future__ import annotations

from dataclasses import dataclass, field

from services.universe_scan_adapter import UniverseScanAdapter


ISSUE_CATEGORIES = {
    "data missing",
    "provider failure",
    "calculation failure",
    "ranking failure",
    "export failure",
}


@dataclass(frozen=True)
class FullUniverseValidationIssue:
    category: str
    ticker: str | None
    message: str
    severity: str = "warning"


@dataclass(frozen=True)
class FullUniverseValidationResult:
    status: str
    total_symbols: int = 0
    processed_symbols: int = 0
    skipped_symbols: int = 0
    failed_symbols: int = 0
    completion_rate: float = 0.0
    issues: list[FullUniverseValidationIssue] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class FullUniverseValidationService:
    """Validate that the existing screener can process the full universe safely."""

    def __init__(
        self,
        universe_adapter=None,
        screening_runner=None,
        diagnostics_service=None,
    ):
        self.universe_adapter = universe_adapter
        self.screening_runner = screening_runner
        self.diagnostics_service = diagnostics_service

    def validate(self, progress_callback=None, cancellation_callback=None):
        tickers = self.load_universe()
        total = len(tickers)
        issues = []
        warnings = []
        errors = []
        if total == 0:
            issue = FullUniverseValidationIssue(
                category="data missing",
                ticker=None,
                message="No eligible NYSE/NASDAQ universe symbols available.",
                severity="warning",
            )
            return FullUniverseValidationResult(
                status="warning",
                total_symbols=0,
                issues=[issue],
                warnings=[issue.message],
            )

        self.progress(progress_callback, total, 0, "Starting full universe validation")
        processed = 0
        failed_symbols = set()
        skipped_symbols = set()
        try:
            result = self.run_screening(tickers, progress_callback, cancellation_callback)
        except Exception as exc:
            issue = FullUniverseValidationIssue(
                category="provider failure",
                ticker=None,
                message=str(exc),
                severity="failed",
            )
            return FullUniverseValidationResult(
                status="failed",
                total_symbols=total,
                processed_symbols=0,
                skipped_symbols=0,
                failed_symbols=total,
                completion_rate=0.0,
                issues=[issue],
                errors=[str(exc)],
            )

        processed = int(value(result, "processed") or value(result, "tickers_processed") or 0)
        warnings.extend(str(item) for item in (value(result, "warnings") or []))
        errors.extend(str(item) for item in (value(result, "errors") or []))
        issues.extend(self.issues_from_messages(warnings, severity="warning"))
        issues.extend(self.issues_from_messages(errors, severity="failed"))
        failed_symbols.update(issue.ticker for issue in issues if issue.ticker)
        skipped_count = max(0, total - processed - len(failed_symbols))
        for ticker in tickers[processed + len(failed_symbols):]:
            skipped_symbols.add(ticker)
        self.progress(progress_callback, total, processed, "Full universe validation complete")
        status = self.status_for(total, processed, issues, errors)
        return FullUniverseValidationResult(
            status=status,
            total_symbols=total,
            processed_symbols=processed,
            skipped_symbols=skipped_count,
            failed_symbols=len(failed_symbols) if failed_symbols else len(errors),
            completion_rate=round((processed / total) * 100.0, 6) if total else 0.0,
            issues=issues,
            warnings=warnings,
            errors=errors,
        )

    def load_universe(self):
        if self.universe_adapter is None:
            return []
        if hasattr(self.universe_adapter, "load_tickers"):
            return list(self.universe_adapter.load_tickers() or [])
        if callable(self.universe_adapter):
            return UniverseScanAdapter.normalize_tickers(self.universe_adapter())
        return []

    def run_screening(self, tickers, progress_callback=None, cancellation_callback=None):
        if self.screening_runner is None:
            return {"processed": len(tickers), "warnings": [], "errors": []}
        if hasattr(self.screening_runner, "run_scan"):
            return self.screening_runner.run_scan(
                progress_callback=progress_callback,
                cancellation_callback=cancellation_callback,
            )
        if hasattr(self.screening_runner, "run"):
            return self.screening_runner.run(
                tickers,
                progress_callback=progress_callback,
                cancellation_callback=cancellation_callback,
            )
        if callable(self.screening_runner):
            return self.screening_runner(tickers)
        return {"processed": len(tickers), "warnings": [], "errors": []}

    def issues_from_messages(self, messages, severity):
        return [
            FullUniverseValidationIssue(
                category=self.category_for_message(message),
                ticker=self.ticker_from_message(message),
                message=str(message),
                severity=severity,
            )
            for message in messages or []
        ]

    @staticmethod
    def category_for_message(message):
        text = str(message or "").lower()
        if any(token in text for token in ("missing", "no data", "ohlcv", "coverage")):
            return "data missing"
        if any(token in text for token in ("provider", "api", "timeout", "connection")):
            return "provider failure"
        if any(token in text for token in ("calculation", "indicator", "support", "bounce")):
            return "calculation failure"
        if "rank" in text:
            return "ranking failure"
        if "export" in text:
            return "export failure"
        return "calculation failure"

    @staticmethod
    def ticker_from_message(message):
        text = str(message or "")
        if ":" in text:
            candidate = text.split(":", 1)[0].strip().upper()
            if candidate:
                return candidate
        return None

    @staticmethod
    def status_for(total, processed, issues, errors):
        if errors or any(issue.severity == "failed" for issue in issues):
            return "failed"
        if processed < total or issues:
            return "warning"
        return "passed"

    @staticmethod
    def progress(callback, total, processed, message):
        if callback:
            callback(
                {
                    "total_symbols": total,
                    "processed_symbols": processed,
                    "completion_rate": round((processed / total) * 100.0, 6) if total else 0.0,
                    "status_message": message,
                }
            )


def value(source, key, default=None):
    if source is None:
        return default
    if isinstance(source, dict):
        return source.get(key, default)
    return getattr(source, key, default)
