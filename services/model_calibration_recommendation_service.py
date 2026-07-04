from __future__ import annotations

from dataclasses import dataclass


SEVERITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "UNKNOWN": 3}


@dataclass(frozen=True)
class CalibrationRecommendationView:
    title: str
    severity: str
    recommended_action: str
    reason: str
    related_metric: str
    timestamp: str | None = None
    recommendation_id: str | None = None
    run_id: str | None = None


class ModelCalibrationRecommendationService:
    """Read-only service for UI-ready calibration recommendations."""

    def __init__(self, repository=None):
        self.repository = repository

    def get_recommendations(self, run_id=None):
        if self.repository is None:
            return []

        selected_run_id = str(run_id).strip() if run_id not in (None, "") else None
        run = None
        if selected_run_id is None and hasattr(self.repository, "fetch_latest_calibration_run"):
            run = self.repository.fetch_latest_calibration_run()
            selected_run_id = value(run, "run_id")

        if selected_run_id in (None, ""):
            return []

        if hasattr(self.repository, "fetch_calibration_recommendations"):
            recommendations = self.repository.fetch_calibration_recommendations(
                selected_run_id
            )
        else:
            recommendations = value(run, "recommendations") or []

        timestamp = value(run, "completed_at") or value(run, "started_at")
        views = [
            self.to_view(recommendation, fallback_timestamp=timestamp)
            for recommendation in recommendations or []
        ]
        return sorted(views, key=self.sort_key)

    def to_view(self, recommendation, fallback_timestamp=None):
        category = value(recommendation, "category") or value(
            recommendation, "field", "recommendation"
        )
        severity = normalize_severity(
            value(recommendation, "severity")
            or value(recommendation, "confidence")
            or "UNKNOWN"
        )
        return CalibrationRecommendationView(
            title=title_for_category(category),
            severity=severity,
            recommended_action=format_action(
                value(recommendation, "recommended_action")
                or value(recommendation, "recommended_value")
            ),
            reason=str(
                value(recommendation, "reason")
                or value(recommendation, "rationale")
                or "No rationale provided."
            ),
            related_metric=str(category or "N/A"),
            timestamp=value(recommendation, "timestamp")
            or value(recommendation, "created_at")
            or fallback_timestamp,
            recommendation_id=value(recommendation, "recommendation_id"),
            run_id=value(recommendation, "run_id"),
        )

    @staticmethod
    def sort_key(recommendation):
        severity_rank = SEVERITY_ORDER.get(recommendation.severity, SEVERITY_ORDER["UNKNOWN"])
        timestamp = recommendation.timestamp or ""
        return (severity_rank, reverse_text(timestamp), recommendation.title)

    @staticmethod
    def to_export_rows(recommendations):
        return [recommendation_to_dict(item) for item in recommendations or []]


def normalize_severity(raw):
    severity = str(raw or "UNKNOWN").upper()
    if severity in {"CRITICAL", "HIGH"}:
        return "HIGH"
    if severity in {"MEDIUM", "MODERATE"}:
        return "MEDIUM"
    if severity == "LOW":
        return "LOW"
    return "UNKNOWN"


def title_for_category(category):
    text = str(category or "recommendation").replace("_", " ").strip()
    return text.title() if text else "Calibration Recommendation"


def format_action(action):
    if action in (None, ""):
        return "N/A"
    if isinstance(action, dict):
        return ", ".join(f"{key}: {value}" for key, value in action.items())
    if isinstance(action, (list, tuple)):
        return ", ".join(str(item) for item in action)
    return str(action)


def recommendation_to_dict(recommendation):
    return {
        "title": value(recommendation, "title") or "Calibration Recommendation",
        "severity": value(recommendation, "severity") or "UNKNOWN",
        "recommended_action": value(recommendation, "recommended_action") or "N/A",
        "reason": value(recommendation, "reason") or "No rationale provided.",
        "related_metric": value(recommendation, "related_metric") or "N/A",
        "timestamp": value(recommendation, "timestamp"),
    }


def value(source, key, default=None):
    if source is None:
        return default
    if isinstance(source, dict):
        return source.get(key, default)
    return getattr(source, key, default)


def reverse_text(text):
    # Provides deterministic descending timestamp sorting without date parsing.
    return "".join(chr(0x10FFFF - ord(char)) for char in str(text))
