from __future__ import annotations

from dataclasses import dataclass, field

from services.model_calibration_history_service import ModelCalibrationHistoryService


DEFAULT_TOLERANCES = {
    "overall_score": 0.0,
    "precision": 0.0,
    "recall": 0.0,
    "f1_score": 0.0,
    "confidence_calibration_error": 0.0,
    "sample_size": 0.0,
}
LOWER_IS_BETTER = {"confidence_calibration_error"}


@dataclass(frozen=True)
class CalibrationValidationMetric:
    metric: str
    before: float | None = None
    after: float | None = None
    delta: float | None = None
    regressed: bool = False


@dataclass(frozen=True)
class CalibrationValidationResult:
    status: str
    before_settings: dict = field(default_factory=dict)
    after_settings: dict = field(default_factory=dict)
    metrics: list[CalibrationValidationMetric] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    promotion_blocked: bool = False
    message: str = ""


class ModelCalibrationValidationService:
    """Validate calibration changes against historical calibration metrics."""

    def __init__(self, history_service=None, repository=None, tolerances=None):
        self.history_service = history_service or ModelCalibrationHistoryService(
            repository=repository
        )
        self.tolerances = dict(DEFAULT_TOLERANCES)
        if isinstance(tolerances, dict):
            self.tolerances.update(tolerances)

    def validate_changes(self, current_settings=None, proposed_settings=None):
        current_settings = dict(current_settings or {})
        proposed_settings = dict(proposed_settings or {})
        warnings = []
        errors = []

        if not proposed_settings:
            warnings.append("No proposed calibration settings supplied.")

        history = self.history_service.get_history(limit=2)
        if len(history) < 2:
            warnings.append("Insufficient historical calibration data for validation.")
            return CalibrationValidationResult(
                status="warning",
                before_settings=current_settings,
                after_settings=proposed_settings,
                warnings=warnings,
                promotion_blocked=False,
                message="Calibration validation completed with warnings.",
            )

        before_run = history[1]
        after_run = history[0]
        metrics = [self.compare_metric(before_run, after_run, metric) for metric in DEFAULT_TOLERANCES]
        regressions = [metric for metric in metrics if metric.regressed]
        if regressions:
            errors.extend(
                f"{metric.metric} regressed by {metric.delta:.4f}"
                for metric in regressions
                if metric.delta is not None
            )
            status = "failed"
        elif warnings:
            status = "warning"
        else:
            status = "passed"

        return CalibrationValidationResult(
            status=status,
            before_settings=current_settings,
            after_settings=proposed_settings,
            metrics=metrics,
            warnings=warnings,
            errors=errors,
            promotion_blocked=status == "failed",
            message=self.message_for(status),
        )

    def compare_metric(self, before_run, after_run, metric):
        before = metric_value(before_run, metric)
        after = metric_value(after_run, metric)
        if before is None or after is None:
            return CalibrationValidationMetric(metric=metric, before=before, after=after)
        delta = after - before
        tolerance = float(self.tolerances.get(metric, 0.0))
        if metric in LOWER_IS_BETTER:
            regressed = delta > tolerance
        else:
            regressed = delta < -tolerance
        return CalibrationValidationMetric(
            metric=metric,
            before=before,
            after=after,
            delta=delta,
            regressed=regressed,
        )

    @staticmethod
    def message_for(status):
        if status == "passed":
            return "Calibration validation passed."
        if status == "failed":
            return "Calibration validation failed; promotion is blocked."
        return "Calibration validation completed with warnings."


def metric_value(source, metric):
    metrics = value(source, "summary_metrics") or {}
    aliases = {
        "overall_score": ("overall_score", "score"),
        "precision": ("precision",),
        "recall": ("recall",),
        "f1_score": ("f1_score", "f1"),
        "confidence_calibration_error": (
            "confidence_calibration_error",
            "calibration_error",
        ),
        "sample_size": ("sample_size", "signal_count", "outcome_count"),
    }
    candidates = [value(source, key) for key in aliases.get(metric, (metric,))]
    candidates.extend(value(metrics, key) for key in aliases.get(metric, (metric,)))
    return number_or_none(first_existing(*candidates))


def value(source, key, default=None):
    if source is None:
        return default
    if isinstance(source, dict):
        return source.get(key, default)
    return getattr(source, key, default)


def first_existing(*values):
    for item in values:
        if item not in (None, ""):
            return item
    return None


def number_or_none(raw):
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None
