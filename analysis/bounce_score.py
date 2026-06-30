"""
Bounce score provider.
"""

from __future__ import annotations

from analysis.base_score import BaseScore
from analysis.score_result import ScoreResult


class BounceScore(BaseScore):
    """
    Scores historical bounce validation quality.
    """

    name = "bounce_score"

    def calculate(self, context):
        warnings = []
        success_rate = self._number(context, "bounce_success_rate", warnings)
        average_bounce = self._number(context, "average_bounce_pct", warnings)
        total_touches = self._number(context, "total_touches", warnings)
        failed = self._number(context, "failed_breakdowns", warnings)

        success_score = success_rate * 0.55
        bounce_score = min(25.0, average_bounce * 2.5)
        touch_score = min(15.0, total_touches * 3)
        failure_penalty = min(20.0, failed * 5)
        score = success_score + bounce_score + touch_score - failure_penalty

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
