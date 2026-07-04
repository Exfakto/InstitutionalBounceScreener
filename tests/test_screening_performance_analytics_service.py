from controllers.screening_controller import ScreeningController
from services.screening_performance_analytics_service import (
    ScreeningPerformanceAnalyticsService,
)


def run(run_id="run-1", timings=None, symbols=10):
    return {
        "run_id": run_id,
        "tickers_processed": symbols,
        "stage_timings": timings or {
            "universe_loading": 1,
            "technical_indicator_calculation": 2,
            "support_detection": 3,
            "bounce_detection": 4,
            "institutional_analysis": 5,
            "composite_scoring": 6,
            "candidate_ranking": 7,
            "export_generation": 8,
        },
    }


def stage(analytics, key):
    return next(item for item in analytics.stages if item.stage_key == key)


def test_screening_performance_timing_aggregation():
    analytics = ScreeningPerformanceAnalyticsService().analyze_run(run())

    assert analytics.run_id == "run-1"
    assert analytics.total_screening_time_seconds == 36
    assert analytics.average_time_per_symbol_seconds == 3.6
    assert analytics.slowest_stage.stage_key == "export_generation"
    assert len(analytics.stages) == 8


def test_screening_performance_empty_metrics_are_safe():
    analytics = ScreeningPerformanceAnalyticsService().analyze_run(None)

    assert analytics.total_screening_time_seconds == 0
    assert analytics.stages == []
    assert analytics.warnings == ["No screening performance metrics available."]


def test_screening_performance_stage_comparison():
    current = run(
        "current",
        timings={
            "universe_loading": 2,
            "technical_indicator_calculation": 1,
            "support_detection": 3,
        },
        symbols=2,
    )
    previous = run(
        "previous",
        timings={
            "universe_loading": 1,
            "technical_indicator_calculation": 2,
            "support_detection": 3,
        },
        symbols=2,
    )

    analytics = ScreeningPerformanceAnalyticsService().analyze_run(current, previous)

    assert stage(analytics, "universe_loading").classification == "slower"
    assert stage(analytics, "universe_loading").delta_seconds == 1
    assert stage(analytics, "universe_loading").percent_delta == 100
    assert stage(analytics, "technical_indicator_calculation").classification == "faster"
    assert stage(analytics, "support_detection").classification == "unchanged"


def test_screening_performance_analyze_latest_uses_repository_history():
    class Repository:
        def fetch_screening_run_history(self, limit=2):
            assert limit == 2
            return [run("new", {"universe_loading": 2}, 1), run("old", {"universe_loading": 1}, 1)]

    analytics = ScreeningPerformanceAnalyticsService(Repository()).analyze_latest()

    assert analytics.run_id == "new"
    assert stage(analytics, "universe_loading").classification == "slower"


def test_screening_controller_integration_delegates_to_service():
    class Service:
        def __init__(self):
            self.run = None
            self.previous = None

        def analyze_run(self, run=None, previous_run=None):
            self.run = run
            self.previous = previous_run
            return "analytics"

        def analyze_latest(self):
            return "latest"

    service = Service()
    controller = ScreeningController(performance_analytics_service=service)

    assert controller.get_screening_performance_analytics(run={"run_id": "x"}) == "analytics"
    assert service.run == {"run_id": "x"}
    assert controller.get_screening_performance_analytics() == "latest"
