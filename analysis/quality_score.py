"""
Placeholder fundamental quality scoring for v1.1.
"""

from __future__ import annotations

from analysis.base_score import BaseScore
from analysis.score_result import ScoreResult


class QualityScore(BaseScore):
    """
    Calculates a simple bounded quality score from fundamental metrics.
    """

    name = "quality_score"

    def calculate(self, metrics):
        """
        Return a v1.1 placeholder heuristic ScoreResult.
        """

        score = 0.0
        warnings = []

        # v1.1 placeholder heuristic: reward growth, profitability,
        # cash generation, modest leverage, and basic liquidity.
        score += self._positive_metric_score(
            metrics,
            "revenue_growth_ttm",
            15,
            20,
            warnings,
        )
        score += self._positive_metric_score(
            metrics,
            "eps_growth_ttm",
            15,
            20,
            warnings,
        )
        score += self._positive_metric_score(metrics, "roe", 15, 25, warnings)
        score += self._positive_metric_score(
            metrics,
            "gross_margin",
            15,
            60,
            warnings,
        )
        score += (
            15
            if self._number(metrics, "free_cash_flow", warnings) > 0
            else 0
        )
        score += self._inverse_metric_score(
            metrics,
            "debt_to_equity",
            15,
            2,
            warnings,
        )
        score += self._current_ratio_score(metrics, warnings)

        return ScoreResult(
            name=self.name,
            value=self.clamp(score),
            details={
                "warnings": warnings,
            },
        )

    def apply(self, metrics):
        scored = dict(metrics)
        scored["quality_score"] = self.calculate(scored).value
        return scored

    @staticmethod
    def _number(metrics, key, warnings):
        value = metrics.get(key)

        if value is None or value == "":
            warnings.append(f"Missing {key}")
            return 0.0

        return float(value)

    def _positive_metric_score(self, metrics, key, max_points, target, warnings):
        value = self._number(metrics, key, warnings)

        if value <= 0:
            return 0.0

        return min(max_points, value / target * max_points)

    def _inverse_metric_score(self, metrics, key, max_points, limit, warnings):
        value = self._number(metrics, key, warnings)

        if value <= 0:
            return max_points

        return max(0.0, max_points * (1 - value / limit))

    def _current_ratio_score(self, metrics, warnings):
        value = self._number(metrics, "current_ratio", warnings)

        if value <= 0:
            return 0.0

        if value >= 1.5:
            return 10.0

        return value / 1.5 * 10
