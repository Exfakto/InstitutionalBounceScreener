from __future__ import annotations

from dataclasses import dataclass, field

from services.beta_testing_service import (
    CandidateReviewItem,
    CandidateReviewPackService as LegacyCandidateReviewPackService,
)
from services.model_calibration_recommendation_service import (
    ModelCalibrationRecommendationService,
    recommendation_to_dict,
)


@dataclass(frozen=True)
class BetaReviewPack:
    candidates: list[CandidateReviewItem] = field(default_factory=list)
    calibration_recommendations: list[dict] = field(default_factory=list)


class BetaReviewPackService:
    """Build beta review packs with optional model calibration recommendations."""

    def __init__(
        self,
        repository=None,
        chart_data_service=None,
        calibration_recommendation_service=None,
    ):
        self.candidate_service = LegacyCandidateReviewPackService(
            repository=repository,
            chart_data_service=chart_data_service,
        )
        self.calibration_recommendation_service = (
            calibration_recommendation_service
            or ModelCalibrationRecommendationService(repository=repository)
        )

    def generate(self, candidates, top_n=10, calibration_run_id=None):
        candidate_rows = self.candidate_service.generate(candidates, top_n=top_n)
        return BetaReviewPack(
            candidates=candidate_rows,
            calibration_recommendations=self.calibration_recommendations(
                calibration_run_id
            ),
        )

    def calibration_recommendations(self, calibration_run_id=None):
        recommendations = self.calibration_recommendation_service.get_recommendations(
            run_id=calibration_run_id
        )
        return [recommendation_to_dict(item) for item in recommendations]

    def checklist(self, review_pack):
        candidates = getattr(review_pack, "candidates", review_pack)
        return self.candidate_service.checklist(candidates)
