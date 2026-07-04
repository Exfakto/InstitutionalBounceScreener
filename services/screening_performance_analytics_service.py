from __future__ import annotations

from dataclasses import dataclass, field


STAGES = [
    ("universe_loading", "Universe loading"),
    ("technical_indicator_calculation", "Technical indicator calculation"),
    ("support_detection", "Support detection"),
    ("bounce_detection", "Bounce detection"),
    ("institutional_analysis", "Institutional analysis"),
    ("composite_scoring", "Composite scoring"),
    ("candidate_ranking", "Candidate ranking"),
    ("export_generation", "Export generation"),
]


@dataclass(frozen=True)
class ScreeningStageTiming:
    stage_key: str
    stage_name: str
    duration_seconds: float
    previous_duration_seconds: float | None = None
    delta_seconds: float | None = None
    percent_delta: float | None = None
    classification: str = "unchanged"


@dataclass(frozen=True)
class ScreeningPerformanceAnalytics:
    run_id: str | None = None
    total_screening_time_seconds: float = 0.0
    average_time_per_symbol_seconds: float | None = None
    symbol_count: int = 0
    slowest_stage: ScreeningStageTiming | None = None
    stages: list[ScreeningStageTiming] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class ScreeningPerformanceAnalyticsService:
    """Calculate passive performance analytics for completed screening runs."""

    def __init__(self, repository=None):
        self.repository = repository

    def analyze_run(self, run=None, previous_run=None):
        if run is None:
            return ScreeningPerformanceAnalytics(
                warnings=["No screening performance metrics available."]
            )
        durations = stage_durations(run)
        previous_durations = stage_durations(previous_run) if previous_run is not None else {}
        stages = [
            self.stage_timing(key, name, durations.get(key, 0.0), previous_durations.get(key))
            for key, name in STAGES
        ]
        total = sum(stage.duration_seconds for stage in stages)
        symbol_count = int(
            first_existing(
                value(run, "symbol_count"),
                value(run, "tickers_processed"),
                value(run, "scanned_count"),
                value(run, "tickers_requested"),
                0,
            )
            or 0
        )
        average = (total / symbol_count) if symbol_count > 0 else None
        slowest = max(stages, key=lambda item: item.duration_seconds) if stages else None
        warnings = []
        if not any(stage.duration_seconds for stage in stages):
            warnings.append("No stage timing metrics available.")
        return ScreeningPerformanceAnalytics(
            run_id=value(run, "run_id"),
            total_screening_time_seconds=round(total, 6),
            average_time_per_symbol_seconds=round(average, 6) if average is not None else None,
            symbol_count=symbol_count,
            slowest_stage=slowest,
            stages=stages,
            warnings=warnings,
        )

    def analyze_latest(self):
        runs = self.fetch_recent_runs(limit=2)
        current = runs[0] if runs else None
        previous = runs[1] if len(runs) > 1 else None
        return self.analyze_run(current, previous)

    def fetch_recent_runs(self, limit=2):
        if self.repository is None:
            return []
        if hasattr(self.repository, "fetch_screening_performance_history"):
            return list(self.repository.fetch_screening_performance_history(limit=limit) or [])
        if hasattr(self.repository, "fetch_screening_run_history"):
            return list(self.repository.fetch_screening_run_history(limit=limit) or [])
        latest = None
        if hasattr(self.repository, "fetch_latest_screening_run"):
            latest = self.repository.fetch_latest_screening_run()
        return [latest] if latest is not None else []

    @staticmethod
    def stage_timing(key, name, duration, previous_duration=None):
        duration = float(duration or 0.0)
        previous = None if previous_duration is None else float(previous_duration or 0.0)
        delta = None
        percent_delta = None
        classification = "unchanged"
        if previous is not None:
            delta = duration - previous
            percent_delta = (delta / abs(previous)) * 100.0 if previous else None
            if abs(delta) >= 1e-12:
                classification = "slower" if delta > 0 else "faster"
        return ScreeningStageTiming(
            stage_key=key,
            stage_name=name,
            duration_seconds=round(duration, 6),
            previous_duration_seconds=previous,
            delta_seconds=round(delta, 6) if delta is not None else None,
            percent_delta=round(percent_delta, 6) if percent_delta is not None else None,
            classification=classification,
        )


def stage_durations(run):
    timings = value(run, "stage_timings") or value(run, "stage_durations") or {}
    result = {}
    for key, _name in STAGES:
        result[key] = number_value(
            first_existing(
                value(timings, key),
                value(timings, key.replace("_", " ")),
                value(run, key),
                value(run, f"{key}_seconds"),
            ),
            default=0.0,
        )
    return result


def value(source, key, default=None):
    if source is None:
        return default
    if isinstance(source, dict):
        return source.get(key, default)
    return getattr(source, key, default)


def first_existing(*values):
    for item in values:
        if item not in (None, ""):
            return item
    return None


def number_value(raw, default=0.0):
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default
