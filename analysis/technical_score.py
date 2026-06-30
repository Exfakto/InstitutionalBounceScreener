"""
Technical score provider.
"""

from __future__ import annotations

from analysis.base_score import BaseScore
from analysis.score_result import ScoreResult


class TechnicalScore(BaseScore):
    """
    Scores basic technical trend quality.
    """

    name = "technical_score"

    def calculate(self, context):
        score = 0.0
        warnings = []

        close = self._number(context, "close", warnings)
        sma20 = self._number(context, "sma20", warnings)
        sma50 = self._number(context, "sma50", warnings)
        sma200 = self._number(context, "sma200", warnings)
        rsi14 = self._number(context, "rsi14", warnings)

        if close and sma20 and close > sma20:
            score += 25

        if sma20 and sma50 and sma20 > sma50:
            score += 25

        if sma50 and sma200 and sma50 > sma200:
            score += 25

        if 40 <= rsi14 <= 70:
            score += 25

        return ScoreResult(
            name=self.name,
            value=self.clamp(score),
            details={
                "warnings": warnings,
            },
        )

    @staticmethod
    def _number(context, key, warnings):
        value = context.get(key)

        if value is None or value == "":
            warnings.append(f"Missing {key}")
            return 0.0

        return float(value)
