from __future__ import annotations

from services.full_universe_validation_service import FullUniverseValidationService
from services.screening_performance_analytics_service import (
    ScreeningPerformanceAnalyticsService,
)


class ScreeningController:
    def __init__(
        self,
        repository=None,
        performance_analytics_service=None,
        full_universe_validation_service=None,
    ):
        self.repository = repository
        self.performance_analytics_service = (
            performance_analytics_service
            or ScreeningPerformanceAnalyticsService(repository=repository)
        )
        self.full_universe_validation_service = (
            full_universe_validation_service
            or FullUniverseValidationService(universe_adapter=repository)
        )

    def get_screening_performance_analytics(self, run=None, previous_run=None):
        if run is not None:
            return self.performance_analytics_service.analyze_run(run, previous_run)
        return self.performance_analytics_service.analyze_latest()

    def validate_full_universe(self, progress_callback=None, cancellation_callback=None):
        return self.full_universe_validation_service.validate(
            progress_callback=progress_callback,
            cancellation_callback=cancellation_callback,
        )
