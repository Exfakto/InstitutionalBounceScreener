from __future__ import annotations

from services.screening_performance_analytics_service import (
    ScreeningPerformanceAnalyticsService,
)


class ScreeningController:
    def __init__(self, repository=None, performance_analytics_service=None):
        self.repository = repository
        self.performance_analytics_service = (
            performance_analytics_service
            or ScreeningPerformanceAnalyticsService(repository=repository)
        )

    def get_screening_performance_analytics(self, run=None, previous_run=None):
        if run is not None:
            return self.performance_analytics_service.analyze_run(run, previous_run)
        return self.performance_analytics_service.analyze_latest()
