"""
Candidate score result model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from analysis.composite_intelligence import CompositeIntelligenceResult
from analysis.institutional_checklist import InstitutionalChecklistResult
from analysis.opportunity_rating import OpportunityRatingResult
from analysis.score_result import ScoreResult

if TYPE_CHECKING:
    from analysis.trade_thesis import TradeThesisResult


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
    opportunity_rating: OpportunityRatingResult | None = None
    institutional_checklist: InstitutionalChecklistResult | None = None
    trade_thesis: "TradeThesisResult | None" = None
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
