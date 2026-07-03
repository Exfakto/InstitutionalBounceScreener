"""
Institutional Bounce scoring engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite


@dataclass(frozen=True)
class InstitutionalBounceScoreInput:
    ticker: str | None = None
    fundamental_quality_score: float | None = None
    institutional_sponsorship_score: float | None = None
    support_strength_score: float | None = None
    bounce_success_rate: float | None = None
    average_bounce_pct: float | None = None
    relative_strength_score: float | None = None
    volume_accumulation_score: float | None = None
    risk_score: float | None = None
    risk_rating: str | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class InstitutionalBounceScoreResult:
    ticker: str | None
    fundamental_quality_score: float
    institutional_sponsorship_score: float
    support_strength_score: float
    bounce_history_score: float
    relative_strength_score: float
    volume_accumulation_score: float
    risk_penalty_score: float
    final_score: float
    rating_label: str
    opportunity_rating: str
    risk_rating: str
    explanation: str
    warnings: list[str] = field(default_factory=list)


class InstitutionalBounceScoringEngine:
    WEIGHTS = {
        "fundamental_quality": 20,
        "institutional_sponsorship": 20,
        "support_strength": 20,
        "bounce_history": 15,
        "relative_strength": 10,
        "volume_accumulation": 10,
    }

    def score(self, data):
        score_input = self.normalize_input(data)
        warnings = list(score_input.warnings)

        fundamental = self.clamp_or_default(score_input.fundamental_quality_score, 50, warnings, "Missing fundamental quality")
        institutional = self.clamp_or_default(score_input.institutional_sponsorship_score, 50, warnings, "Missing institutional sponsorship")
        support = self.clamp_or_default(score_input.support_strength_score, 50, warnings, "Missing support strength")
        bounce = self.bounce_history_score(score_input, warnings)
        relative_strength = self.clamp_or_default(score_input.relative_strength_score, 50, warnings, "Missing relative strength")
        volume = self.clamp_or_default(score_input.volume_accumulation_score, 50, warnings, "Missing volume accumulation")
        risk_penalty = self.risk_penalty(score_input)

        weighted = (
            fundamental * 0.20
            + institutional * 0.20
            + support * 0.20
            + bounce * 0.15
            + relative_strength * 0.10
            + volume * 0.10
        )
        normalized_weighted = weighted / (sum(self.WEIGHTS.values()) / 100)
        final_score = round(max(0.0, min(100.0, normalized_weighted - risk_penalty)), 2)
        risk_rating = self.risk_rating(score_input)

        return InstitutionalBounceScoreResult(
            ticker=score_input.ticker,
            fundamental_quality_score=fundamental,
            institutional_sponsorship_score=institutional,
            support_strength_score=support,
            bounce_history_score=bounce,
            relative_strength_score=relative_strength,
            volume_accumulation_score=volume,
            risk_penalty_score=risk_penalty,
            final_score=final_score,
            rating_label=self.rating_label(final_score),
            opportunity_rating=self.opportunity_rating(final_score),
            risk_rating=risk_rating,
            explanation=self.explanation(
                final_score,
                fundamental,
                institutional,
                support,
                bounce,
                relative_strength,
                volume,
                risk_penalty,
            ),
            warnings=warnings,
        )

    def normalize_input(self, data):
        if isinstance(data, InstitutionalBounceScoreInput):
            return data

        return InstitutionalBounceScoreInput(
            ticker=self.value(data, "ticker"),
            fundamental_quality_score=self.first_number(data, ["fundamental_quality_score", "quality_score"]),
            institutional_sponsorship_score=self.first_number(data, ["institutional_sponsorship_score", "institutional_score", "institutional_score_value"]),
            support_strength_score=self.first_number(data, ["support_strength_score", "support_score", "strength_score"]),
            bounce_success_rate=self.first_number(data, ["bounce_success_rate", "bounce_success_pct", "historical_bounce_success_rate"]),
            average_bounce_pct=self.first_number(data, ["average_bounce_pct", "average_bounce", "avg_bounce"]),
            relative_strength_score=self.first_number(data, ["relative_strength_score", "relative_strength"]),
            volume_accumulation_score=self.first_number(data, ["volume_accumulation_score", "volume_score", "accumulation_score"]),
            risk_score=self.first_number(data, ["risk_score", "overall_risk_score"]),
            risk_rating=self.first_existing(self.value(data, "risk_rating"), self.metric(data, "risk_rating")),
            warnings=list(self.value(data, "warnings") or []),
        )

    def bounce_history_score(self, score_input, warnings):
        success = score_input.bounce_success_rate
        average = score_input.average_bounce_pct
        if success is None and average is None:
            warnings.append("Missing bounce history")
            return 50.0
        success_score = self.clamp(success if success is not None else 50)
        average_score = self.clamp((average or 0) * 4)
        return round(success_score * 0.7 + average_score * 0.3, 2)

    def risk_penalty(self, score_input):
        rating = str(score_input.risk_rating or "").lower()
        if "high" in rating:
            return 15.0
        if "moderate" in rating or "medium" in rating:
            return 7.5
        risk = score_input.risk_score
        if risk is None:
            return 0.0
        return round(min(15.0, max(0.0, risk / 100 * 15)), 2)

    def risk_rating(self, score_input):
        explicit = score_input.risk_rating
        if explicit:
            text = str(explicit)
            lower = text.lower()
            if "low" in lower:
                return "Low"
            if "moderate" in lower or "medium" in lower:
                return "Moderate"
            if "high" in lower:
                return "High"
        if score_input.risk_score is None:
            return "Unknown"
        if score_input.risk_score >= 70:
            return "High"
        if score_input.risk_score >= 40:
            return "Moderate"
        return "Low"

    @staticmethod
    def rating_label(score):
        if score >= 90:
            return "A+ Elite Bounce Setup"
        if score >= 80:
            return "A High-Probability Setup"
        if score >= 70:
            return "B Watchlist Candidate"
        if score >= 60:
            return "C Weak / Needs Confirmation"
        return "Reject"

    @staticmethod
    def opportunity_rating(score):
        if score >= 80:
            return "Strong"
        if score >= 70:
            return "Moderate"
        if score >= 60:
            return "Weak"
        return "Reject"

    @staticmethod
    def explanation(final_score, fundamental, institutional, support, bounce, relative_strength, volume, risk_penalty):
        strengths = []
        if institutional >= 70:
            strengths.append("strong institutional sponsorship")
        if support >= 70:
            strengths.append("strong support quality")
        if bounce >= 70:
            strengths.append("favorable historical bounce behavior")
        if relative_strength >= 70:
            strengths.append("positive relative strength")
        if volume >= 70:
            strengths.append("constructive volume accumulation")
        if not strengths:
            strengths.append("limited confirmed edge")
        risk_text = f" Risk penalty reduced the score by {risk_penalty:.1f} points." if risk_penalty else ""
        return f"Final score {final_score:.1f} reflects " + ", ".join(strengths) + "." + risk_text

    @staticmethod
    def clamp_or_default(value, default, warnings, warning):
        if value is None:
            warnings.append(warning)
            return float(default)
        return InstitutionalBounceScoringEngine.clamp(value)

    @staticmethod
    def clamp(value):
        return max(0.0, min(100.0, float(value)))

    @staticmethod
    def first_number(data, keys):
        for key in keys:
            number = InstitutionalBounceScoringEngine.number(InstitutionalBounceScoringEngine.value(data, key))
            if number is not None:
                return number
            number = InstitutionalBounceScoringEngine.number(InstitutionalBounceScoringEngine.metric(data, key))
            if number is not None:
                return number
        return None

    @staticmethod
    def value(source, key):
        if source is None:
            return None
        if isinstance(source, dict):
            return source.get(key)
        return getattr(source, key, None)

    @staticmethod
    def metric(source, key):
        metrics = InstitutionalBounceScoringEngine.value(source, "metrics")
        return metrics.get(key) if isinstance(metrics, dict) else None

    @staticmethod
    def first_existing(*values):
        for value in values:
            if value not in (None, ""):
                return value
        return None

    @staticmethod
    def number(value):
        if value in (None, ""):
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if isfinite(number) else None
