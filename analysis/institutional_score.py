"""
Placeholder institutional scoring for v1.1.
"""

from __future__ import annotations

from analysis.base_score import BaseScore
from analysis.score_result import ScoreResult


class InstitutionalScore(BaseScore):
    """
    Calculates a simple bounded institutional score.
    """

    name = "institutional_score"

    def calculate(self, metrics):
        """
        Return a v1.1 placeholder heuristic ScoreResult.
        """

        score = 0.0
        warnings = []

        # v1.1 placeholder heuristic: reward meaningful ownership,
        # positive ownership change, net buying, and insider buying;
        # penalize insider selling.
        score += self._positive_metric_score(
            metrics,
            "institutional_ownership_pct",
            30,
            80,
            warnings,
        )
        score += self._signed_change_score(
            metrics,
            "institutional_ownership_change_qoq",
            warnings,
        )
        score += (
            25
            if self._number(metrics, "net_institutional_buying", warnings) > 0
            else 0
        )
        score += 10 if self._flag(metrics, "insider_buying_flag", warnings) else 0
        score -= 10 if self._flag(metrics, "insider_selling_flag", warnings) else 0

        return ScoreResult(
            name=self.name,
            value=self.clamp(score),
            details={
                "warnings": warnings,
            },
        )

    def apply(self, metrics):
        scored = dict(metrics)
        scored["institutional_score"] = self.calculate(scored).value
        return scored

    @staticmethod
    def _number(metrics, key, warnings):
        value = metrics.get(key)

        if value is None or value == "":
            warnings.append(f"Missing {key}")
            return 0.0

        return float(value)

    @staticmethod
    def _flag(metrics, key, warnings):
        value = metrics.get(key)

        if value is None or value == "":
            warnings.append(f"Missing {key}")
            return False

        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "y"}

        return bool(value)

    def _positive_metric_score(self, metrics, key, max_points, target, warnings):
        value = self._number(metrics, key, warnings)

        if value <= 0:
            return 0.0

        return min(max_points, value / target * max_points)

    def _signed_change_score(self, metrics, key, warnings):
        value = self._number(metrics, key, warnings)

        if value <= 0:
            return 0.0

        return min(25.0, value / 5 * 25)
