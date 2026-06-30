"""
Institutional momentum calculation utilities.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass(frozen=True)
class InstitutionalMomentumResult:
    """
    Pure institutional momentum calculation output.
    """

    current_ownership_pct: float | None
    previous_ownership_pct: float | None
    ownership_change_pct: float | None
    ownership_trend: str
    consecutive_increase_quarters: int
    consecutive_decrease_quarters: int
    insider_buying_score: float
    insider_selling_score: float
    momentum_score: float
    warnings: list[str] = field(default_factory=list)


class InstitutionalMomentumCalculator:
    """
    Calculate institutional accumulation or distribution momentum.

    The score is a v2.1 placeholder heuristic:
    - rising ownership and consecutive accumulation improve momentum
    - falling ownership and consecutive distribution reduce momentum
    - new large buyers help, while new large sellers hurt
    - insider buying helps, while insider selling hurts
    """

    def calculate(
        self,
        current_ownership,
        previous_ownership=None,
        ownership_history=None,
        insider_metrics=None,
    ) -> InstitutionalMomentumResult:
        warnings = []
        history = self.normalized_history(ownership_history)
        current = self.number_or_none(current_ownership)

        if current is None and history:
            current = history[-1]

        previous = self.number_or_none(previous_ownership)

        if previous is None and len(history) >= 2:
            previous = history[-2]

        if current is None:
            warnings.append("Missing current institutional ownership")

        if previous is None:
            warnings.append("Missing previous institutional ownership")

        ownership_change = None

        if current is not None and previous is not None:
            ownership_change = current - previous

        trend = self.ownership_trend(ownership_change)
        increases = self.consecutive_increases(history)
        decreases = self.consecutive_decreases(history)
        insider_buying = self.insider_buying_score(insider_metrics or {})
        insider_selling = self.insider_selling_score(insider_metrics or {})
        score = self.momentum_score(
            ownership_change=ownership_change,
            consecutive_increase_quarters=increases,
            consecutive_decrease_quarters=decreases,
            new_large_buyers=self.number_or_none(
                self.value(insider_metrics or {}, "new_large_buyers")
            ),
            new_large_sellers=self.number_or_none(
                self.value(insider_metrics or {}, "new_large_sellers")
            ),
            insider_buying_score=insider_buying,
            insider_selling_score=insider_selling,
        )

        if not history:
            warnings.append("Missing ownership history")

        if not insider_metrics:
            warnings.append("Missing insider metrics")

        return InstitutionalMomentumResult(
            current_ownership_pct=current,
            previous_ownership_pct=previous,
            ownership_change_pct=ownership_change,
            ownership_trend=trend,
            consecutive_increase_quarters=increases,
            consecutive_decrease_quarters=decreases,
            insider_buying_score=insider_buying,
            insider_selling_score=insider_selling,
            momentum_score=score,
            warnings=warnings,
        )

    def momentum_score(
        self,
        ownership_change,
        consecutive_increase_quarters,
        consecutive_decrease_quarters,
        new_large_buyers,
        new_large_sellers,
        insider_buying_score,
        insider_selling_score,
    ):
        score = 50.0

        if ownership_change is not None:
            score += max(-25.0, min(25.0, ownership_change * 5.0))

        score += min(15.0, consecutive_increase_quarters * 5.0)
        score -= min(15.0, consecutive_decrease_quarters * 5.0)

        if new_large_buyers is not None:
            score += min(10.0, new_large_buyers * 2.0)

        if new_large_sellers is not None:
            score -= min(10.0, new_large_sellers * 2.0)

        score += insider_buying_score * 0.15
        score -= insider_selling_score * 0.15

        return self.clamp(score)

    def insider_buying_score(self, metrics):
        explicit = self.number_or_none(self.value(metrics, "insider_buying_score"))

        if explicit is not None:
            return self.clamp(explicit)

        flag = self.value(metrics, "insider_buying_flag")

        return 75.0 if self.truthy(flag) else 0.0

    def insider_selling_score(self, metrics):
        explicit = self.number_or_none(self.value(metrics, "insider_selling_score"))

        if explicit is not None:
            return self.clamp(explicit)

        flag = self.value(metrics, "insider_selling_flag")

        return 75.0 if self.truthy(flag) else 0.0

    @staticmethod
    def ownership_trend(ownership_change):
        if ownership_change is None:
            return "unknown"

        if ownership_change > 0:
            return "increasing"

        if ownership_change < 0:
            return "decreasing"

        return "flat"

    @classmethod
    def normalized_history(cls, ownership_history):
        if ownership_history is None:
            return []

        values = []

        for item in ownership_history:
            if isinstance(item, dict) or hasattr(item, "keys"):
                value = cls.value(item, "institutional_ownership_pct")
            else:
                value = item

            number = cls.number_or_none(value)

            if number is not None:
                values.append(number)

        return values

    @staticmethod
    def consecutive_increases(values):
        count = 0

        for index in range(len(values) - 1, 0, -1):
            if values[index] > values[index - 1]:
                count += 1
            else:
                break

        return count

    @staticmethod
    def consecutive_decreases(values):
        count = 0

        for index in range(len(values) - 1, 0, -1):
            if values[index] < values[index - 1]:
                count += 1
            else:
                break

        return count

    @staticmethod
    def value(row, key):
        if row is None:
            return None

        if isinstance(row, dict):
            return row.get(key)

        try:
            return row[key]
        except (IndexError, KeyError, TypeError):
            return None

    @staticmethod
    def number_or_none(value):
        if value is None or value == "":
            return None

        if pd.isna(value):
            return None

        return float(value)

    @staticmethod
    def truthy(value):
        if value is None or value == "":
            return False

        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "y"}

        return bool(value)

    @staticmethod
    def clamp(value):
        return max(0.0, min(100.0, float(value)))
