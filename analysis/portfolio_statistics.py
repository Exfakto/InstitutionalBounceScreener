"""
Portfolio and paper-trade statistics utilities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass(frozen=True)
class PortfolioStatisticsResult:
    """
    Pure v2.7 portfolio statistics output.
    """

    total_trades: int
    open_trades: int
    closed_trades: int
    winning_trades: int
    losing_trades: int
    cancelled_trades: int
    win_rate: float
    loss_rate: float
    average_gain_pct: float
    average_loss_pct: float
    average_return_pct: float
    total_return_pct: float
    profit_factor: float | None
    expectancy: float
    average_risk_reward: float
    best_trade: dict | None
    worst_trade: dict | None
    average_holding_days: float | None
    max_holding_days: int | None
    min_holding_days: int | None
    by_status: dict
    by_opportunity_rating: dict
    by_confidence: dict
    warnings: list[str] = field(default_factory=list)


class PortfolioStatisticsCalculator:
    """
    Calculate portfolio statistics from paper trade journal records.

    These are v2.7 placeholder heuristics:
    - closed wins/losses are inferred from explicit status first, then from
      exit_price versus entry_price
    - percent return = ((exit_price - entry_price) / entry_price) * 100
    - profit factor = total positive returns / absolute total negative returns
    - expectancy = average return percent per closed trade with valid prices
    - open and cancelled trades are counted but excluded from closed performance
    """

    OPEN_STATUSES = {"Watching", "Entered"}
    WIN_STATUSES = {"Exited Win"}
    LOSS_STATUSES = {"Exited Loss"}
    CANCELLED_STATUSES = {"Cancelled"}

    def calculate(self, trades):
        trades = list(trades or [])
        warnings = []
        returns = []
        gains = []
        losses = []
        holding_days = []
        risk_rewards = []
        best_trade = None
        worst_trade = None
        counts = {
            "total": len(trades),
            "open": 0,
            "closed": 0,
            "wins": 0,
            "losses": 0,
            "cancelled": 0,
        }
        by_status = {}
        by_opportunity_rating = {}
        by_confidence = {}

        for trade in trades:
            status = self.text_value(trade, "status") or "Unknown"
            by_status[status] = by_status.get(status, 0) + 1
            self.increment_breakdown(
                by_opportunity_rating,
                self.text_value(trade, "opportunity_rating"),
            )
            self.increment_breakdown(
                by_confidence,
                self.text_value(trade, "confidence"),
            )

            if status in self.CANCELLED_STATUSES:
                counts["cancelled"] += 1
                continue

            if status in self.OPEN_STATUSES:
                counts["open"] += 1
                self.warn_open_missing_data(trade, warnings)
                continue

            entry_price = self.numeric_value(trade, "entry_price")
            exit_price = self.numeric_value(trade, "exit_price")

            if status in self.WIN_STATUSES or status in self.LOSS_STATUSES:
                counts["closed"] += 1
            elif entry_price is not None and exit_price is not None:
                counts["closed"] += 1
            else:
                counts["open"] += 1
                self.warn_open_missing_data(trade, warnings)
                continue

            classification = self.closed_classification(
                status,
                entry_price,
                exit_price,
            )

            if classification == "win":
                counts["wins"] += 1
            elif classification == "loss":
                counts["losses"] += 1

            return_pct = self.return_pct(entry_price, exit_price, warnings)

            if return_pct is not None:
                rounded_return = self.round_value(return_pct)
                returns.append(rounded_return)

                if rounded_return >= 0:
                    gains.append(rounded_return)
                else:
                    losses.append(rounded_return)

                summary = self.trade_summary(trade, rounded_return)
                if best_trade is None or rounded_return > best_trade["return_pct"]:
                    best_trade = summary
                if worst_trade is None or rounded_return < worst_trade["return_pct"]:
                    worst_trade = summary

            days = self.holding_days(trade, warnings)
            if days is not None:
                holding_days.append(days)

            risk_reward = self.numeric_value(trade, "risk_reward")
            if risk_reward is not None:
                risk_rewards.append(risk_reward)

            if self.value_for(trade, "shares") in (None, ""):
                warnings.append("Missing shares")

        if counts["closed"] == 0:
            warnings.append("No closed trades")

        return PortfolioStatisticsResult(
            total_trades=counts["total"],
            open_trades=counts["open"],
            closed_trades=counts["closed"],
            winning_trades=counts["wins"],
            losing_trades=counts["losses"],
            cancelled_trades=counts["cancelled"],
            win_rate=self.rate(counts["wins"], counts["closed"]),
            loss_rate=self.rate(counts["losses"], counts["closed"]),
            average_gain_pct=self.average(gains),
            average_loss_pct=self.average(losses),
            average_return_pct=self.average(returns),
            total_return_pct=self.round_value(sum(returns)),
            profit_factor=self.profit_factor(gains, losses),
            expectancy=self.average(returns),
            average_risk_reward=self.average(risk_rewards),
            best_trade=best_trade,
            worst_trade=worst_trade,
            average_holding_days=self.average_or_none(holding_days),
            max_holding_days=max(holding_days) if holding_days else None,
            min_holding_days=min(holding_days) if holding_days else None,
            by_status=by_status,
            by_opportunity_rating=by_opportunity_rating,
            by_confidence=by_confidence,
            warnings=self.dedupe(warnings),
        )

    @classmethod
    def closed_classification(cls, status, entry_price, exit_price):
        if status in cls.WIN_STATUSES:
            return "win"

        if status in cls.LOSS_STATUSES:
            return "loss"

        if entry_price is None or exit_price is None:
            return None

        if exit_price >= entry_price:
            return "win"

        return "loss"

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
    def warn_open_missing_data(cls, trade, warnings):
        if cls.numeric_value(trade, "entry_price") is None:
            warnings.append("Missing entry price")

        if cls.value_for(trade, "shares") in (None, ""):
            warnings.append("Missing shares")

    @classmethod
    def trade_summary(cls, trade, return_pct):
        return {
            "ticker": cls.text_value(trade, "ticker"),
            "status": cls.text_value(trade, "status"),
            "return_pct": return_pct,
        }

    @classmethod
    def increment_breakdown(cls, breakdown, value):
        key = value or "Unknown"
        breakdown[key] = breakdown.get(key, 0) + 1

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
    def average_or_none(cls, values):
        if not values:
            return None

        return cls.average(values)

    @classmethod
    def profit_factor(cls, gains, losses):
        total_gains = sum(gain for gain in gains if gain > 0)
        total_losses = abs(sum(loss for loss in losses if loss < 0))

        if total_losses == 0:
            if total_gains > 0:
                return None
            return 0.0

        return cls.round_value(total_gains / total_losses)

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
