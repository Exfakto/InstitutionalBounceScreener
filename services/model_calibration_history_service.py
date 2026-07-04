from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CalibrationHistoryItem:
    run_id: str
    timestamp: str
    model_version: str
    sample_size: int | None
    overall_score: float | None
    status: str
    summary: str = ""
    warnings: list[str] | None = None
    errors: list[str] | None = None


class ModelCalibrationHistoryService:
    """Read historical calibration runs from the existing calibration repository."""

    def __init__(self, repository=None):
        self.repository = repository

    def get_history(self, limit=25, offset=0):
        if self.repository is None or not hasattr(
            self.repository, "fetch_calibration_run_history"
        ):
            return []
        rows = self.repository.fetch_calibration_run_history(limit=limit, offset=offset)
        items = [self.to_history_item(row) for row in rows or []]
        return sorted(items, key=lambda item: item.timestamp or "", reverse=True)

    def get_run_details(self, run_id):
        if run_id in (None, "") or self.repository is None:
            return None
        row = None
        if hasattr(self.repository, "fetch_calibration_run"):
            row = self.repository.fetch_calibration_run(run_id)
        if row is None:
            return None
        return self.to_history_item(row)

    def to_history_item(self, row):
        summary = value(row, "summary")
        summary_metrics = value(row, "summary_metrics") or {}
        return CalibrationHistoryItem(
            run_id=str(value(row, "run_id") or ""),
            timestamp=str(value(row, "completed_at") or value(row, "started_at") or ""),
            model_version=str(
                first_existing(
                    value(row, "model_version"),
                    value(summary_metrics, "model_version"),
                    value(row, "source_validation_run_id"),
                    "N/A",
                )
            ),
            sample_size=number_or_none(
                first_existing(
                    value(row, "sample_size"),
                    value(summary_metrics, "sample_size"),
                    value(summary_metrics, "signal_count"),
                    value(summary_metrics, "outcome_count"),
                ),
                integer=True,
            ),
            overall_score=number_or_none(
                first_existing(
                    value(row, "overall_score"),
                    value(summary_metrics, "overall_score"),
                    value(summary_metrics, "score"),
                    value(summary_metrics, "expectancy"),
                )
            ),
            status=str(value(row, "status") or "UNKNOWN"),
            summary=str(summary or ""),
            warnings=list(value(row, "warnings") or []),
            errors=list(value(row, "errors") or []),
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


def number_or_none(raw, integer=False):
    try:
        number = float(raw)
    except (TypeError, ValueError):
        return None
    if integer:
        return int(number)
    return number
