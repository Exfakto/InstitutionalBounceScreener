"""
Generation 2 composite institutional bounce intelligence scoring.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from analysis.score_result import ScoreResult


@dataclass(frozen=True)
class CompositeIntelligenceResult:
    """
    Pure Gen 2 composite intelligence output.
    """

    institutional_bounce_score: float
    component_scores: dict
    weighted_breakdown: dict
    warnings: list[str] = field(default_factory=list)
    missing_components: list[str] = field(default_factory=list)


class CompositeIntelligenceCalculator:
    """
    Combine available analytics into an Institutional Bounce Intelligence Score.

    This is a v2.1 placeholder heuristic:
    - valid component scores are clamped to 0..100
    - configured weights are normalized internally
    - missing components reduce confidence without forcing the score to zero
    - invalid component values are ignored and reported as warnings
    """

    DEFAULT_WEIGHTS = {
        "quality_score": 15,
        "institutional_score": 12,
        "institutional_momentum_score": 10,
        "technical_score": 10,
        "relative_strength_score": 10,
        "support_score": 12,
        "bounce_score": 12,
        "entry_quality_score": 8,
        "volume_score": 5,
        "trend_score": 4,
        "earnings_risk_score": 1,
        "risk_score": 1,
    }

    def __init__(self, weights=None, config_path=None):
        self.config_path = Path(config_path or "config/scoring.json")
        self.weights = dict(weights) if weights is not None else self.load_weights()

    def calculate(self, component_scores):
        warnings = []
        components = component_scores or {}
        weights = self.normalized_weights(self.weights)
        valid_scores = {}
        weighted_breakdown = {}
        missing_components = []
        weighted_total = 0.0
        available_weight = 0.0

        for name, weight in weights.items():
            raw_value = self.component_value(components.get(name))

            if raw_value is None:
                missing_components.append(name)
                continue

            try:
                value = self.clamp(raw_value)
            except (TypeError, ValueError):
                warnings.append(f"Invalid component value for {name}")
                missing_components.append(name)
                continue

            contribution = value * weight
            valid_scores[name] = value
            weighted_breakdown[name] = {
                "score": value,
                "weight": weight,
                "contribution": contribution,
            }
            weighted_total += contribution
            available_weight += weight

        if not valid_scores:
            warnings.append("No valid component scores available")
            return CompositeIntelligenceResult(
                institutional_bounce_score=0.0,
                component_scores={},
                weighted_breakdown={},
                warnings=warnings,
                missing_components=missing_components,
            )

        raw_score = weighted_total / available_weight
        confidence_factor = 0.5 + (available_weight * 0.5)
        final_score = self.clamp(raw_score * confidence_factor)

        if missing_components:
            warnings.append("Missing components reduced confidence")

        return CompositeIntelligenceResult(
            institutional_bounce_score=final_score,
            component_scores=valid_scores,
            weighted_breakdown=weighted_breakdown,
            warnings=warnings,
            missing_components=missing_components,
        )

    def load_weights(self):
        if not self.config_path.exists():
            return dict(self.DEFAULT_WEIGHTS)

        with self.config_path.open("r", encoding="utf-8") as file:
            config = json.load(file)

        return config.get("gen2_weights", self.DEFAULT_WEIGHTS)

    @staticmethod
    def normalized_weights(weights):
        numeric_weights = {}

        for name, weight in (weights or {}).items():
            try:
                numeric_weight = float(weight)
            except (TypeError, ValueError):
                continue

            if numeric_weight > 0:
                numeric_weights[name] = numeric_weight

        total = sum(numeric_weights.values())

        if total <= 0:
            return {}

        return {
            name: weight / total
            for name, weight in numeric_weights.items()
        }

    @staticmethod
    def component_value(value):
        if isinstance(value, ScoreResult):
            return value.value

        return value

    @staticmethod
    def clamp(value):
        return max(0.0, min(100.0, float(value)))
