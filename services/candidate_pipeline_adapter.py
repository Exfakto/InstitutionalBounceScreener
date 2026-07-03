"""
Pipeline adapter from composite scores to persisted ranked candidates.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from services.candidate_ranking_engine import CandidateRankingEngine, CandidateRankingResult


@dataclass(frozen=True)
class CandidatePipelineResult:
    run_id: str
    ranked_candidates: list
    rejected_candidates: list
    warnings: list[str]


class CandidatePipelineAdapter:
    """
    Rank composite score results and persist the ranking run.
    """

    def __init__(self, repository, ranking_engine=None):
        self.repository = repository
        self.ranking_engine = ranking_engine or CandidateRankingEngine()

    def run(
        self,
        composite_scores,
        run_id=None,
        minimum_score=None,
        allow_low_confidence=False,
    ):
        run_id = str(run_id or uuid4())
        scores = list(composite_scores or [])

        if minimum_score is None:
            ranking_result = self.ranking_engine.rank_composite_scores(
                scores,
                allow_low_confidence=allow_low_confidence,
            )
        else:
            ranking_result = self.ranking_engine.rank_composite_scores(
                scores,
                minimum_score=minimum_score,
                allow_low_confidence=allow_low_confidence,
            )

        candidates_to_save = [
            *ranking_result.ranked_candidates,
            *ranking_result.rejected_candidates,
        ]
        self.repository.save_ranked_candidates(run_id, candidates_to_save)

        return CandidatePipelineResult(
            run_id=run_id,
            ranked_candidates=ranking_result.ranked_candidates,
            rejected_candidates=ranking_result.rejected_candidates,
            warnings=ranking_result.warnings,
        )
