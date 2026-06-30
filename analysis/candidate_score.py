"""
Candidate score result model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from analysis.composite_intelligence import CompositeIntelligenceResult
from analysis.score_result import ScoreResult


@dataclass(frozen=True)
class CandidateScore:
    """
    Scoring result for one ticker.
    """

    ticker: str
    scores: list[ScoreResult]
    composite_score: ScoreResult
    institutional_bounce_score: float | None = None
    composite_intelligence: CompositeIntelligenceResult | None = None
    composite_intelligence_component_scores: dict = field(default_factory=dict)
    missing_components: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @property
    def score_map(self):
        return {
            score.name: score
            for score in self.scores
        }

    @property
    def primary_score_value(self):
        if self.institutional_bounce_score is not None:
            return self.institutional_bounce_score

        return self.composite_score.value
