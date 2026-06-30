"""
Candidate score result model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from analysis.score_result import ScoreResult


@dataclass(frozen=True)
class CandidateScore:
    """
    Scoring result for one ticker.
    """

    ticker: str
    scores: list[ScoreResult]
    composite_score: ScoreResult
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @property
    def score_map(self):
        return {
            score.name: score
            for score in self.scores
        }
