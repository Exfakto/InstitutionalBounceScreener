from __future__ import annotations

from dataclasses import dataclass, field

from services.model_calibration_history_service import ModelCalibrationHistoryService


HIGHER_IS_BETTER = {
    "overall_score": True,
    "precision": True,
    "recall": True,
    "f1_score": True,
    "confidence_calibration_error": False,
    "sample_size": True,
}

METRIC_LABELS = {
    "overall_score": "Overall Score",
    "precision": "Precision",
    "recall": "Recall",
    "f1_score": "F1 Score",
    "confidence_calibration_error": "Confidence Calibration Error",
    "sample_size": "Sample Size",
    "status": "Status",
}


@dataclass(frozen=True)
class CalibrationMetricComparison:
    metric: str
    label: str
    base_value: object = None
    comparison_value: object = None
    delta: float | None = None
    percent_delta: float | None = None
    classification: str = "unchanged"


@dataclass(frozen=True)
class CalibrationRunComparison:
    base_run_id: str | None
    comparison_run_id: str | None
    base_timestamp: str | None = None
    comparison_timestamp: str | None = None
    metrics: list[CalibrationMetricComparison] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    missing_run: bool = False


class ModelCalibrationComparisonService:
    """Compare two historical calibration runs without mutating calibration settings."""

    def __init__(self, history_service=None, repository=None):
        self.history_service = history_service or ModelCalibrationHistoryService(
            repository=repository
        )

    def compare_runs(self, base_run_id, comparison_run_id):
        warnings = []
        base = self.history_service.get_run_details(base_run_id)
        comparison = self.history_service.get_run_details(comparison_run_id)
        if base is None:
            warnings.append(f"Calibration run not found: {base_run_id}")
        if comparison is None:
            warnings.append(f"Calibration run not found: {comparison_run_id}")
        if base is None or comparison is None:
            return CalibrationRunComparison(
                base_run_id=base_run_id,
                comparison_run_id=comparison_run_id,
                warnings=warnings,
                missing_run=True,
            )

        metrics = [
            self.compare_numeric_metric(base, comparison, "overall_score"),
            self.compare_numeric_metric(base, comparison, "precision"),
            self.compare_numeric_metric(base, comparison, "recall"),
            self.compare_numeric_metric(base, comparison, "f1_score"),
            self.compare_numeric_metric(
                base, comparison, "confidence_calibration_error"
            ),
            self.compare_numeric_metric(base, comparison, "sample_size"),
            self.compare_status(base, comparison),
        ]
        return CalibrationRunComparison(
            base_run_id=value(base, "run_id"),
            comparison_run_id=value(comparison, "run_id"),
            base_timestamp=timestamp_for(base),
            comparison_timestamp=timestamp_for(comparison),
            metrics=metrics,
            warnings=warnings,
            missing_run=False,
        )

    def compare_numeric_metric(self, base, comparison, metric):
        base_value = metric_value(base, metric)
        comparison_value = metric_value(comparison, metric)
        if base_value is None or comparison_value is None:
            return CalibrationMetricComparison(
                metric=metric,
                label=METRIC_LABELS[metric],
                base_value=base_value,
                comparison_value=comparison_value,
                classification="unchanged",
            )
        delta = comparison_value - base_value
        percent_delta = None
        if base_value not in (None, 0):
            percent_delta = (delta / abs(base_value)) * 100.0
        classification = classify_delta(delta, higher_is_better=HIGHER_IS_BETTER[metric])
        return CalibrationMetricComparison(
            metric=metric,
            label=METRIC_LABELS[metric],
            base_value=base_value,
            comparison_value=comparison_value,
            delta=delta,
            percent_delta=percent_delta,
            classification=classification,
        )

    @staticmethod
    def compare_status(base, comparison):
        base_status = value(base, "status") or "UNKNOWN"
        comparison_status = value(comparison, "status") or "UNKNOWN"
        classification = "unchanged" if base_status == comparison_status else "changed"
        return CalibrationMetricComparison(
            metric="status",
            label=METRIC_LABELS["status"],
            base_value=base_status,
            comparison_value=comparison_status,
            classification=classification,
        )


def metric_value(source, metric):
    if metric == "sample_size":
        return number_or_none(
            first_existing(
                value(source, "sample_size"),
                value(value(source, "summary_metrics") or {}, "sample_size"),
                value(value(source, "summary_metrics") or {}, "signal_count"),
                value(value(source, "summary_metrics") or {}, "outcome_count"),
            )
        )
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
    }
    candidates = [value(source, key) for key in aliases.get(metric, (metric,))]
    candidates.extend(value(metrics, key) for key in aliases.get(metric, (metric,)))
    return number_or_none(first_existing(*candidates))


def classify_delta(delta, higher_is_better=True):
    if abs(delta or 0.0) < 1e-12:
        return "unchanged"
    if higher_is_better:
        return "improved" if delta > 0 else "regressed"
    return "improved" if delta < 0 else "regressed"


def timestamp_for(source):
    return first_existing(
        value(source, "timestamp"),
        value(source, "completed_at"),
        value(source, "started_at"),
    )


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
