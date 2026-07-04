from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CalibrationRun:
    run_id: str
    started_at: str
    completed_at: str | None = None
    status: str = "STARTED"
    source_validation_run_id: str | None = None
    source_signal_quality_run_id: str | None = None
    summary: str = ""
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CalibrationRecommendation:
    recommendation_id: str
    run_id: str
    category: str
    current_value: Any = None
    recommended_value: Any = None
    rationale: str = ""
    expected_impact: str = ""
    confidence: str = "UNKNOWN"


class CalibrationRepository:
    """Thin typed wrapper around the database manager calibration methods."""

    def __init__(self, repository):
        self.repository = repository

    def save_run(self, run):
        if self.repository is None or not hasattr(self.repository, "save_calibration_run"):
            return None
        return self.repository.save_calibration_run(run)

    def save_recommendations(self, run_id, recommendations):
        if self.repository is None or not hasattr(
            self.repository, "save_calibration_recommendations"
        ):
            return []
        return self.repository.save_calibration_recommendations(run_id, recommendations)

    def fetch_latest_run(self):
        if self.repository is None or not hasattr(
            self.repository, "fetch_latest_calibration_run"
        ):
            return None
        return self.repository.fetch_latest_calibration_run()

    def fetch_recommendations(self, run_id):
        if self.repository is None or not hasattr(
            self.repository, "fetch_calibration_recommendations"
        ):
            return []
        return self.repository.fetch_calibration_recommendations(run_id)

    def fetch_run_history(self, limit=25, offset=0):
        if self.repository is None or not hasattr(
            self.repository, "fetch_calibration_run_history"
        ):
            return []
        return self.repository.fetch_calibration_run_history(limit=limit, offset=offset)

    def clear_run(self, run_id):
        if self.repository is None or not hasattr(self.repository, "clear_calibration_run"):
            return 0
        return self.repository.clear_calibration_run(run_id)
