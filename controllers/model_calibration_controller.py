from __future__ import annotations

from services.model_calibration_history_service import ModelCalibrationHistoryService
from services.model_calibration_recommendation_service import (
    ModelCalibrationRecommendationService,
)
from services.model_calibration_trend_service import ModelCalibrationTrendService


class ModelCalibrationController:
    def __init__(
        self,
        repository=None,
        recommendation_service=None,
        history_service=None,
        trend_service=None,
    ):
        self.repository = repository
        self.recommendation_service = (
            recommendation_service
            or ModelCalibrationRecommendationService(repository=repository)
        )
        self.history_service = history_service or ModelCalibrationHistoryService(
            repository=repository
        )
        self.trend_service = trend_service or ModelCalibrationTrendService(
            history_service=self.history_service
        )

    def get_calibration_recommendations(self, run_id=None):
        return self.recommendation_service.get_recommendations(run_id=run_id)

    def get_calibration_history(self, limit=25, offset=0):
        return self.history_service.get_history(limit=limit, offset=offset)

    def get_calibration_run_details(self, run_id):
        return self.history_service.get_run_details(run_id)

    def get_calibration_trend(self, window="Last 25"):
        return self.trend_service.get_trend(window=window)
