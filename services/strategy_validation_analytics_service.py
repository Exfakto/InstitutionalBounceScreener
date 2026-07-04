from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median, stdev

from services.strategy_validation_repository import StrategyValidationRepository


RETURN_COLUMNS = {
    "5d": "return_5d",
    "10d": "return_10d",
    "20d": "return_20d",
    "60d": "return_60d",
}

SCORE_BUCKETS = ("90-100", "80-89", "70-79", "below 70")
OUTCOMES = ("win", "loss", "flat", "incomplete")


@dataclass(frozen=True)
class PerformanceSummary:
    total_samples: int = 0
    completed_samples: int = 0
    win_rate: float = 0.0
    average_return: float = 0.0
    median_return: float = 0.0
    average_drawdown: float = 0.0
    average_max_gain: float = 0.0
    expectancy: float = 0.0
    profit_factor: float = 0.0


@dataclass(frozen=True)
class ForwardReturnSummary:
    horizon: str
    count: int = 0
    average: float = 0.0
    median: float = 0.0
    std_deviation: float = 0.0
    best: float = 0.0
    worst: float = 0.0


@dataclass(frozen=True)
class GroupPerformanceSummary:
    label: str
    count: int = 0
    completed_count: int = 0
    win_rate: float = 0.0
    average_return: float = 0.0
    drawdown: float = 0.0
    expectancy: float = 0.0


@dataclass(frozen=True)
class StrategyValidationAnalyticsReport:
    overall: PerformanceSummary = field(default_factory=PerformanceSummary)
    forward_returns: dict[str, ForwardReturnSummary] = field(default_factory=dict)
    score_buckets: dict[str, GroupPerformanceSummary] = field(default_factory=dict)
    sector_performance: dict[str, GroupPerformanceSummary] = field(default_factory=dict)
    outcome_distribution: dict[str, int] = field(default_factory=dict)


class StrategyValidationAnalyticsService:
    """
    Computes research analytics from persisted strategy validation samples.
    """

    def __init__(self, repository=None, primary_horizon="20d"):
        self.repository = repository or StrategyValidationRepository()
        self.primary_horizon = self.normalize_horizon(primary_horizon)

    def analyze(self, run_id=None, samples=None) -> StrategyValidationAnalyticsReport:
        rows = list(samples if samples is not None else self.load_samples(run_id))
        return StrategyValidationAnalyticsReport(
            overall=self.performance_summary(rows, self.primary_horizon),
            forward_returns={
                horizon: self.forward_return_summary(rows, horizon)
                for horizon in RETURN_COLUMNS
            },
            score_buckets={
                bucket: self.group_summary(bucket, self.rows_for_bucket(rows, bucket))
                for bucket in SCORE_BUCKETS
            },
            sector_performance=self.sector_summaries(rows),
            outcome_distribution=self.outcome_distribution(rows),
        )

    def load_samples(self, run_id=None):
        return self.repository.get_samples_by_date_range(run_id=run_id)

    def performance_summary(self, rows, horizon):
        returns = self.returns_for(rows, horizon)
        winners = [value for value in returns if value > 0]
        losers = [value for value in returns if value < 0]
        gross_profit = sum(winners)
        gross_loss = abs(sum(losers))
        return PerformanceSummary(
            total_samples=len(rows or []),
            completed_samples=len(returns),
            win_rate=self.win_rate(returns),
            average_return=self.average(returns),
            median_return=median(returns) if returns else 0.0,
            average_drawdown=self.average(
                self.numeric_values(rows, "max_drawdown")
            ),
            average_max_gain=self.average(self.numeric_values(rows, "max_gain")),
            expectancy=self.expectancy(returns),
            profit_factor=(
                gross_profit / gross_loss
                if gross_loss
                else (gross_profit if gross_profit else 0.0)
            ),
        )

    def forward_return_summary(self, rows, horizon):
        returns = self.returns_for(rows, horizon)
        return ForwardReturnSummary(
            horizon=horizon,
            count=len(returns),
            average=self.average(returns),
            median=median(returns) if returns else 0.0,
            std_deviation=stdev(returns) if len(returns) > 1 else 0.0,
            best=max(returns) if returns else 0.0,
            worst=min(returns) if returns else 0.0,
        )

    def group_summary(self, label, rows):
        returns = self.returns_for(rows, self.primary_horizon)
        return GroupPerformanceSummary(
            label=label,
            count=len(rows or []),
            completed_count=len(returns),
            win_rate=self.win_rate(returns),
            average_return=self.average(returns),
            drawdown=self.average(self.numeric_values(rows, "max_drawdown")),
            expectancy=self.expectancy(returns),
        )

    def sector_summaries(self, rows):
        grouped = {}
        for row in rows or []:
            sector = self.value(row, "sector")
            if sector in (None, ""):
                continue
            grouped.setdefault(str(sector), []).append(row)
        return {
            sector: self.group_summary(sector, sector_rows)
            for sector, sector_rows in sorted(grouped.items())
        }

    @classmethod
    def outcome_distribution(cls, rows):
        distribution = {outcome: 0 for outcome in OUTCOMES}
        for row in rows or []:
            outcome = str(cls.value(row, "outcome") or "incomplete").lower()
            if outcome not in distribution:
                outcome = "incomplete"
            distribution[outcome] += 1
        return distribution

    @classmethod
    def rows_for_bucket(cls, rows, bucket):
        return [
            row
            for row in (rows or [])
            if cls.value(row, "score_bucket") == bucket
        ]

    @classmethod
    def returns_for(cls, rows, horizon):
        column = RETURN_COLUMNS[cls.normalize_horizon(horizon)]
        return cls.numeric_values(rows, column)

    @classmethod
    def numeric_values(cls, rows, key):
        values = []
        for row in rows or []:
            number = cls.number(cls.value(row, key))
            if number is not None:
                values.append(number)
        return values

    @classmethod
    def expectancy(cls, returns):
        return cls.average(returns)

    @staticmethod
    def win_rate(values):
        values = list(values or [])
        return sum(1 for value in values if value > 0) / len(values) if values else 0.0

    @staticmethod
    def average(values):
        values = list(values or [])
        return sum(values) / len(values) if values else 0.0

    @staticmethod
    def normalize_horizon(horizon):
        normalized = str(horizon or "20d").lower().replace("return_", "")
        return normalized if normalized in RETURN_COLUMNS else "20d"

    @staticmethod
    def value(source, key):
        if source is None:
            return None
        if isinstance(source, dict):
            return source.get(key)
        return getattr(source, key, None)

    @staticmethod
    def number(value):
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
