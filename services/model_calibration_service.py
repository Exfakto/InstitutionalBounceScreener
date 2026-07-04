from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


MINIMUM_RECOMMENDED_SCORE = 70
SEVERE_DRAWDOWN_THRESHOLD = -12.0
WEAK_WIN_RATE_THRESHOLD = 0.45
WEAK_EXPECTANCY_THRESHOLD = 0.0
COMPONENT_SCORE_FIELDS = ("support", "bounce", "technical", "institutional")


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


class ModelCalibrationService:
    """Generate recommendation-only calibration reports from validation outputs."""

    def __init__(self, repository=None):
        self.repository = CalibrationRepository(repository)

    def calibrate(
        self,
        validation_result=None,
        signal_quality_report=None,
        run_id=None,
    ):
        started_at = now_utc()
        run_id = run_id or f"calibration-{uuid.uuid4().hex[:12]}"
        warnings = []
        errors = []
        recommendations = []

        source_validation_run_id = (
            value(validation_result, "run_id")
            or value(signal_quality_report, "validation_run_id")
        )
        source_signal_quality_run_id = value(signal_quality_report, "report_id")

        weak_groups = list(value(signal_quality_report, "weak_groups") or [])
        quality_recommendations = list(
            value(signal_quality_report, "recommendations") or []
        )
        factor_bucket_results = list(
            value(validation_result, "factor_bucket_results") or []
        )

        if value(signal_quality_report, "warnings"):
            warnings.extend(value(signal_quality_report, "warnings") or [])
        if value(validation_result, "warnings"):
            warnings.extend(value(validation_result, "warnings") or [])
        if value(validation_result, "errors"):
            errors.extend(value(validation_result, "errors") or [])

        recommendations.extend(
            self.recommendations_from_quality_hints(run_id, quality_recommendations)
        )
        recommendations.extend(self.recommendations_from_weak_groups(run_id, weak_groups))
        recommendations.extend(
            self.recommendations_from_factor_buckets(run_id, factor_bucket_results)
        )
        recommendations = self.dedupe_recommendations(recommendations)

        if not weak_groups and not quality_recommendations and not factor_bucket_results:
            warnings.append("No validation or signal-quality data available for calibration.")

        status = "COMPLETED" if recommendations else "NO_RECOMMENDATIONS"
        summary = self.summary_text(recommendations, warnings)
        run = CalibrationRun(
            run_id=run_id,
            started_at=started_at,
            completed_at=now_utc(),
            status=status,
            source_validation_run_id=source_validation_run_id,
            source_signal_quality_run_id=source_signal_quality_run_id,
            summary=summary,
            warnings=warnings,
            errors=errors,
        )
        saved_run = self.repository.save_run(run)
        saved_recommendations = self.repository.save_recommendations(
            run_id, recommendations
        )
        return {
            "run": saved_run or run,
            "recommendations": saved_recommendations or recommendations,
            "warnings": warnings,
            "errors": errors,
        }

    def recommendations_from_quality_hints(self, run_id, recommendations):
        converted = []
        for index, recommendation in enumerate(recommendations or [], start=1):
            field = value(recommendation, "field")
            category = self.category_for_field(field)
            if category is None:
                continue
            converted.append(
                CalibrationRecommendation(
                    recommendation_id=f"{run_id}-{category}-{index}",
                    run_id=run_id,
                    category=category,
                    current_value=value(recommendation, "current_value"),
                    recommended_value=value(recommendation, "recommended_value"),
                    rationale=value(recommendation, "reason") or "Signal quality analysis recommended a calibration review.",
                    expected_impact=self.expected_impact_for_category(category),
                    confidence=self.confidence_from_severity(
                        value(recommendation, "severity")
                    ),
                )
            )
        return converted

    def recommendations_from_weak_groups(self, run_id, weak_groups):
        recommendations = []
        weak_groups = [group for group in (weak_groups or []) if bool(value(group, "weak", True))]
        if not weak_groups:
            return recommendations

        if self.has_dimension(weak_groups, "final_score_bucket"):
            recommendations.append(
                self.recommendation(
                    run_id,
                    "minimum_final_score",
                    MINIMUM_RECOMMENDED_SCORE,
                    "Weak final-score buckets underperformed validation targets.",
                    weak_groups,
                )
            )
        for component in COMPONENT_SCORE_FIELDS:
            dimension = f"{component}_score_bucket"
            if self.has_dimension(weak_groups, dimension):
                recommendations.append(
                    self.recommendation(
                        run_id,
                        f"minimum_{component}_score",
                        MINIMUM_RECOMMENDED_SCORE,
                        f"Weak {component} score buckets underperformed validation targets.",
                        [group for group in weak_groups if value(group, "dimension") == dimension],
                    )
                )
        if any(
            str(value(group, "dimension")) == "confidence_level"
            and str(value(group, "group")).upper() in {"LOW", "UNKNOWN"}
            for group in weak_groups
        ):
            recommendations.append(
                self.recommendation(
                    run_id,
                    "confidence_filtering_rules",
                    "Require MEDIUM or HIGH confidence",
                    "Low or unknown confidence groups showed poor validation performance.",
                    weak_groups,
                    current_value="Allow LOW/UNKNOWN",
                    confidence="HIGH",
                )
            )
        if any(str(value(group, "dimension")) == "grade" for group in weak_groups):
            recommendations.append(
                self.recommendation(
                    run_id,
                    "minimum_final_score",
                    MINIMUM_RECOMMENDED_SCORE,
                    "Poor-performing grades indicate the minimum final score should be reviewed.",
                    [group for group in weak_groups if value(group, "dimension") == "grade"],
                )
            )
        if any(
            safe_float(value(group, "max_drawdown"), 0.0) <= SEVERE_DRAWDOWN_THRESHOLD
            for group in weak_groups
        ):
            recommendations.append(
                self.recommendation(
                    run_id,
                    "confidence_filtering_rules",
                    "Tighten confidence and rejection filters for high-drawdown groups",
                    "Some validation groups showed excessive drawdown.",
                    weak_groups,
                    current_value="Current confidence filters",
                    confidence="MEDIUM",
                )
            )
        return recommendations

    def recommendations_from_factor_buckets(self, run_id, factor_bucket_results):
        recommendations = []
        weak_buckets = [
            bucket for bucket in (factor_bucket_results or [])
            if self.bucket_is_weak(bucket)
        ]
        if not weak_buckets:
            return recommendations

        if any(str(value(bucket, "factor")) == "final_score" for bucket in weak_buckets):
            recommendations.append(
                self.recommendation(
                    run_id,
                    "minimum_final_score",
                    MINIMUM_RECOMMENDED_SCORE,
                    "Validation factor buckets show weak lower final-score performance.",
                    weak_buckets,
                )
            )
        for component in COMPONENT_SCORE_FIELDS:
            if any(
                str(value(bucket, "factor")) in {component, f"{component}_score"}
                for bucket in weak_buckets
            ):
                recommendations.append(
                    self.recommendation(
                        run_id,
                        f"minimum_{component}_score",
                        MINIMUM_RECOMMENDED_SCORE,
                        f"Validation factor buckets show weak {component} score performance.",
                        [
                            bucket for bucket in weak_buckets
                            if str(value(bucket, "factor")) in {component, f"{component}_score"}
                        ],
                    )
                )
        return recommendations

    def recommendation(
        self,
        run_id,
        category,
        recommended_value,
        rationale,
        evidence,
        current_value=None,
        confidence=None,
    ):
        evidence_label = self.evidence_label(evidence)
        return CalibrationRecommendation(
            recommendation_id=f"{run_id}-{category}",
            run_id=run_id,
            category=category,
            current_value=current_value,
            recommended_value=recommended_value,
            rationale=f"{rationale} Evidence: {evidence_label}",
            expected_impact=self.expected_impact_for_category(category),
            confidence=confidence or self.confidence_from_evidence(evidence),
        )

    @staticmethod
    def category_for_field(field):
        mapping = {
            "minimum_final_score": "minimum_final_score",
            "minimum_support_score": "minimum_support_score",
            "minimum_bounce_score": "minimum_bounce_score",
            "minimum_technical_score": "minimum_technical_score",
            "minimum_institutional_score": "minimum_institutional_score",
            "confidence_requirement": "confidence_filtering_rules",
        }
        return mapping.get(str(field or ""))

    @staticmethod
    def expected_impact_for_category(category):
        if category == "minimum_final_score":
            return "Reduce weak low-score candidates before ranking."
        if category == "confidence_filtering_rules":
            return "Reduce low-conviction and high-drawdown signals."
        if str(category).startswith("minimum_"):
            component = str(category).replace("minimum_", "").replace("_score", "")
            return f"Improve candidate quality by filtering weak {component} setups."
        return "Improve calibration review quality."

    @staticmethod
    def confidence_from_severity(severity):
        severity = str(severity or "").upper()
        if severity == "HIGH":
            return "HIGH"
        if severity == "LOW":
            return "LOW"
        return "MEDIUM"

    @staticmethod
    def confidence_from_evidence(evidence):
        items = list(evidence or [])
        total_signals = sum(int(safe_float(value(item, "signal_count"), 0)) for item in items)
        severe_drawdown = any(
            safe_float(value(item, "max_drawdown"), 0.0) <= SEVERE_DRAWDOWN_THRESHOLD
            for item in items
        )
        if total_signals >= 10 or severe_drawdown:
            return "HIGH"
        if total_signals >= 3:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def has_dimension(groups, dimension):
        return any(str(value(group, "dimension")) == dimension for group in groups or [])

    @staticmethod
    def bucket_is_weak(bucket):
        return (
            safe_float(value(bucket, "win_rate"), 1.0) < WEAK_WIN_RATE_THRESHOLD
            or safe_float(value(bucket, "expectancy"), 1.0) < WEAK_EXPECTANCY_THRESHOLD
            or safe_float(value(bucket, "max_drawdown"), 0.0) <= SEVERE_DRAWDOWN_THRESHOLD
        )

    @staticmethod
    def evidence_label(evidence):
        labels = []
        for item in evidence or []:
            dimension = value(item, "dimension") or value(item, "factor") or "group"
            group = value(item, "group") or value(item, "bucket") or "unknown"
            labels.append(f"{dimension}:{group}")
        return ", ".join(labels) if labels else "validation underperformance"

    @staticmethod
    def summary_text(recommendations, warnings):
        if recommendations:
            return f"Generated {len(recommendations)} calibration recommendation(s)."
        if warnings:
            return "No calibration recommendations generated; warnings require review."
        return "No calibration recommendations generated."

    @staticmethod
    def dedupe_recommendations(recommendations):
        deduped = {}
        for recommendation in recommendations or []:
            category = recommendation.category
            existing = deduped.get(category)
            if existing is None:
                deduped[category] = recommendation
                continue
            deduped[category] = higher_confidence(existing, recommendation)
        return list(deduped.values())


def higher_confidence(left, right):
    rank = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
    if rank.get(str(right.confidence).upper(), 1) > rank.get(str(left.confidence).upper(), 1):
        return right
    return left


def now_utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def value(source, key, default=None):
    if source is None:
        return default
    if isinstance(source, dict):
        return source.get(key, default)
    return getattr(source, key, default)


def safe_float(raw, default=None):
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default
