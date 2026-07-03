"""
Composite scoring for institutional bounce setups.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite


SUPPORT_QUALITY_WEIGHT = 0.30
BOUNCE_HISTORY_WEIGHT = 0.25
TECHNICAL_CONFIRMATION_WEIGHT = 0.20
INSTITUTIONAL_STRENGTH_WEIGHT = 0.25

DEFAULT_COMPONENT_SCORE = 50.0


@dataclass(frozen=True)
class BounceCompositeScoreResult:
    ticker: str | None
    final_score: float
    support_score: float
    bounce_score: float
    technical_score: float
    institutional_score: float
    confidence_level: str
    explanation: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class BounceCompositeScoringEngine:
    """
    Combine support, bounce, technical, and institutional outputs into one score.
    """

    def score(
        self,
        ticker=None,
        support=None,
        bounce=None,
        technical=None,
        institutional=None,
    ):
        warnings = []
        explanation = []

        normalized_ticker = self.first_existing(
            ticker,
            self.value(support, "ticker"),
            self.value(self.value(support, "primary_zone"), "ticker"),
            self.value(bounce, "ticker"),
            self.value(technical, "ticker"),
            self.value(institutional, "ticker"),
        )

        support_score = self.support_score(support, warnings, explanation)
        bounce_score = self.bounce_score(bounce, warnings, explanation)
        technical_score = self.technical_score(technical, warnings, explanation)
        institutional_score = self.institutional_score(
            institutional,
            warnings,
            explanation,
        )

        final_score = self.clamp(
            support_score * SUPPORT_QUALITY_WEIGHT
            + bounce_score * BOUNCE_HISTORY_WEIGHT
            + technical_score * TECHNICAL_CONFIRMATION_WEIGHT
            + institutional_score * INSTITUTIONAL_STRENGTH_WEIGHT
        )

        confidence_level = self.confidence_level(final_score, warnings)

        return BounceCompositeScoreResult(
            ticker=normalized_ticker,
            final_score=round(final_score, 2),
            support_score=round(support_score, 2),
            bounce_score=round(bounce_score, 2),
            technical_score=round(technical_score, 2),
            institutional_score=round(institutional_score, 2),
            confidence_level=confidence_level,
            explanation=explanation,
            warnings=self.unique_warnings(warnings),
        )

    def support_score(self, support, warnings, explanation):
        if support is None:
            warnings.append("Missing support data")
            explanation.append("Support quality is unavailable; using neutral score.")
            return DEFAULT_COMPONENT_SCORE

        zone = self.value(support, "primary_zone") or support
        strength = self.number(
            self.first_existing(
                self.value(zone, "support_strength_score"),
                self.value(zone, "strength_score"),
                self.value(zone, "support_score"),
            )
        )
        confidence = self.number(self.value(zone, "confidence_score"))

        if strength is None and confidence is None:
            warnings.append("Missing support score")
            explanation.append("Support quality is unavailable; using neutral score.")
            return DEFAULT_COMPONENT_SCORE

        score = self.average_present([strength, confidence])
        touch_count = self.number(self.value(zone, "touch_count"))
        if touch_count is not None and touch_count >= 4:
            score += 5

        if score >= 75:
            explanation.append("Support quality is strong with repeatable zone confirmation.")
        elif score >= 55:
            explanation.append("Support quality is average and needs confirmation.")
        else:
            explanation.append("Support quality is weak.")
        self.extend_warnings(warnings, self.value(support, "warnings"))
        return self.clamp(score)

    def bounce_score(self, bounce, warnings, explanation):
        result = self.primary_bounce_result(bounce)
        if result is None:
            warnings.append("Missing bounce history")
            explanation.append("Bounce history is unavailable; using neutral score.")
            return DEFAULT_COMPONENT_SCORE

        success_rate = self.number(self.value(result, "bounce_success_rate"))
        average_bounce = self.number(self.value(result, "average_bounce_pct"))
        largest_bounce = self.number(self.value(result, "largest_bounce_pct"))
        tests = self.number(self.value(result, "total_support_tests"))
        failed_breaks = self.number(self.value(result, "failed_support_breaks")) or 0

        if success_rate is None and average_bounce is None and largest_bounce is None:
            warnings.append("Missing bounce metrics")
            explanation.append("Bounce history metrics are unavailable; using neutral score.")
            return DEFAULT_COMPONENT_SCORE

        success_score = self.clamp(success_rate if success_rate is not None else 50)
        average_score = self.clamp((average_bounce or 0) * 4)
        largest_score = self.clamp((largest_bounce or 0) * 2)
        score = success_score * 0.55 + average_score * 0.30 + largest_score * 0.15

        if tests is not None and tests >= 4:
            score += 5
        score -= min(20.0, failed_breaks * 7.5)

        if score >= 75:
            explanation.append("Historical bounce behavior is favorable.")
        elif score >= 55:
            explanation.append("Historical bounce behavior is average.")
        else:
            explanation.append("Historical bounce behavior is weak.")
        self.extend_warnings(warnings, self.value(result, "warnings"))
        return self.clamp(score)

    def technical_score(self, technical, warnings, explanation):
        if technical is None:
            warnings.append("Missing technical data")
            explanation.append("Technical confirmation is unavailable; using neutral score.")
            return DEFAULT_COMPONENT_SCORE

        close = self.number(self.value(technical, "close"))
        ema20 = self.number(self.value(technical, "ema20"))
        ema50 = self.number(self.value(technical, "ema50"))
        ema200 = self.number(self.value(technical, "ema200"))
        rsi = self.number(self.value(technical, "rsi14"))
        macd_histogram = self.number(self.value(technical, "macd_histogram"))
        relative_volume = self.number(self.value(technical, "relative_volume"))

        components = []
        trend_values = [ema for ema in (ema20, ema50, ema200) if close is not None and ema is not None]
        if trend_values:
            above_count = sum(1 for ema in trend_values if close >= ema)
            components.append(above_count / len(trend_values) * 100)
        if rsi is not None:
            components.append(self.rsi_score(rsi))
        if macd_histogram is not None:
            components.append(75.0 if macd_histogram > 0 else 35.0 if macd_histogram < 0 else 50.0)
        if relative_volume is not None:
            components.append(self.clamp(relative_volume * 50))

        if not components:
            warnings.append("Missing technical metrics")
            explanation.append("Technical confirmation metrics are unavailable; using neutral score.")
            return DEFAULT_COMPONENT_SCORE

        score = sum(components) / len(components)
        if score >= 75:
            explanation.append("Technical confirmation is strong.")
        elif score >= 55:
            explanation.append("Technical confirmation is constructive but mixed.")
        else:
            explanation.append("Technical confirmation is weak.")
        self.extend_warnings(warnings, self.value(technical, "warnings"))
        return self.clamp(score)

    def institutional_score(self, institutional, warnings, explanation):
        if institutional is None:
            warnings.append("Missing institutional data")
            explanation.append("Institutional strength is unavailable; using neutral score.")
            return DEFAULT_COMPONENT_SCORE

        score_result = self.value(institutional, "score_result") or institutional
        score = self.number(
            self.first_existing(
                self.value(score_result, "overall_institutional_strength_score"),
                self.value(score_result, "institutional_score"),
                self.value(score_result, "institutional_strength_score"),
            )
        )
        if score is None:
            warnings.append("Missing institutional score")
            explanation.append("Institutional strength score is unavailable; using neutral score.")
            return DEFAULT_COMPONENT_SCORE

        if score >= 75:
            explanation.append("Institutional sponsorship is strong.")
        elif score >= 55:
            explanation.append("Institutional sponsorship is neutral to moderate.")
        else:
            explanation.append("Institutional sponsorship is weak.")
        self.extend_warnings(warnings, self.value(institutional, "warnings"))
        self.extend_warnings(warnings, self.value(score_result, "warnings"))
        return self.clamp(score)

    @staticmethod
    def confidence_level(final_score, warnings):
        missing_count = sum(1 for warning in warnings if str(warning).lower().startswith("missing"))
        if missing_count >= 2:
            return "LOW"
        if missing_count == 1:
            return "MEDIUM" if final_score >= 65 else "LOW"
        if final_score >= 75:
            return "HIGH"
        if final_score >= 50:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def primary_bounce_result(bounce):
        if bounce is None:
            return None
        if isinstance(bounce, (list, tuple)):
            if not bounce:
                return None
            return max(
                bounce,
                key=lambda result: (
                    BounceCompositeScoringEngine.number(
                        BounceCompositeScoringEngine.value(result, "bounce_success_rate")
                    )
                    or 0,
                    BounceCompositeScoringEngine.number(
                        BounceCompositeScoringEngine.value(result, "average_bounce_pct")
                    )
                    or 0,
                ),
            )
        return bounce

    @staticmethod
    def rsi_score(rsi):
        if 45 <= rsi <= 70:
            return 80.0
        if 35 <= rsi < 45 or 70 < rsi <= 80:
            return 60.0
        if 30 <= rsi < 35:
            return 45.0
        return 25.0

    @staticmethod
    def average_present(values):
        present = [value for value in values if value is not None]
        if not present:
            return DEFAULT_COMPONENT_SCORE
        return sum(present) / len(present)

    @staticmethod
    def extend_warnings(warnings, additional):
        for warning in additional or []:
            if warning not in warnings:
                warnings.append(warning)

    @staticmethod
    def unique_warnings(warnings):
        unique = []
        for warning in warnings:
            if warning and warning not in unique:
                unique.append(warning)
        return unique

    @staticmethod
    def clamp(value):
        return max(0.0, min(100.0, float(value)))

    @staticmethod
    def number(value):
        if value in (None, ""):
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if isfinite(number) else None

    @staticmethod
    def value(source, key):
        if source is None:
            return None
        if isinstance(source, dict):
            return source.get(key)
        return getattr(source, key, None)

    @staticmethod
    def first_existing(*values):
        for value in values:
            if value not in (None, ""):
                return value
        return None
