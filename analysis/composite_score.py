"""
Composite scoring provider.
"""

from __future__ import annotations

import json
from pathlib import Path

from analysis.base_score import BaseScore
from analysis.score_result import ScoreResult


class CompositeScore(BaseScore):
    """
    Calculates a weighted composite score from existing score values.
    """

    name = "composite_score"

    def __init__(self, config_path=None):
        self.config_path = Path(config_path or "config/scoring.json")
        self.weights = self.load_weights()

    def calculate(self, context):
        """
        Return weighted composite score.
        """

        total_weight = 0.0
        weighted_score = 0.0
        values = {}

        for score_name, weight in self.weights.items():
            value = self.score_value(context, score_name)

            if value is None:
                continue

            numeric_weight = float(weight)
            weighted_score += self.clamp(value) * numeric_weight
            total_weight += numeric_weight
            values[score_name] = self.clamp(value)

        composite = (
            weighted_score / total_weight
            if total_weight
            else 0.0
        )

        return ScoreResult(
            name=self.name,
            value=self.clamp(composite),
            details={
                "weights": dict(self.weights),
                "values": values,
            },
        )

    def load_weights(self):
        """
        Load score weights from config/scoring.json.
        """

        if not self.config_path.exists():
            return {}

        with self.config_path.open("r", encoding="utf-8") as file:
            config = json.load(file)

        return config.get("legacy_weights", config.get("weights", {}))

    @staticmethod
    def score_value(context, score_name):

        if isinstance(context, dict):
            value = context.get(score_name)

            if isinstance(value, ScoreResult):
                return value.value

            return value

        return getattr(context, score_name, None)
