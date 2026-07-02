from __future__ import annotations

from datetime import date, datetime

from backtesting.backtest_models import BacktestStatistics, BacktestTrade
from backtesting.backtest_result import BacktestResult
from backtesting.equity_curve import EquityCurve
from backtesting.strategy import BacktestStrategy


class BacktestEngine:
    """
    Deterministic architecture shell for historical strategy evaluation.
    """

    INITIAL_EQUITY = 100_000.0

    def run_backtest(self, historical_candidates, strategy) -> BacktestResult:
        if not isinstance(strategy, BacktestStrategy):
            raise TypeError("strategy must implement BacktestStrategy.")

        candidates = historical_candidates or []
        trades = list(strategy.generate_trades(candidates))
        warnings = []

        if trades:
            self.validate_trades(trades)
        else:
            trades = [
                self.simulate_trade(candidate, strategy)
                for candidate in candidates
            ]

        if not candidates:
            warnings.append("No historical candidates supplied.")

        ordered_trades = self.chronological_trades(trades)
        equity_curve = self.calculate_equity_curve(ordered_trades)

        return BacktestResult(
            trades=ordered_trades,
            statistics=self.calculate_statistics(ordered_trades),
            equity_curve=equity_curve,
            portfolio_analytics=self.calculate_portfolio_analytics(
                ordered_trades,
                equity_curve,
            ),
            warnings=warnings,
        )

    def simulate_trade(self, historical_candidate, strategy=None) -> BacktestTrade:
        candidate = self.object_mapping(historical_candidate)
        prices = self.normalized_prices(self.value_for(candidate, "prices", "price_history", "history"))

        if not prices:
            raise ValueError("Historical candidate requires price history.")

        ticker = self.first_value(candidate, "ticker", "symbol")
        if not ticker:
            raise ValueError("Historical candidate requires a ticker.")

        entry_index = self.entry_index(
            prices,
            self.first_value(candidate, "entry_date", "signal_date", "date"),
        )
        entry_row = prices[entry_index]
        entry_price = self.numeric_value(
            self.first_value(
                candidate,
                "entry_price",
                "recommended_entry",
                "entry",
            )
        )
        if entry_price is None:
            entry_price = self.numeric_value(self.first_value(entry_row, "close", "open"))

        stop_price = self.numeric_value(
            self.first_value(candidate, "stop_price", "recommended_stop", "stop")
        )
        target_price = self.numeric_value(
            self.first_value(candidate, "target_price", "target_1", "target")
        )
        max_hold_days = self.max_hold_days(candidate, strategy)

        if entry_price is None or entry_price <= 0:
            raise ValueError("Historical candidate requires a positive entry price.")

        if stop_price is None or stop_price < 0:
            raise ValueError("Historical candidate requires a non-negative stop price.")

        if target_price is None or target_price < 0:
            raise ValueError("Historical candidate requires a non-negative target price.")

        exit_row, exit_price, exit_reason = self.exit_for_trade(
            prices=prices,
            entry_index=entry_index,
            entry_price=entry_price,
            stop_price=stop_price,
            target_price=target_price,
            max_hold_days=max_hold_days,
        )

        return BacktestTrade(
            ticker=str(ticker),
            entry_date=self.first_value(entry_row, "date"),
            exit_date=self.first_value(exit_row, "date"),
            entry_price=entry_price,
            exit_price=exit_price,
            stop_price=stop_price,
            target_price=target_price,
            exit_reason=exit_reason,
            opportunity_score=self.numeric_value(
                self.first_value(
                    candidate,
                    "opportunity_score",
                    "opportunity_rating_score",
                    "primary_score_value",
                )
            ),
            confidence=self.optional_text(self.first_value(candidate, "confidence")),
            warnings=list(self.first_value(candidate, "warnings") or []),
        )

    @classmethod
    def exit_for_trade(
        cls,
        prices,
        entry_index,
        entry_price,
        stop_price,
        target_price,
        max_hold_days,
    ):
        entry_date = cls.date_value(cls.first_value(prices[entry_index], "date"))
        last_allowed_index = len(prices) - 1

        for index in range(entry_index + 1, len(prices)):
            row = prices[index]
            high = cls.numeric_value(cls.first_value(row, "high", "close"))
            low = cls.numeric_value(cls.first_value(row, "low", "close"))
            current_date = cls.date_value(cls.first_value(row, "date"))

            if low is not None and low <= stop_price:
                return row, stop_price, "stop_reached"

            if high is not None and high >= target_price:
                return row, target_price, "target_reached"

            if max_hold_days is not None and (current_date - entry_date).days >= max_hold_days:
                close = cls.numeric_value(cls.first_value(row, "close"))
                return row, close if close is not None else entry_price, "maximum_holding_period"

        final_row = prices[last_allowed_index]
        final_close = cls.numeric_value(cls.first_value(final_row, "close"))
        return (
            final_row,
            final_close if final_close is not None else entry_price,
            "end_of_available_data",
        )

    @classmethod
    def calculate_statistics(cls, trades: list[BacktestTrade]) -> BacktestStatistics:
        total = len(trades)

        if total == 0:
            return BacktestStatistics()

        returns = [trade.return_pct for trade in trades]
        gains = [value for value in returns if value > 0]
        losses = [value for value in returns if value < 0]
        wins = len(gains)
        loss_count = len(losses)
        win_rate = wins / total
        average_gain = sum(gains) / len(gains) if gains else 0.0
        average_loss = sum(losses) / len(losses) if losses else 0.0
        expectancy = (win_rate * average_gain) + ((1.0 - win_rate) * average_loss)
        average_hold_days = sum(trade.hold_days for trade in trades) / total
        profit_factor = cls.profit_factor(trades)

        return BacktestStatistics(
            total_trades=total,
            wins=wins,
            losses=loss_count,
            win_rate=win_rate,
            average_gain=average_gain,
            average_loss=average_loss,
            expectancy=expectancy,
            average_hold_days=average_hold_days,
            profit_factor=profit_factor,
            max_drawdown=cls.max_drawdown(trades),
            largest_winner=max(gains) if gains else 0.0,
            largest_loser=min(losses) if losses else 0.0,
        )

    @classmethod
    def calculate_equity_curve(
        cls,
        trades: list[BacktestTrade],
        initial_equity: float | None = None,
    ) -> EquityCurve:
        return EquityCurve.from_trades(
            trades,
            initial_equity=initial_equity or cls.INITIAL_EQUITY,
        )

    @classmethod
    def calculate_portfolio_analytics(
        cls,
        trades: list[BacktestTrade],
        equity_curve: EquityCurve | None = None,
    ) -> dict:
        if equity_curve is None:
            equity_curve = cls.calculate_equity_curve(trades)

        if not trades:
            return {
                "total_return": 0.0,
                "annualized_return": 0.0,
                "average_trade_return": 0.0,
                "median_trade_return": 0.0,
                "best_trade": 0.0,
                "worst_trade": 0.0,
                "average_holding_period": 0.0,
                "max_drawdown": 0.0,
                "average_drawdown": 0.0,
                "recovery_periods": [],
                "rolling_equity_highs": [],
            }

        returns = [trade.return_pct for trade in trades]

        return {
            "total_return": equity_curve.cumulative_return,
            "annualized_return": equity_curve.cagr,
            "average_trade_return": sum(returns) / len(returns),
            "median_trade_return": cls.median(returns),
            "best_trade": max(returns),
            "worst_trade": min(returns),
            "average_holding_period": (
                sum(trade.hold_days for trade in trades) / len(trades)
            ),
            "max_drawdown": min(equity_curve.drawdown_series)
            if equity_curve.drawdown_series
            else 0.0,
            "average_drawdown": equity_curve.average_drawdown,
            "recovery_periods": list(equity_curve.recovery_periods),
            "rolling_equity_highs": list(equity_curve.rolling_equity_highs),
        }

    @staticmethod
    def validate_trades(trades):
        for trade in trades:
            if not isinstance(trade, BacktestTrade):
                raise TypeError("strategy generated an invalid trade.")

    @classmethod
    def chronological_trades(cls, trades):
        return sorted(
            trades,
            key=lambda trade: cls.date_value(trade.exit_date),
        )

    @staticmethod
    def median(values):
        ordered = sorted(values)
        count = len(ordered)

        if count == 0:
            return 0.0

        middle = count // 2

        if count % 2 == 1:
            return ordered[middle]

        return (ordered[middle - 1] + ordered[middle]) / 2.0

    @staticmethod
    def max_drawdown(trades: list[BacktestTrade]) -> float:
        equity = 0.0
        peak = 0.0
        max_drawdown = 0.0

        for trade in trades:
            equity += trade.profit_loss
            peak = max(peak, equity)
            drawdown = equity - peak
            max_drawdown = min(max_drawdown, drawdown)

        return max_drawdown

    @staticmethod
    def profit_factor(trades: list[BacktestTrade]) -> float:
        gross_profit = sum(
            trade.profit_loss
            for trade in trades
            if trade.profit_loss > 0
        )
        gross_loss = abs(
            sum(
                trade.profit_loss
                for trade in trades
                if trade.profit_loss < 0
            )
        )

        if gross_loss == 0:
            return gross_profit if gross_profit > 0 else 0.0

        return gross_profit / gross_loss

    @classmethod
    def normalized_prices(cls, prices):
        if not isinstance(prices, list):
            return []

        normalized = [cls.object_mapping(price) for price in prices]
        return sorted(
            normalized,
            key=lambda row: cls.date_value(cls.first_value(row, "date")),
        )

    @classmethod
    def entry_index(cls, prices, entry_date):
        if entry_date is None:
            return 0

        requested = cls.date_value(entry_date)

        for index, row in enumerate(prices):
            if cls.date_value(cls.first_value(row, "date")) >= requested:
                return index

        raise ValueError("Entry date is outside available price history.")

    @classmethod
    def max_hold_days(cls, candidate, strategy):
        value = cls.first_value(candidate, "max_hold_days", "maximum_hold_days")

        if value is None and strategy is not None:
            value = getattr(strategy, "max_hold_days", None)

        if value is None:
            return None

        try:
            days = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("max_hold_days must be an integer.") from exc

        if days <= 0:
            raise ValueError("max_hold_days must be positive.")

        return days

    @staticmethod
    def object_mapping(value):
        if isinstance(value, dict):
            return value

        if hasattr(value, "__dict__"):
            return vars(value)

        return {}

    @classmethod
    def value_for(cls, source, *names):
        for name in names:
            value = cls.first_value(source, name)
            if value is not None:
                return value

        return None

    @staticmethod
    def first_value(source, *names):
        if source is None:
            return None

        for name in names:
            if isinstance(source, dict):
                value = source.get(name)
            else:
                value = getattr(source, name, None)

            if value is not None and value != "":
                return value

        return None

    @staticmethod
    def numeric_value(value):
        if value is None or value == "":
            return None

        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("Backtest numeric fields must be numeric.") from exc

    @staticmethod
    def date_value(value):
        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, date):
            return value

        try:
            return datetime.fromisoformat(str(value)).date()
        except (TypeError, ValueError) as exc:
            raise ValueError("Backtest price rows require date-like values.") from exc

    @staticmethod
    def optional_text(value):
        if value is None:
            return None

        return str(value)
