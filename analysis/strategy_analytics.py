"""
Institutional Bounce strategy analytics utilities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass(frozen=True)
class StrategyAnalyticsResult:
    """
    Pure v2.7 strategy analytics output.
    """

    overall_statistics: dict
    opportunity_rating_statistics: dict
    confidence_statistics: dict
    sector_statistics: dict
    holding_period_statistics: dict
    expectancy_statistics: dict
    risk_reward_statistics: dict
    top_performing_rating: str | None
    worst_performing_rating: str | None
    top_sector: str | None
    worst_sector: str | None
    warnings: list[str] = field(default_factory=list)


class StrategyAnalyticsCalculator:
    """
    Evaluate Institutional Bounce strategy performance from paper trades.

    These are v2.7 placeholder heuristics:
    - completed trades are exited trades, or records with valid entry/exit prices
    - return percent uses actual_return when supplied, otherwise entry/exit prices
    - expectancy is the average completed-trade return percent
    - win rate is wins divided by completed trades with classifiable returns
    - grouping statistics count completed trades only
    """

    WIN_STATUSES = {"Exited Win"}
    LOSS_STATUSES = {"Exited Loss"}
    INCOMPLETE_STATUSES = {"Watching", "Entered", "Cancelled"}
    RISK_REWARD_BUCKETS = ["<1.5", "1.5-2", "2-3", "3-5", ">5"]
    HOLDING_BUCKETS = ["0-5 days", "6-10 days", "11-20 days", ">20 days"]

    def calculate(self, trades):
        trades = list(trades or [])
        warnings = []
        completed = []

        for trade in trades:
            record = self.completed_record(trade, warnings)
            if record is not None:
                completed.append(record)

        returns = [record["return_pct"] for record in completed]
        wins = [record for record in completed if record["return_pct"] >= 0]
        holding_days = [
            record["holding_days"]
            for record in completed
            if record["holding_days"] is not None
        ]
        risk_rewards = [
            record["risk_reward"]
            for record in completed
            if record["risk_reward"] is not None
        ]

        if not completed:
            warnings.append("No completed trades")

        opportunity_stats = self.group_statistics(completed, "opportunity_rating")
        confidence_stats = self.group_statistics(completed, "confidence")
        sector_stats = self.group_statistics(completed, "sector")

        top_rating, worst_rating = self.top_and_worst(opportunity_stats)
        top_sector, worst_sector = self.top_and_worst(sector_stats)

        return StrategyAnalyticsResult(
            overall_statistics={
                "total_trades": len(trades),
                "completed_trades": len(completed),
                "win_rate": self.rate(len(wins), len(completed)),
                "average_return": self.average(returns),
                "median_return": self.median(returns),
                "expectancy": self.average(returns),
                "average_holding_days": self.average(holding_days),
            },
            opportunity_rating_statistics=opportunity_stats,
            confidence_statistics=confidence_stats,
            sector_statistics=sector_stats,
            holding_period_statistics=self.holding_distribution(holding_days),
            expectancy_statistics={
                "expectancy": self.average(returns),
                "average_return": self.average(returns),
                "median_return": self.median(returns),
                "positive_expectancy": self.average(returns) > 0,
                "sample_size": len(completed),
            },
            risk_reward_statistics={
                "average_risk_reward": self.average(risk_rewards),
                "distribution": self.risk_reward_distribution(risk_rewards),
            },
            top_performing_rating=top_rating,
            worst_performing_rating=worst_rating,
            top_sector=top_sector,
            worst_sector=worst_sector,
            warnings=self.dedupe(warnings),
        )

    @classmethod
    def completed_record(cls, trade, warnings):
        status = cls.text_value(trade, "status")
        entry_price = cls.numeric_value(trade, "entry_price")
        exit_price = cls.numeric_value(trade, "exit_price")
        actual_return = cls.numeric_value(trade, "actual_return")

        is_completed_status = status in cls.WIN_STATUSES or status in cls.LOSS_STATUSES
        has_price_completion = entry_price is not None and exit_price is not None

        if not is_completed_status and not has_price_completion:
            return None

        return_pct = actual_return

        if return_pct is None:
            return_pct = cls.return_pct(entry_price, exit_price, warnings)

        if return_pct is None:
            return None

        return {
            "ticker": cls.text_value(trade, "ticker"),
            "sector": cls.text_value(trade, "sector") or "Unknown",
            "opportunity_rating": (
                cls.text_value(trade, "opportunity_rating") or "Unknown"
            ),
            "confidence": cls.text_value(trade, "confidence") or "Unknown",
            "status": status or "Unknown",
            "return_pct": cls.round_value(return_pct),
            "holding_days": cls.holding_days(trade, warnings),
            "risk_reward": cls.numeric_value(trade, "risk_reward"),
        }

    @classmethod
    def return_pct(cls, entry_price, exit_price, warnings):
        if entry_price is None:
            warnings.append("Missing entry price")
            return None

        if exit_price is None:
            warnings.append("Missing exit price")
            return None

        if entry_price <= 0 or exit_price < 0:
            warnings.append("Invalid price data")
            return None

        return ((exit_price - entry_price) / entry_price) * 100.0

    @classmethod
    def holding_days(cls, trade, warnings):
        entry_date = cls.date_value(trade, "entry_date")
        exit_date = cls.date_value(trade, "exit_date")

        if entry_date is None or exit_date is None:
            warnings.append("Missing dates")
            return None

        days = (exit_date - entry_date).days

        if days < 0:
            warnings.append("Missing dates")
            return None

        return days

    @classmethod
    def group_statistics(cls, records, key):
        groups = {}

        for record in records:
            group = record[key] or "Unknown"
            groups.setdefault(group, []).append(record)

        return {
            group: cls.stats_for_records(group_records)
            for group, group_records in groups.items()
        }

    @classmethod
    def stats_for_records(cls, records):
        returns = [record["return_pct"] for record in records]
        wins = [record for record in records if record["return_pct"] >= 0]

        return {
            "trade_count": len(records),
            "win_rate": cls.rate(len(wins), len(records)),
            "average_return": cls.average(returns),
        }

    @classmethod
    def risk_reward_distribution(cls, values):
        distribution = {bucket: 0 for bucket in cls.RISK_REWARD_BUCKETS}

        for value in values:
            distribution[cls.risk_reward_bucket(value)] += 1

        return distribution

    @classmethod
    def holding_distribution(cls, values):
        distribution = {bucket: 0 for bucket in cls.HOLDING_BUCKETS}

        for value in values:
            distribution[cls.holding_bucket(value)] += 1

        return distribution

    @staticmethod
    def risk_reward_bucket(value):
        if value < 1.5:
            return "<1.5"
        if value < 2:
            return "1.5-2"
        if value < 3:
            return "2-3"
        if value <= 5:
            return "3-5"
        return ">5"

    @staticmethod
    def holding_bucket(value):
        if value <= 5:
            return "0-5 days"
        if value <= 10:
            return "6-10 days"
        if value <= 20:
            return "11-20 days"
        return ">20 days"

    @staticmethod
    def top_and_worst(statistics):
        if not statistics:
            return None, None

        ranked = sorted(
            statistics.items(),
            key=lambda item: (item[1]["average_return"], item[1]["win_rate"], item[0]),
        )

        return ranked[-1][0], ranked[0][0]

    @classmethod
    def numeric_value(cls, trade, key):
        value = cls.value_for(trade, key)

        if value is None or value == "":
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @classmethod
    def text_value(cls, trade, key):
        value = cls.value_for(trade, key)

        if value is None:
            return None

        text = str(value).strip()

        return text or None

    @classmethod
    def date_value(cls, trade, key):
        value = cls.value_for(trade, key)

        if value is None or value == "":
            return None

        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, date):
            return value

        text = str(value).strip()

        if not text:
            return None

        try:
            return datetime.fromisoformat(text).date()
        except ValueError:
            try:
                return datetime.strptime(text[:10], "%Y-%m-%d").date()
            except ValueError:
                return None

    @staticmethod
    def value_for(trade, key):
        if trade is None:
            return None

        if isinstance(trade, dict):
            return trade.get(key)

        return getattr(trade, key, None)

    @classmethod
    def rate(cls, count, total):
        if total <= 0:
            return 0.0

        return cls.round_value((count / total) * 100.0)

    @classmethod
    def average(cls, values):
        if not values:
            return 0.0

        return cls.round_value(sum(values) / len(values))

    @classmethod
    def median(cls, values):
        if not values:
            return 0.0

        sorted_values = sorted(values)
        midpoint = len(sorted_values) // 2

        if len(sorted_values) % 2 == 1:
            return cls.round_value(sorted_values[midpoint])

        return cls.round_value(
            (sorted_values[midpoint - 1] + sorted_values[midpoint]) / 2.0
        )

    @staticmethod
    def round_value(value):
        return round(float(value), 6)

    @staticmethod
    def dedupe(values):
        deduped = []

        for value in values:
            if value not in deduped:
                deduped.append(value)

        return deduped
