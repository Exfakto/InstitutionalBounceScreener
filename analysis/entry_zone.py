"""
Entry-zone classification utilities.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from analysis.score_result import ScoreResult


@dataclass(frozen=True)
class EntryZoneResult:
    """
    Pure v2.4 entry-zone output.
    """

    entry_label: str
    entry_score: float
    current_price: float | None
    ideal_entry_low: float | None
    ideal_entry_high: float | None
    acceptable_entry_low: float | None
    acceptable_entry_high: float | None
    distance_to_support_pct: float | None
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class EntryZoneCalculator:
    """
    Classify entry quality relative to the nearest support zone.

    These are v2.4 placeholder heuristics:
    - support zone through 2% above support high is the ideal entry band
    - 2% to 5% above support high is acceptable
    - 5% to 8% above support high is extended
    - more than 8% above support high is too late
    - strong support, bounce history, entry quality, and institutional score
      improve the score
    - high ATR, weak risk score, and larger support distance reduce the score
    """

    LABEL_IDEAL = "Ideal Entry"
    LABEL_ACCEPTABLE = "Acceptable Entry"
    LABEL_EXTENDED = "Extended"
    LABEL_TOO_LATE = "Too Late"
    LABEL_UNAVAILABLE = "Unavailable"

    def calculate(self, metrics):
        metrics = metrics or {}
        warnings = []
        price = self.metric(metrics, "current_price")
        support_low = self.metric(metrics, "nearest_support_low")
        support_high = self.metric(metrics, "nearest_support_high")
        support_mid = self.metric(metrics, "nearest_support_mid")

        if price is None or price <= 0:
            warnings.append("Missing current price")

        if support_low is None or support_high is None:
            warnings.append("Missing support zone")

        if warnings:
            return self.unavailable_result(price, warnings)

        if support_mid is None:
            support_mid = (support_low + support_high) / 2.0

        if support_low > support_high:
            support_low, support_high = support_high, support_low

        ideal_low = support_low
        ideal_high = support_high * 1.02
        acceptable_low = support_high * 1.02
        acceptable_high = support_high * 1.05
        distance_pct = self.distance_pct(price, support_low, support_high)
        label, base_score, reason = self.classify(price, support_low, support_high)
        reasons = [reason]
        score = base_score

        score += self.positive_adjustment(
            metrics,
            "support_strength_score",
            "Strong support strength improves entry quality",
            reasons,
        )
        score += self.positive_adjustment(
            metrics,
            "bounce_success_rate",
            "Strong bounce history improves entry quality",
            reasons,
        )
        score += self.positive_adjustment(
            metrics,
            "entry_quality_score",
            "Strong entry quality score confirms setup",
            reasons,
        )
        score += self.positive_adjustment(
            metrics,
            "institutional_bounce_score",
            "Strong institutional bounce score supports entry",
            reasons,
        )
        score += self.positive_adjustment(
            metrics,
            "opportunity_rating_score",
            "Strong opportunity rating supports entry",
            reasons,
            strong_at=85.0,
            moderate_at=70.0,
            strong_points=6.0,
            moderate_points=3.0,
        )

        score -= self.atr_penalty(metrics, reasons)
        score -= self.risk_penalty(metrics, reasons)
        score -= self.distance_penalty(distance_pct, reasons)

        return EntryZoneResult(
            entry_label=label,
            entry_score=self.clamp(score),
            current_price=price,
            ideal_entry_low=ideal_low,
            ideal_entry_high=ideal_high,
            acceptable_entry_low=acceptable_low,
            acceptable_entry_high=acceptable_high,
            distance_to_support_pct=distance_pct,
            reasons=reasons,
            warnings=[],
        )

    def classify(self, price, support_low, support_high):
        if support_low <= price <= support_high:
            return (
                self.LABEL_IDEAL,
                82.0,
                "Price is inside the validated support zone",
            )

        distance_above_high = ((price - support_high) / support_high) * 100.0

        if 0 <= distance_above_high <= 2.0:
            return (
                self.LABEL_IDEAL,
                78.0,
                "Price is within 2% above support",
            )

        if distance_above_high <= 5.0:
            return (
                self.LABEL_ACCEPTABLE,
                64.0,
                "Price is 2% to 5% above support",
            )

        if distance_above_high <= 8.0:
            return (
                self.LABEL_EXTENDED,
                42.0,
                "Price is 5% to 8% above support",
            )

        return (
            self.LABEL_TOO_LATE,
            20.0,
            "Price is more than 8% above support",
        )

    def positive_adjustment(
        self,
        metrics,
        name,
        reason,
        reasons,
        strong_at=80.0,
        moderate_at=70.0,
        strong_points=7.0,
        moderate_points=3.0,
    ):
        value = self.metric(metrics, name)

        if value is None:
            return 0.0

        if value >= strong_at:
            reasons.append(reason)
            return strong_points

        if value >= moderate_at:
            return moderate_points

        return 0.0

    def atr_penalty(self, metrics, reasons):
        atr_pct = self.metric(metrics, "atr_pct")

        if atr_pct is None:
            return 0.0

        if atr_pct >= 8.0:
            reasons.append("Very high ATR increases entry risk")
            return 18.0

        if atr_pct >= 5.0:
            reasons.append("Elevated ATR increases entry risk")
            return 9.0

        return 0.0

    def risk_penalty(self, metrics, reasons):
        risk_score = self.metric(metrics, "risk_score")

        if risk_score is None:
            return 0.0

        if risk_score < 40:
            reasons.append("Weak risk score reduces entry quality")
            return 14.0

        if risk_score < 55:
            reasons.append("Mixed risk score reduces entry quality")
            return 7.0

        return 0.0

    @staticmethod
    def distance_penalty(distance_pct, reasons):
        if distance_pct is None:
            return 0.0

        if distance_pct > 8.0:
            reasons.append("Distance to support is high")
            return min(20.0, (distance_pct - 8.0) * 2.0)

        if distance_pct > 5.0:
            return (distance_pct - 5.0) * 1.5

        return 0.0

    @staticmethod
    def distance_pct(price, support_low, support_high):
        if support_low <= price <= support_high:
            return 0.0

        if price > support_high:
            return ((price - support_high) / support_high) * 100.0

        return ((support_low - price) / support_low) * 100.0

    @staticmethod
    def metric(metrics, name):
        value = metrics.get(name)

        if isinstance(value, ScoreResult):
            value = value.value

        if value is None or value == "":
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def unavailable_result(current_price, warnings):
        return EntryZoneResult(
            entry_label=EntryZoneCalculator.LABEL_UNAVAILABLE,
            entry_score=0.0,
            current_price=current_price,
            ideal_entry_low=None,
            ideal_entry_high=None,
            acceptable_entry_low=None,
            acceptable_entry_high=None,
            distance_to_support_pct=None,
            reasons=[],
            warnings=warnings,
        )

    @staticmethod
    def clamp(value):
        return max(0.0, min(100.0, float(value)))
