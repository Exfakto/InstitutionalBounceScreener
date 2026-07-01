"""
Upside target projection utilities.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from analysis.score_result import ScoreResult


@dataclass(frozen=True)
class TargetProjectionResult:
    """
    Pure v2.4 target projection output.
    """

    target_1: float | None
    target_2: float | None
    target_3: float | None
    expected_reward_pct: float | None
    conservative_reward_pct: float | None
    aggressive_reward_pct: float | None
    target_method: str
    confidence: str
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class TargetProjectionCalculator:
    """
    Calculate upside target projections from available bounce and ATR context.

    These are v2.4 placeholder heuristics:
    - target_1 uses median bounce percent when available, otherwise 1.5x ATR
    - target_2 uses average bounce percent when available, otherwise 2.5x ATR
    - target_3 uses the stronger historical bounce context, otherwise 4x ATR
    - resistance caps projected targets that would exceed known resistance
    - confidence rises with bounce validation, support strength, and
      institutional bounce score
    """

    METHOD_HISTORICAL = "Historical Bounce"
    METHOD_ATR = "ATR Fallback"
    METHOD_MIXED = "Mixed"
    METHOD_UNAVAILABLE = "Unavailable"

    def calculate(self, metrics):
        metrics = metrics or {}
        warnings = []
        reasons = []
        current_price = self.metric(metrics, "current_price")
        atr = self.metric(metrics, "atr")
        atr_pct = self.metric(metrics, "atr_pct")
        average_bounce_pct = self.metric(metrics, "average_bounce_pct")
        median_bounce_pct = self.metric(metrics, "median_bounce_pct")
        resistance_level = self.metric(metrics, "resistance_level")

        if current_price is None or current_price <= 0:
            warnings.append("Missing current price")
            return self.unavailable_result(warnings)

        if atr is None and atr_pct is not None:
            atr = current_price * (atr_pct / 100.0)

        has_bounce_data = (
            average_bounce_pct is not None
            or median_bounce_pct is not None
        )
        has_atr_data = atr is not None and atr > 0

        if not has_bounce_data:
            warnings.append("Missing bounce target data")

        if not has_atr_data:
            warnings.append("Missing ATR target data")

        if not has_bounce_data and not has_atr_data:
            return self.unavailable_result(warnings)

        target_1, method_1 = self.target_from_bounce_or_atr(
            current_price=current_price,
            bounce_pct=median_bounce_pct,
            atr=atr,
            atr_multiple=1.5,
        )
        target_2, method_2 = self.target_from_bounce_or_atr(
            current_price=current_price,
            bounce_pct=average_bounce_pct,
            atr=atr,
            atr_multiple=2.5,
        )
        target_3, method_3 = self.aggressive_target(
            current_price=current_price,
            average_bounce_pct=average_bounce_pct,
            median_bounce_pct=median_bounce_pct,
            atr=atr,
        )
        methods = {method_1, method_2, method_3}
        target_method = self.target_method(methods)

        if target_method == self.METHOD_HISTORICAL:
            reasons.append("Targets use historical bounce behavior")
        elif target_method == self.METHOD_ATR:
            reasons.append("Targets use ATR fallback projections")
        else:
            reasons.append("Targets combine historical bounce and ATR projections")

        target_1 = self.apply_resistance_cap(target_1, resistance_level, warnings)
        target_2 = self.apply_resistance_cap(target_2, resistance_level, warnings)
        target_3 = self.apply_resistance_cap(target_3, resistance_level, warnings)

        confidence = self.confidence(metrics, has_bounce_data, has_atr_data)

        return TargetProjectionResult(
            target_1=self.round_value(target_1),
            target_2=self.round_value(target_2),
            target_3=self.round_value(target_3),
            expected_reward_pct=self.round_value(
                self.reward_pct(current_price, target_2)
            ),
            conservative_reward_pct=self.round_value(
                self.reward_pct(current_price, target_1)
            ),
            aggressive_reward_pct=self.round_value(
                self.reward_pct(current_price, target_3)
            ),
            target_method=target_method,
            confidence=confidence,
            reasons=reasons,
            warnings=self.dedupe(warnings),
        )

    def target_from_bounce_or_atr(
        self,
        current_price,
        bounce_pct,
        atr,
        atr_multiple,
    ):
        if bounce_pct is not None:
            return (
                current_price * (1.0 + self.clamp_reward_pct(bounce_pct) / 100.0),
                self.METHOD_HISTORICAL,
            )

        return current_price + (atr * atr_multiple), self.METHOD_ATR

    def aggressive_target(
        self,
        current_price,
        average_bounce_pct,
        median_bounce_pct,
        atr,
    ):
        bounce_values = [
            value
            for value in [average_bounce_pct, median_bounce_pct]
            if value is not None
        ]

        if bounce_values:
            strongest_bounce = max(bounce_values) * 1.25
            return (
                current_price
                * (1.0 + self.clamp_reward_pct(strongest_bounce) / 100.0),
                self.METHOD_HISTORICAL,
            )

        return current_price + (atr * 4.0), self.METHOD_ATR

    def confidence(self, metrics, has_bounce_data, has_atr_data):
        if not has_bounce_data and not has_atr_data:
            return "Very Low"

        bounce_success = self.metric(metrics, "bounce_success_rate")
        support_strength = self.metric(metrics, "support_strength_score")
        institutional_score = self.metric(metrics, "institutional_bounce_score")
        opportunity_score = self.metric(metrics, "opportunity_rating_score")
        available_scores = [
            score
            for score in [
                bounce_success,
                support_strength,
                institutional_score,
                opportunity_score,
            ]
            if score is not None
        ]

        if not available_scores:
            return "Moderate" if has_bounce_data and has_atr_data else "Low"

        strong_count = sum(1 for score in available_scores if score >= 80.0)
        weak_count = sum(1 for score in available_scores if score < 50.0)

        if (
            bounce_success is not None
            and bounce_success >= 80.0
            and support_strength is not None
            and support_strength >= 80.0
            and institutional_score is not None
            and institutional_score >= 80.0
        ):
            return "Very High"

        if weak_count >= 2:
            return "Low"

        if strong_count >= 2 and has_bounce_data:
            return "High"

        if has_bounce_data or has_atr_data:
            return "Moderate"

        return "Very Low"

    @classmethod
    def target_method(cls, methods):
        if methods == {cls.METHOD_HISTORICAL}:
            return cls.METHOD_HISTORICAL

        if methods == {cls.METHOD_ATR}:
            return cls.METHOD_ATR

        return cls.METHOD_MIXED

    @staticmethod
    def apply_resistance_cap(target, resistance_level, warnings):
        if target is None or resistance_level is None:
            return target

        if resistance_level < target:
            warnings.append("Resistance capped projected target")
            return resistance_level

        return target

    @staticmethod
    def reward_pct(current_price, target):
        if current_price is None or current_price <= 0 or target is None:
            return None

        return max(0.0, ((target - current_price) / current_price) * 100.0)

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
    def clamp_reward_pct(value):
        return max(0.0, min(100.0, float(value)))

    @staticmethod
    def round_value(value):
        if value is None:
            return None

        return round(float(value), 6)

    @classmethod
    def unavailable_result(cls, warnings):
        return TargetProjectionResult(
            target_1=None,
            target_2=None,
            target_3=None,
            expected_reward_pct=None,
            conservative_reward_pct=None,
            aggressive_reward_pct=None,
            target_method=cls.METHOD_UNAVAILABLE,
            confidence="Very Low",
            reasons=[],
            warnings=cls.dedupe(warnings),
        )

    @staticmethod
    def dedupe(values):
        deduped = []

        for value in values:
            if value not in deduped:
                deduped.append(value)

        return deduped
