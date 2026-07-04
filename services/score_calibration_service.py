from __future__ import annotations

from dataclasses import dataclass, field
from math import sqrt

from services.strategy_validation_analytics_service import (
    RETURN_COLUMNS,
    GroupPerformanceSummary,
    StrategyValidationAnalyticsService,
)
from services.strategy_validation_repository import StrategyValidationRepository


SCORING_COMPONENTS = {
    "overall_score": ("score", "final_score", "overall_score"),
    "quality_score": ("quality_score",),
    "institutional_score": ("institutional_score",),
    "technical_score": ("technical_score",),
    "support_score": ("support_score",),
    "bounce_score": ("bounce_score",),
}

SCORE_BUCKETS = (
    ("90-100", 90.0, 100.0),
    ("80-89", 80.0, 89.999999),
    ("70-79", 70.0, 79.999999),
    ("below 70", float("-inf"), 69.999999),
)


@dataclass(frozen=True)
class CalibrationMetric:
    component: str
    correlations: dict[str, float] = field(default_factory=dict)
    bucket_summaries: dict[str, GroupPerformanceSummary] = field(default_factory=dict)
    sample_count: int = 0
    predictive_power: float = 0.0
    rank: int | None = None


@dataclass(frozen=True)
class CalibrationRecommendation:
    component: str
    action: str
    rationale: str
    predictive_power: float = 0.0


@dataclass(frozen=True)
class ScoreCalibrationReport:
    metrics: dict[str, CalibrationMetric] = field(default_factory=dict)
    ranked_components: list[CalibrationMetric] = field(default_factory=list)
    recommendations: list[CalibrationRecommendation] = field(default_factory=list)
    sample_count: int = 0


class ScoreCalibrationService:
    """
    Estimates scoring-factor predictive value from historical validation samples.
    """

    def __init__(
        self,
        repository=None,
        analytics_service=None,
        primary_horizon="20d",
    ):
        self.repository = repository or StrategyValidationRepository()
        self.analytics_service = analytics_service or StrategyValidationAnalyticsService(
            self.repository,
            primary_horizon=primary_horizon,
        )
        self.primary_horizon = self.analytics_service.normalize_horizon(primary_horizon)

    def calibrate(self, run_id=None, samples=None) -> ScoreCalibrationReport:
        rows = list(samples if samples is not None else self.load_samples(run_id))
        metrics = {
            component: self.component_metric(component, rows)
            for component in SCORING_COMPONENTS
        }
        ranked = self.rank_metrics(metrics.values())
        ranked_metrics = [
            CalibrationMetric(
                component=metric.component,
                correlations=metric.correlations,
                bucket_summaries=metric.bucket_summaries,
                sample_count=metric.sample_count,
                predictive_power=metric.predictive_power,
                rank=index + 1,
            )
            for index, metric in enumerate(ranked)
        ]
        ranked_by_component = {metric.component: metric for metric in ranked_metrics}
        return ScoreCalibrationReport(
            metrics={
                component: ranked_by_component.get(component, metric)
                for component, metric in metrics.items()
            },
            ranked_components=ranked_metrics,
            recommendations=[
                self.recommendation(metric)
                for metric in ranked_metrics
            ],
            sample_count=len(rows),
        )

    def load_samples(self, run_id=None):
        return self.repository.get_samples_by_date_range(run_id=run_id)

    def component_metric(self, component, rows) -> CalibrationMetric:
        pairs_by_horizon = {
            horizon: self.score_return_pairs(component, rows, horizon)
            for horizon in RETURN_COLUMNS
        }
        correlations = {
            horizon: self.correlation(pairs)
            for horizon, pairs in pairs_by_horizon.items()
        }
        primary_pairs = pairs_by_horizon[self.primary_horizon]
        predictive_power = max(
            (abs(value) for value in correlations.values()),
            default=0.0,
        )
        return CalibrationMetric(
            component=component,
            correlations=correlations,
            bucket_summaries=self.bucket_summaries(component, rows),
            sample_count=len(primary_pairs),
            predictive_power=predictive_power,
        )

    def bucket_summaries(self, component, rows):
        summaries = {}
        for label, low, high in SCORE_BUCKETS:
            bucket_rows = [
                row
                for row in (rows or [])
                if self.score_for_component(row, component) is not None
                and low <= self.score_for_component(row, component) <= high
            ]
            summaries[label] = self.analytics_service.group_summary(label, bucket_rows)
        return summaries

    def score_return_pairs(self, component, rows, horizon):
        column = RETURN_COLUMNS[self.analytics_service.normalize_horizon(horizon)]
        pairs = []
        for row in rows or []:
            score = self.score_for_component(row, component)
            return_value = self.number(self.value(row, column))
            if score is not None and return_value is not None:
                pairs.append((score, return_value))
        return pairs

    @classmethod
    def score_for_component(cls, row, component):
        for key in SCORING_COMPONENTS.get(component, (component,)):
            value = cls.number(cls.value(row, key))
            if value is not None:
                return value
        return None

    @staticmethod
    def rank_metrics(metrics):
        return sorted(
            metrics or [],
            key=lambda metric: (metric.predictive_power, metric.sample_count),
            reverse=True,
        )

    @staticmethod
    def recommendation(metric):
        if metric.sample_count == 0:
            return CalibrationRecommendation(
                component=metric.component,
                action="keep current weight",
                rationale="No completed validation samples are available.",
                predictive_power=metric.predictive_power,
            )
        if metric.predictive_power >= 0.25:
            return CalibrationRecommendation(
                component=metric.component,
                action="increase weight",
                rationale="Historical returns show meaningful positive or negative predictive relationship.",
                predictive_power=metric.predictive_power,
            )
        if metric.predictive_power <= 0.05:
            return CalibrationRecommendation(
                component=metric.component,
                action="decrease weight",
                rationale="Historical returns show little predictive relationship.",
                predictive_power=metric.predictive_power,
            )
        return CalibrationRecommendation(
            component=metric.component,
            action="keep current weight",
            rationale="Historical predictive relationship is present but not decisive.",
            predictive_power=metric.predictive_power,
        )

    @staticmethod
    def correlation(pairs):
        pairs = list(pairs or [])
        if len(pairs) < 2:
            return 0.0
        scores = [score for score, _ in pairs]
        returns = [return_value for _, return_value in pairs]
        score_mean = sum(scores) / len(scores)
        return_mean = sum(returns) / len(returns)
        numerator = sum(
            (score - score_mean) * (return_value - return_mean)
            for score, return_value in pairs
        )
        score_variance = sum((score - score_mean) ** 2 for score in scores)
        return_variance = sum(
            (return_value - return_mean) ** 2 for return_value in returns
        )
        denominator = sqrt(score_variance * return_variance)
        return numerator / denominator if denominator else 0.0

    @staticmethod
    def value(source, key):
        if source is None:
            return None
        if isinstance(source, dict):
            return source.get(key)
        return getattr(source, key, None)

    @staticmethod
    def number(value):
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
