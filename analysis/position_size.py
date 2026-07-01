"""
Position sizing utilities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import floor

from analysis.score_result import ScoreResult


@dataclass(frozen=True)
class PositionSizeResult:
    """
    Pure v2.4 position sizing output.
    """

    shares: int
    position_value: float
    risk_amount: float
    risk_per_share: float
    capital_used: float
    position_percent: float
    remaining_capital: float
    is_valid: bool
    warnings: list[str] = field(default_factory=list)


class PositionSizeCalculator:
    """
    Calculate position size from account risk and stop distance.

    These are v2.4 placeholder heuristics:
    - risk_amount = account_size * risk_percent
    - risk_per_share = entry_price - stop_price
    - shares are floored to whole shares
    - account size and optional maximum position percent cap position value
    - invalid or missing inputs return a safe zero-sized result
    """

    DEFAULT_MINIMUM_POSITION_SIZE = 1

    def calculate(self, metrics):
        metrics = metrics or {}
        warnings = []
        fatal_warnings = []
        account_size = self.metric(metrics, "account_size")
        risk_percent = self.metric(metrics, "risk_percent")
        entry_price = self.metric(metrics, "entry_price")
        stop_price = self.metric(metrics, "stop_price")
        maximum_position_percent = self.metric(metrics, "maximum_position_percent")
        minimum_position_size = self.metric(metrics, "minimum_position_size")

        if account_size is None or account_size <= 0:
            fatal_warnings.append("Missing inputs")
            fatal_warnings.append("Insufficient account size")

        if risk_percent is None:
            fatal_warnings.append("Missing inputs")
        elif risk_percent <= 0:
            fatal_warnings.append("Risk too small")
        elif risk_percent > 5:
            warnings.append("Risk too large")

        if entry_price is None or stop_price is None:
            fatal_warnings.append("Missing inputs")
            fatal_warnings.append("Invalid prices")
        elif entry_price <= 0 or stop_price <= 0:
            fatal_warnings.append("Invalid prices")

        if fatal_warnings:
            return self.zero_result(self.dedupe(fatal_warnings + warnings))

        risk_per_share = entry_price - stop_price

        if risk_per_share <= 0:
            warnings.append("Stop above entry")
            return self.zero_result(warnings, risk_per_share=max(0.0, risk_per_share))

        risk_amount = account_size * (risk_percent / 100.0)

        if risk_amount < risk_per_share:
            warnings.append("Risk too small")

        raw_shares = floor(risk_amount / risk_per_share)

        if raw_shares <= 0:
            return self.zero_result(
                self.dedupe(warnings + ["Risk too small"]),
                risk_amount=risk_amount,
                risk_per_share=risk_per_share,
            )

        shares = raw_shares
        account_cap_shares = floor(account_size / entry_price)

        if shares > account_cap_shares:
            shares = account_cap_shares
            warnings.append("Position exceeds account")

        if maximum_position_percent is not None:
            max_position_value = account_size * (maximum_position_percent / 100.0)
            max_position_shares = floor(max_position_value / entry_price)

            if shares > max_position_shares:
                shares = max_position_shares
                warnings.append("Position limited by maximum position percent")

        minimum_size = int(minimum_position_size or self.DEFAULT_MINIMUM_POSITION_SIZE)

        if shares < minimum_size:
            warnings.append("Risk too small")

        if shares <= 0:
            return self.zero_result(
                self.dedupe(warnings),
                risk_amount=risk_amount,
                risk_per_share=risk_per_share,
            )

        capital_used = shares * entry_price
        position_percent = (capital_used / account_size) * 100.0
        remaining_capital = max(0.0, account_size - capital_used)

        return PositionSizeResult(
            shares=int(shares),
            position_value=self.round_value(capital_used),
            risk_amount=self.round_value(risk_amount),
            risk_per_share=self.round_value(risk_per_share),
            capital_used=self.round_value(capital_used),
            position_percent=self.round_value(position_percent),
            remaining_capital=self.round_value(remaining_capital),
            is_valid=shares >= minimum_size,
            warnings=self.dedupe(warnings),
        )

    @staticmethod
    def metric(metrics, name):
        value = metrics.get(name)

        if isinstance(value, ScoreResult):
            value = value.value

        if value is None or value == "":
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @classmethod
    def zero_result(
        cls,
        warnings,
        risk_amount=0.0,
        risk_per_share=0.0,
    ):
        return PositionSizeResult(
            shares=0,
            position_value=0.0,
            risk_amount=cls.round_value(max(0.0, risk_amount)),
            risk_per_share=cls.round_value(max(0.0, risk_per_share)),
            capital_used=0.0,
            position_percent=0.0,
            remaining_capital=0.0,
            is_valid=False,
            warnings=cls.dedupe(warnings),
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
