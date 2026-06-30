"""
Pure v2.3 opportunity rating heuristics.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from analysis.score_result import ScoreResult


@dataclass(frozen=True)
class OpportunityRatingResult:
    """
    Structured decision-support output for an institutional bounce setup.
    """

    rating_score: float
    rating_label: str
    stars: int
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class OpportunityRatingCalculator:
    """
    Convert existing intelligence metrics into a simple opportunity rating.

    These are v2.3 placeholder heuristics:
    - available component scores are clamped to 0..100 and weighted
    - Gen 2 intelligence carries the largest weight when present
    - support, bounce, entry, relative strength, and trend improve the setup
    - high earnings risk and excessive distance above support reduce the setup
    - risk_score is treated as better when higher, matching the current
      score-provider convention of higher scores being more favorable
    """

    SCORE_WEIGHTS = {
        "institutional_bounce_score": 35,
        "support_score": 10,
        "bounce_score": 10,
        "entry_quality_score": 10,
        "relative_strength_score": 8,
        "trend_score": 7,
        "institutional_momentum_score": 5,
        "quality_score": 4,
        "institutional_score": 4,
        "technical_score": 3,
        "volume_score": 2,
        "risk_score": 2,
    }
    OPTIONAL_METRICS = [
        "earnings_risk_score",
        "distance_to_support_pct",
        "bounce_success_rate",
        "average_bounce_pct",
    ]

    def calculate(self, metrics):
        metrics = metrics or {}
        warnings = []
        strengths = []
        weaknesses = []

        base_score = self.weighted_score(metrics, warnings)

        if base_score is None:
            base_score = 0.0
            warnings.append("No valid opportunity score metrics available")

        adjustment = self.adjustment_score(metrics, warnings, strengths, weaknesses)
        rating_score = self.clamp(base_score + adjustment)

        self.add_component_notes(metrics, warnings, strengths, weaknesses)

        return OpportunityRatingResult(
            rating_score=rating_score,
            rating_label=self.rating_label(rating_score),
            stars=self.stars(rating_score),
            strengths=strengths,
            weaknesses=weaknesses,
            warnings=warnings,
        )

    def weighted_score(self, metrics, warnings):
        weighted_total = 0.0
        available_weight = 0.0

        for name, weight in self.SCORE_WEIGHTS.items():
            value = self.metric_value(metrics.get(name))

            if value is None:
                warnings.append(f"Missing metric: {name}")
                continue

            try:
                score = self.clamp(value)
            except (TypeError, ValueError):
                warnings.append(f"Invalid metric: {name}")
                continue

            weighted_total += score * weight
            available_weight += weight

        if available_weight <= 0:
            return None

        return weighted_total / available_weight

    def adjustment_score(self, metrics, warnings, strengths, weaknesses):
        adjustment = 0.0

        earnings_risk = self.safe_metric(
            metrics,
            "earnings_risk_score",
            warnings,
            warn_missing=False,
        )
        if earnings_risk is not None:
            if earnings_risk >= 85:
                adjustment -= 22
                weaknesses.append("Severe near-term earnings risk")
            elif earnings_risk >= 70:
                adjustment -= 15
                weaknesses.append("High near-term earnings risk")
            elif earnings_risk >= 50:
                adjustment -= 7
                weaknesses.append("Moderate earnings risk")
            elif earnings_risk <= 25:
                adjustment += 2
                strengths.append("Low earnings risk")

        distance = self.safe_metric(
            metrics,
            "distance_to_support_pct",
            warnings,
            warn_missing=False,
        )
        if distance is not None:
            if distance <= 3:
                adjustment += 4
                strengths.append("Price is close to support")
            elif distance <= 7:
                adjustment += 1
            elif distance > 10:
                penalty = min(25.0, (distance - 10.0) * 2.0)
                adjustment -= penalty
                weaknesses.append("Price is extended above support")

        bounce_success = self.safe_metric(
            metrics,
            "bounce_success_rate",
            warnings,
            warn_missing=False,
        )
        if bounce_success is not None:
            if bounce_success >= 80:
                adjustment += 4
                strengths.append("Strong historical bounce success rate")
            elif bounce_success < 50:
                adjustment -= 6
                weaknesses.append("Weak historical bounce success rate")

        average_bounce = self.safe_metric(
            metrics,
            "average_bounce_pct",
            warnings,
            warn_missing=False,
        )
        if average_bounce is not None:
            if average_bounce >= 8:
                adjustment += 3
                strengths.append("Strong average historical bounce")
            elif average_bounce < 3:
                adjustment -= 3
                weaknesses.append("Limited historical bounce magnitude")

        for name in self.OPTIONAL_METRICS:
            if name not in metrics or metrics.get(name) is None:
                warnings.append(f"Missing metric: {name}")

        return adjustment

    def add_component_notes(self, metrics, warnings, strengths, weaknesses):
        note_rules = [
            (
                "institutional_bounce_score",
                85,
                60,
                "Strong Gen 2 institutional bounce score",
                "Weak Gen 2 institutional bounce score",
            ),
            (
                "support_score",
                80,
                60,
                "Strong support quality",
                "Weak support quality",
            ),
            (
                "bounce_score",
                80,
                60,
                "Strong bounce validation",
                "Weak bounce validation",
            ),
            (
                "entry_quality_score",
                80,
                60,
                "Constructive entry quality",
                "Poor entry quality",
            ),
            (
                "relative_strength_score",
                75,
                50,
                "Strong relative strength",
                "Weak relative strength",
            ),
            (
                "trend_score",
                75,
                50,
                "Constructive trend",
                "Weak trend",
            ),
            (
                "risk_score",
                75,
                50,
                "Constructive risk profile",
                "Unfavorable risk profile",
            ),
        ]

        for name, strong_cutoff, weak_cutoff, strength, weakness in note_rules:
            value = self.safe_metric(metrics, name, warnings, warn_missing=False)

            if value is None:
                continue

            if value >= strong_cutoff:
                strengths.append(strength)
            elif value < weak_cutoff:
                weaknesses.append(weakness)

    def safe_metric(self, metrics, name, warnings, warn_missing=True):
        if name not in metrics or metrics.get(name) is None:
            if warn_missing:
                warnings.append(f"Missing metric: {name}")
            return None

        value = self.metric_value(metrics.get(name))

        try:
            return float(value)
        except (TypeError, ValueError):
            warnings.append(f"Invalid metric: {name}")
            return None

    @staticmethod
    def metric_value(value):
        if isinstance(value, ScoreResult):
            return value.value

        return value

    @staticmethod
    def clamp(value):
        return max(0.0, min(100.0, float(value)))

    @staticmethod
    def rating_label(score):
        if score >= 90:
            return "Elite Bounce"

        if score >= 80:
            return "High Probability"

        if score >= 70:
            return "Watch List"

        if score >= 60:
            return "Weak Setup"

        return "Avoid"

    @staticmethod
    def stars(score):
        if score >= 90:
            return 5

        if score >= 80:
            return 4

        if score >= 70:
            return 3

        if score >= 60:
            return 2

        return 1
