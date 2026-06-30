"""
Placeholder earnings risk scoring for v2.1.
"""

from __future__ import annotations

from analysis.base_score import BaseScore
from analysis.score_result import ScoreResult


class EarningsScore(BaseScore):
    """
    Calculates a bounded earnings risk score from explicit earnings metrics.
    """

    name = "earnings_score"

    def calculate(self, metrics):
        """
        Return a v2.1 placeholder heuristic ScoreResult.
        """

        warnings = []
        days_until_earnings = self._number_or_none(
            metrics,
            "days_until_earnings",
            warnings,
        )

        if days_until_earnings is None:
            score = 50.0
        elif 0 <= days_until_earnings <= 7:
            score = 30.0
        elif 8 <= days_until_earnings <= 14:
            score = 55.0
        elif days_until_earnings > 14:
            score = 75.0
        else:
            score = 60.0

        score += self._surprise_adjustment(
            metrics,
            "eps_surprise_pct",
            warnings,
        )
        score += self._surprise_adjustment(
            metrics,
            "revenue_surprise_pct",
            warnings,
        )

        return ScoreResult(
            name=self.name,
            value=self.clamp(score),
            details={
                "warnings": warnings,
            },
        )

    def apply(self, metrics):
        scored = dict(metrics)
        scored["earnings_risk_score"] = self.calculate(scored).value
        return scored

    @staticmethod
    def _number_or_none(metrics, key, warnings):
        value = metrics.get(key)

        if value is None or value == "":
            warnings.append(f"Missing {key}")
            return None

        return float(value)

    def _surprise_adjustment(self, metrics, key, warnings):
        value = self._number_or_none(metrics, key, warnings)

        if value is None:
            return 0.0

        if value >= 0:
            return min(10.0, value * 0.5)

        return max(-15.0, value * 0.75)
