from __future__ import annotations

from services.model_calibration_recommendation_service import (
    ModelCalibrationRecommendationService,
)


class ModelCalibrationController:
    def __init__(self, repository=None, recommendation_service=None):
        self.repository = repository
        self.recommendation_service = (
            recommendation_service
            or ModelCalibrationRecommendationService(repository=repository)
        )

    def get_calibration_recommendations(self, run_id=None):
        return self.recommendation_service.get_recommendations(run_id=run_id)
