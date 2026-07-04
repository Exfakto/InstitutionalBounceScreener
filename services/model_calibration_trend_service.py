from __future__ import annotations

from dataclasses import dataclass, field

from services.model_calibration_history_service import ModelCalibrationHistoryService


WINDOW_LIMITS = {
    "Last 10": 10,
    "Last 25": 25,
    "Last 50": 50,
    "All": None,
}


@dataclass(frozen=True)
class CalibrationTrendPoint:
    run_id: str
    timestamp: str
    overall_score: float | None = None
    precision: float | None = None
    recall: float | None = None
    f1_score: float | None = None
    confidence_calibration_error: float | None = None
    sample_size: int | None = None


@dataclass(frozen=True)
class CalibrationTrendSeries:
    points: list[CalibrationTrendPoint] = field(default_factory=list)
    window: str = "Last 25"
    insufficient_data: bool = False
    message: str = ""


class ModelCalibrationTrendService:
    """Prepare chart-ready calibration trend data from historical runs."""

    def __init__(self, history_service=None, repository=None):
        self.history_service = history_service or ModelCalibrationHistoryService(
            repository=repository
        )

    def get_trend(self, window="Last 25"):
        window = normalize_window(window)
        limit = WINDOW_LIMITS[window]
        history = self.history_service.get_history(limit=limit or 1000000)
        history = apply_window(history, limit)
        points = [self.to_point(item) for item in reversed(history)]
        insufficient = len(points) < 2
        return CalibrationTrendSeries(
            points=points,
            window=window,
            insufficient_data=insufficient,
            message="Insufficient historical data" if insufficient else "",
        )

    def to_point(self, item):
        metrics = value(item, "summary_metrics") or {}
        return CalibrationTrendPoint(
            run_id=str(value(item, "run_id") or ""),
            timestamp=str(value(item, "timestamp") or value(item, "completed_at") or value(item, "started_at") or ""),
            overall_score=number_or_none(
                first_existing(
                    value(item, "overall_score"),
                    value(metrics, "overall_score"),
                    value(metrics, "score"),
                )
            ),
            precision=number_or_none(
                first_existing(value(item, "precision"), value(metrics, "precision"))
            ),
            recall=number_or_none(
                first_existing(value(item, "recall"), value(metrics, "recall"))
            ),
            f1_score=number_or_none(
                first_existing(
                    value(item, "f1_score"),
                    value(item, "f1"),
                    value(metrics, "f1_score"),
                    value(metrics, "f1"),
                )
            ),
            confidence_calibration_error=number_or_none(
                first_existing(
                    value(item, "confidence_calibration_error"),
                    value(item, "calibration_error"),
                    value(metrics, "confidence_calibration_error"),
                    value(metrics, "calibration_error"),
                )
            ),
            sample_size=number_or_none(
                first_existing(
                    value(item, "sample_size"),
                    value(metrics, "sample_size"),
                    value(metrics, "signal_count"),
                    value(metrics, "outcome_count"),
                ),
                integer=True,
            ),
        )


def normalize_window(window):
    text = str(window or "Last 25")
    return text if text in WINDOW_LIMITS else "Last 25"


def apply_window(history, limit):
    rows = list(history or [])
    if limit is None:
        return rows
    return rows[:limit]


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


def number_or_none(raw, integer=False):
    try:
        number = float(raw)
    except (TypeError, ValueError):
        return None
    if integer:
        return int(number)
    return number
