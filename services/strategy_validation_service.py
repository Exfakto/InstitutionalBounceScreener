from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from statistics import median
from typing import Any


DEFAULT_FORWARD_HORIZONS = (5, 10, 20, 60)
SCORE_BUCKETS = (
    ("90-100", 90.0, 100.0),
    ("80-89", 80.0, 89.999999),
    ("70-79", 70.0, 79.999999),
    ("below 70", float("-inf"), 69.999999),
)


@dataclass(frozen=True)
class ForwardReturnResult:
    horizon_days: int
    complete: bool
    return_pct: float | None = None
    exit_date: str | None = None
    warning: str | None = None

    @property
    def is_win(self):
        return self.complete and self.return_pct is not None and self.return_pct > 0


@dataclass(frozen=True)
class StrategyValidationSample:
    ticker: str
    signal_date: str
    entry_date: str | None
    entry_price: float | None
    final_score: float | None
    forward_returns: dict[int, ForwardReturnResult] = field(default_factory=dict)
    max_forward_gain_pct: float | None = None
    max_forward_drawdown_pct: float | None = None
    complete: bool = False
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ScoreBucketSummary:
    label: str
    sample_count: int = 0
    completed_count: int = 0
    average_return: float = 0.0
    median_return: float = 0.0
    win_rate: float = 0.0


@dataclass(frozen=True)
class StrategyValidationReport:
    samples: list[StrategyValidationSample] = field(default_factory=list)
    horizon_summaries: dict[int, ScoreBucketSummary] = field(default_factory=dict)
    score_buckets: dict[str, ScoreBucketSummary] = field(default_factory=dict)
    sample_count: int = 0
    completed_count: int = 0
    average_return: float = 0.0
    median_return: float = 0.0
    win_rate: float = 0.0
    warnings: list[str] = field(default_factory=list)


class StrategyValidationService:
    """
    Historical forward-return validation for ranked screener candidates.

    The engine enters on the first trading row after the candidate signal date
    to avoid using same-day or future-known close data as the signal input.
    """

    def __init__(self, horizons=None, primary_horizon=20):
        self.horizons = tuple(horizons or DEFAULT_FORWARD_HORIZONS)
        self.primary_horizon = int(primary_horizon)

    def validate(self, candidates, price_history) -> StrategyValidationReport:
        samples = [
            self.validate_sample(candidate, price_history)
            for candidate in (candidates or [])
        ]
        return self.build_report(samples)

    def validate_sample(self, candidate, price_history) -> StrategyValidationSample:
        ticker = self.normalized_ticker(self.value(candidate, "ticker"))
        signal_date = self.first_existing(
            self.value(candidate, "signal_date"),
            self.value(candidate, "created_at"),
            self.value(self.value(candidate, "source"), "created_at"),
            self.value(candidate, "date"),
        )
        score = self.number(
            self.first_existing(
                self.value(candidate, "final_score"),
                self.value(candidate, "primary_score_value"),
                self.value(candidate, "score"),
            )
        )
        warnings = []

        if not ticker:
            return StrategyValidationSample(
                ticker="",
                signal_date=str(signal_date or ""),
                entry_date=None,
                entry_price=None,
                final_score=score,
                complete=False,
                warnings=["Candidate ticker missing"],
            )
        if not signal_date:
            return StrategyValidationSample(
                ticker=ticker,
                signal_date="",
                entry_date=None,
                entry_price=None,
                final_score=score,
                complete=False,
                warnings=["Candidate signal date missing"],
            )

        rows = self.price_rows_for_ticker(price_history, ticker)
        if not rows:
            return StrategyValidationSample(
                ticker=ticker,
                signal_date=str(signal_date),
                entry_date=None,
                entry_price=None,
                final_score=score,
                complete=False,
                warnings=[f"{ticker}: missing price history"],
            )

        entry_index = self.entry_index(rows, signal_date)
        if entry_index is None:
            return StrategyValidationSample(
                ticker=ticker,
                signal_date=str(signal_date),
                entry_date=None,
                entry_price=None,
                final_score=score,
                complete=False,
                warnings=[f"{ticker}: no price row after signal date"],
            )

        entry_row = rows[entry_index]
        entry_price = self.number(self.value(entry_row, "close"))
        entry_date = self.date_value(self.value(entry_row, "date"))
        if entry_price is None or entry_price <= 0:
            return StrategyValidationSample(
                ticker=ticker,
                signal_date=str(signal_date),
                entry_date=str(entry_date),
                entry_price=entry_price,
                final_score=score,
                complete=False,
                warnings=[f"{ticker}: invalid entry price"],
            )

        forward_returns = {}
        for horizon in self.horizons:
            forward_returns[int(horizon)] = self.forward_return(
                rows,
                entry_index,
                entry_price,
                int(horizon),
            )
            if not forward_returns[int(horizon)].complete:
                warnings.append(forward_returns[int(horizon)].warning or "")

        max_gain, max_drawdown = self.forward_extremes(
            rows,
            entry_index,
            entry_price,
            max(self.horizons),
        )
        complete = all(result.complete for result in forward_returns.values())
        return StrategyValidationSample(
            ticker=ticker,
            signal_date=str(signal_date),
            entry_date=str(entry_date),
            entry_price=entry_price,
            final_score=score,
            forward_returns=forward_returns,
            max_forward_gain_pct=max_gain,
            max_forward_drawdown_pct=max_drawdown,
            complete=complete,
            warnings=self.unique(warnings),
        )

    def build_report(self, samples) -> StrategyValidationReport:
        samples = list(samples or [])
        primary_returns = self.completed_returns(samples, self.primary_horizon)
        return StrategyValidationReport(
            samples=samples,
            horizon_summaries={
                horizon: self.summary_for_horizon(str(horizon), samples, horizon)
                for horizon in self.horizons
            },
            score_buckets=self.score_bucket_summaries(samples, self.primary_horizon),
            sample_count=len(samples),
            completed_count=len(primary_returns),
            average_return=self.average(primary_returns),
            median_return=median(primary_returns) if primary_returns else 0.0,
            win_rate=self.win_rate(primary_returns),
            warnings=self.unique(
                warning
                for sample in samples
                for warning in (sample.warnings or [])
            ),
        )

    def summary_for_horizon(self, label, samples, horizon) -> ScoreBucketSummary:
        returns = self.completed_returns(samples, horizon)
        return ScoreBucketSummary(
            label=label,
            sample_count=len(samples or []),
            completed_count=len(returns),
            average_return=self.average(returns),
            median_return=median(returns) if returns else 0.0,
            win_rate=self.win_rate(returns),
        )

    def score_bucket_summaries(self, samples, horizon):
        summaries = {}
        for label, low, high in SCORE_BUCKETS:
            bucket_samples = [
                sample
                for sample in (samples or [])
                if sample.final_score is not None and low <= sample.final_score <= high
            ]
            summaries[label] = self.summary_for_horizon(label, bucket_samples, horizon)
        return summaries

    @classmethod
    def forward_return(cls, rows, entry_index, entry_price, horizon) -> ForwardReturnResult:
        exit_index = entry_index + horizon
        if exit_index >= len(rows):
            return ForwardReturnResult(
                horizon_days=horizon,
                complete=False,
                warning=f"Insufficient forward data for {horizon} trading days",
            )

        exit_row = rows[exit_index]
        exit_price = cls.number(cls.value(exit_row, "close"))
        if exit_price is None:
            return ForwardReturnResult(
                horizon_days=horizon,
                complete=False,
                warning=f"Missing close price at {horizon} trading days",
            )
        return ForwardReturnResult(
            horizon_days=horizon,
            complete=True,
            return_pct=((exit_price - entry_price) / entry_price) * 100,
            exit_date=str(cls.value(exit_row, "date")),
        )

    @classmethod
    def forward_extremes(cls, rows, entry_index, entry_price, horizon):
        max_gain = 0.0
        max_drawdown = 0.0
        last_index = min(len(rows) - 1, entry_index + horizon)
        for row in rows[entry_index + 1 : last_index + 1]:
            high = cls.number(cls.value(row, "high") or cls.value(row, "close"))
            low = cls.number(cls.value(row, "low") or cls.value(row, "close"))
            if high is not None:
                max_gain = max(max_gain, ((high - entry_price) / entry_price) * 100)
            if low is not None:
                max_drawdown = min(
                    max_drawdown,
                    ((low - entry_price) / entry_price) * 100,
                )
        return max_gain, max_drawdown

    @classmethod
    def price_rows_for_ticker(cls, price_history, ticker):
        if isinstance(price_history, dict):
            rows = price_history.get(ticker) or price_history.get(str(ticker).upper()) or []
        else:
            rows = price_history or []
        rows = [
            row
            for row in rows
            if cls.value(row, "date") not in (None, "")
        ]
        return sorted(rows, key=lambda row: cls.date_value(cls.value(row, "date")))

    @classmethod
    def entry_index(cls, rows, signal_date):
        requested = cls.date_value(signal_date)
        for index, row in enumerate(rows):
            if cls.date_value(cls.value(row, "date")) > requested:
                return index
        return None

    @staticmethod
    def completed_returns(samples, horizon):
        values = []
        for sample in samples or []:
            result = sample.forward_returns.get(horizon)
            if result is not None and result.complete and result.return_pct is not None:
                values.append(result.return_pct)
        return values

    @staticmethod
    def average(values):
        values = list(values or [])
        return sum(values) / len(values) if values else 0.0

    @staticmethod
    def win_rate(values):
        values = list(values or [])
        return sum(1 for value in values if value > 0) / len(values) if values else 0.0

    @staticmethod
    def value(source: Any, key: str):
        if source is None:
            return None
        if isinstance(source, dict):
            return source.get(key)
        return getattr(source, key, None)

    @staticmethod
    def number(value):
        if hasattr(value, "value"):
            value = value.value
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def date_value(value):
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return datetime.fromisoformat(str(value)).date()

    @staticmethod
    def first_existing(*values):
        for value in values:
            if value not in (None, ""):
                return value
        return None

    @staticmethod
    def normalized_ticker(value):
        return str(value or "").strip().upper()

    @staticmethod
    def unique(values):
        result = []
        for value in values or []:
            if value and value not in result:
                result.append(value)
        return result
