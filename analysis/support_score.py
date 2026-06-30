"""
Support score provider.
"""

from __future__ import annotations

from analysis.base_score import BaseScore
from analysis.score_result import ScoreResult


class SupportScore(BaseScore):
    """
    Scores support-zone quality.
    """

    name = "support_score"

    def calculate(self, context):
        warnings = []
        strength = self._number(context, "strength_score", warnings)
        touches = self._number(context, "touches", warnings)
        distance_pct = abs(
            self._number(context, "distance_from_current_pct", warnings)
        )

        touch_score = min(20.0, touches * 4)
        distance_score = max(0.0, 20.0 - distance_pct)
        score = (strength * 0.6) + touch_score + distance_score

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
