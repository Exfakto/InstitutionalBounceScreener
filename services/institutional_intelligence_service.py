"""
Normalize raw institutional metrics into component scores.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite


OWNERSHIP_WEIGHT = 0.35
OWNERSHIP_TREND_WEIGHT = 0.20
INSTITUTIONAL_BUYING_WEIGHT = 0.25
INSIDER_ACTIVITY_WEIGHT = 0.20

DEFAULT_COMPONENT_SCORE = 50.0
STRONG_OWNERSHIP_PCT = 70.0
TREND_SCALE_PCT = 5.0
BUYING_SCALE_DOLLARS = 500_000_000.0


@dataclass(frozen=True)
class InstitutionalScoreResult:
    ownership_score: float
    ownership_trend_score: float
    institutional_buying_score: float
    insider_activity_score: float
    overall_institutional_strength_score: float
    ownership_explanation: str
    ownership_trend_explanation: str
    institutional_buying_explanation: str
    insider_activity_explanation: str
    overall_explanation: str
    warnings: list[str] = field(default_factory=list)


class InstitutionalIntelligenceService:
    """
    Convert raw institutional activity metrics into normalized 0-100 scores.
    """

    def calculate(
        self,
        institutional_ownership_pct=None,
        institutional_ownership_change_qoq=None,
        net_institutional_buying=None,
        insider_buying_flag=None,
        insider_selling_flag=None,
    ):
        warnings = []

        ownership_score, ownership_text = self.score_ownership(
            institutional_ownership_pct,
            warnings,
        )
        trend_score, trend_text = self.score_ownership_trend(
            institutional_ownership_change_qoq,
            warnings,
        )
        buying_score, buying_text = self.score_institutional_buying(
            net_institutional_buying,
            warnings,
        )
        insider_score, insider_text = self.score_insider_activity(
            insider_buying_flag,
            insider_selling_flag,
            warnings,
        )

        overall = self.clamp(
            ownership_score * OWNERSHIP_WEIGHT
            + trend_score * OWNERSHIP_TREND_WEIGHT
            + buying_score * INSTITUTIONAL_BUYING_WEIGHT
            + insider_score * INSIDER_ACTIVITY_WEIGHT
        )

        return InstitutionalScoreResult(
            ownership_score=ownership_score,
            ownership_trend_score=trend_score,
            institutional_buying_score=buying_score,
            insider_activity_score=insider_score,
            overall_institutional_strength_score=round(overall, 2),
            ownership_explanation=ownership_text,
            ownership_trend_explanation=trend_text,
            institutional_buying_explanation=buying_text,
            insider_activity_explanation=insider_text,
            overall_explanation=self.overall_explanation(overall),
            warnings=warnings,
        )

    def calculate_from_record(self, record):
        return self.calculate(
            institutional_ownership_pct=self.value(record, "institutional_ownership_pct"),
            institutional_ownership_change_qoq=self.value(
                record,
                "institutional_ownership_change_qoq",
            ),
            net_institutional_buying=self.value(record, "net_institutional_buying"),
            insider_buying_flag=self.value(record, "insider_buying_flag"),
            insider_selling_flag=self.value(record, "insider_selling_flag"),
        )

    def score_ownership(self, value, warnings):
        number = self.number(value)
        if number is None:
            warnings.append("Missing institutional ownership")
            return DEFAULT_COMPONENT_SCORE, "Institutional ownership is unavailable; using neutral score."

        score = self.clamp((number / STRONG_OWNERSHIP_PCT) * 100)
        if number >= 60:
            text = f"Institutional ownership is strong at {number:.1f}%."
        elif number >= 35:
            text = f"Institutional ownership is moderate at {number:.1f}%."
        else:
            text = f"Institutional ownership is weak at {number:.1f}%."
        return round(score, 2), text

    def score_ownership_trend(self, value, warnings):
        number = self.number(value)
        if number is None:
            warnings.append("Missing institutional ownership trend")
            return DEFAULT_COMPONENT_SCORE, "Ownership trend is unavailable; using neutral score."

        score = self.directional_score(number, TREND_SCALE_PCT)
        if number > 0:
            text = f"Ownership increased {number:.1f}% quarter over quarter."
        elif number < 0:
            text = f"Ownership decreased {abs(number):.1f}% quarter over quarter."
        else:
            text = "Ownership was flat quarter over quarter."
        return score, text

    def score_institutional_buying(self, value, warnings):
        number = self.number(value)
        if number is None:
            warnings.append("Missing net institutional buying")
            return DEFAULT_COMPONENT_SCORE, "Net institutional buying is unavailable; using neutral score."

        score = self.directional_score(number, BUYING_SCALE_DOLLARS)
        if number > 0:
            text = f"Net institutional buying is positive at ${number:,.0f}."
        elif number < 0:
            text = f"Net institutional buying is negative at -${abs(number):,.0f}."
        else:
            text = "Net institutional buying is flat."
        return score, text

    def score_insider_activity(self, buying, selling, warnings):
        buying_value = self.bool_or_none(buying)
        selling_value = self.bool_or_none(selling)

        if buying_value is None and selling_value is None:
            warnings.append("Missing insider activity")
            return DEFAULT_COMPONENT_SCORE, "Insider activity is unavailable; using neutral score."

        if buying_value and not selling_value:
            return 85.0, "Insider buying is present without insider selling pressure."
        if selling_value and not buying_value:
            return 20.0, "Insider selling is present without offsetting insider buying."
        if buying_value and selling_value:
            return 50.0, "Insider buying and selling are both present; using neutral score."
        return 55.0, "No major insider selling pressure is present."

    @staticmethod
    def overall_explanation(score):
        if score >= 75:
            return "Overall institutional strength is strong."
        if score >= 55:
            return "Overall institutional strength is neutral to moderate."
        return "Overall institutional strength is weak."

    @staticmethod
    def directional_score(value, scale):
        bounded = max(-1.0, min(1.0, value / scale))
        return round((bounded + 1) * 50, 2)

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
    def bool_or_none(value):
        if value in (None, ""):
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value > 0
        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "yes", "y", "buying", "positive"}:
            return True
        if normalized in {"0", "false", "no", "n", "none", "neutral"}:
            return False
        return None

    @staticmethod
    def value(record, key):
        if record is None:
            return None
        if isinstance(record, dict):
            return record.get(key)
        return getattr(record, key, None)
