from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from statistics import median
from uuid import uuid4


@dataclass(frozen=True)
class BacktestSignal:
    ticker: str
    signal_date: str
    entry_price: float
    support_zone: dict | None = None
    final_score: float | None = None
    grade: str | None = None
    confidence_level: str | None = None
    setup_label: str | None = None
    source_run_id: str | None = None


@dataclass(frozen=True)
class BacktestTradeResult:
    ticker: str
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    return_pct: float
    max_gain_pct: float
    max_drawdown_pct: float
    holding_days: int
    exit_reason: str
    final_score: float | None = None
    grade: str | None = None
    confidence_level: str | None = None
    setup_label: str | None = None
    source_run_id: str | None = None
    signal_date: str | None = None
    warnings: list[str] = field(default_factory=list)

    @property
    def is_win(self):
        return self.return_pct > 0


@dataclass(frozen=True)
class BacktestConfig:
    min_score: float = 60.0
    allowed_grades: tuple[str, ...] = ("A+", "A", "B", "C")
    max_holding_days: int = 30
    profit_target_pct: float = 20.0
    stop_loss_pct: float = 8.0
    entry_rule: str = "next_close"
    exit_rule: str = "target_stop_or_max_hold"


@dataclass(frozen=True)
class BacktestRunResult:
    run_id: str
    config: BacktestConfig
    trades: list[BacktestTradeResult] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class BacktestMetricsService:
    def calculate(self, trades, rejected_signal_count=0, invalid_signal_count=0):
        trades = list(trades or [])
        returns = [trade.return_pct for trade in trades]
        winners = [value for value in returns if value > 0]
        losers = [value for value in returns if value < 0]
        gross_profit = sum(winners)
        gross_loss = abs(sum(losers))
        total = len(trades)
        win_rate = len(winners) / total if total else 0.0
        average_winner = sum(winners) / len(winners) if winners else 0.0
        average_loser = sum(losers) / len(losers) if losers else 0.0
        profit_factor = gross_profit / gross_loss if gross_loss else (gross_profit if gross_profit else 0.0)
        expectancy = (win_rate * average_winner) + ((1 - win_rate) * average_loser) if total else 0.0
        return {
            "total_trades": total,
            "win_rate": win_rate,
            "average_return": sum(returns) / total if total else 0.0,
            "median_return": median(returns) if returns else 0.0,
            "average_winner": average_winner,
            "average_loser": average_loser,
            "profit_factor": profit_factor,
            "max_drawdown": min((trade.max_drawdown_pct for trade in trades), default=0.0),
            "expectancy": expectancy,
            "rejected_signal_count": int(rejected_signal_count or 0),
            "invalid_signal_count": int(invalid_signal_count or 0),
        }


class BacktestEngine:
    def __init__(self, repository=None, metrics_service=None):
        self.repository = repository
        self.metrics_service = metrics_service or BacktestMetricsService()

    def ranked_candidates_to_signals(self, candidates, config=None):
        config = config or BacktestConfig()
        signals = []
        warnings = []
        rejected = 0
        invalid = 0
        for candidate in candidates or []:
            signal, warning = self.signal_from_candidate(candidate, config)
            if signal is not None:
                signals.append(signal)
            elif warning and warning.startswith("Rejected"):
                rejected += 1
                warnings.append(warning)
            else:
                invalid += 1
                warnings.append(warning or "Invalid backtest signal")
        return signals, warnings, rejected, invalid

    def signal_from_candidate(self, candidate, config):
        ticker = self.value(candidate, "ticker")
        final_score = self.number(self.value(candidate, "final_score"))
        grade = self.value(candidate, "grade")
        if not ticker:
            return None, "Invalid signal: ticker missing"
        if final_score is not None and final_score < config.min_score:
            return None, f"Rejected {ticker}: score below {config.min_score:g}"
        if config.allowed_grades and grade not in config.allowed_grades:
            return None, f"Rejected {ticker}: grade {grade or 'N/A'} not allowed"

        signal_date = (
            self.value(candidate, "signal_date")
            or self.value(candidate, "created_at")
            or self.value(self.value(candidate, "source"), "created_at")
        )
        entry_price = self.number(
            self.value(candidate, "entry_price")
            or self.value(candidate, "current_price")
            or self.value(candidate, "price")
        )
        if not signal_date:
            return None, f"Invalid signal {ticker}: signal date missing"
        if entry_price is None or entry_price <= 0:
            return None, f"Invalid signal {ticker}: entry price missing"
        return BacktestSignal(
            ticker=str(ticker).upper(),
            signal_date=str(signal_date),
            entry_price=entry_price,
            support_zone=self.value(candidate, "support_zone"),
            final_score=final_score,
            grade=grade,
            confidence_level=self.value(candidate, "confidence_level"),
            setup_label=self.value(candidate, "setup_label"),
            source_run_id=(
                self.value(candidate, "source_run_id")
                or self.value(candidate, "run_id")
                or self.value(self.value(candidate, "source"), "run_id")
            ),
        ), None

    def run_backtest(self, ranked_candidates, config=None, run_id=None):
        config = config or BacktestConfig()
        run_id = str(run_id or uuid4())
        signals, warnings, rejected, invalid = self.ranked_candidates_to_signals(
            ranked_candidates,
            config=config,
        )
        trades = []
        for signal in signals:
            trade, trade_warnings = self.simulate_signal(signal, config)
            warnings.extend(trade_warnings)
            if trade is None:
                invalid += 1
            else:
                trades.append(trade)
        metrics = self.metrics_service.calculate(
            trades,
            rejected_signal_count=rejected,
            invalid_signal_count=invalid,
        )
        return BacktestRunResult(
            run_id=run_id,
            config=config,
            trades=trades,
            metrics=metrics,
            warnings=self.unique(warnings),
            errors=[],
        )

    def run_batch_backtest(self, candidate_batches, config=None):
        return [
            self.run_backtest(batch, config=config)
            for batch in (candidate_batches or [])
        ]

    def simulate_signal(self, signal, config):
        prices = self.fetch_prices(signal.ticker)
        warnings = []
        if not prices:
            return None, [f"{signal.ticker}: missing OHLCV data"]
        entry_index = self.entry_index(prices, signal.signal_date)
        if entry_index is None:
            return None, [f"{signal.ticker}: insufficient OHLCV data after signal"]
        entry_row = prices[entry_index]
        entry_price = (
            self.number(self.value(entry_row, "close"))
            if config.entry_rule == "next_close"
            else signal.entry_price
        )
        if entry_price is None or entry_price <= 0:
            return None, [f"{signal.ticker}: invalid entry price"]
        target = entry_price * (1 + config.profit_target_pct / 100)
        stop = entry_price * (1 - config.stop_loss_pct / 100)
        max_gain = 0.0
        max_drawdown = 0.0
        exit_row = entry_row
        exit_price = entry_price
        exit_reason = "max_holding_days"
        entry_date = self.date_value(self.value(entry_row, "date"))

        for row in prices[entry_index + 1:]:
            current_date = self.date_value(self.value(row, "date"))
            holding_days = (current_date - entry_date).days
            high = self.number(self.value(row, "high") or self.value(row, "close"))
            low = self.number(self.value(row, "low") or self.value(row, "close"))
            close = self.number(self.value(row, "close")) or entry_price
            if high is not None:
                max_gain = max(max_gain, ((high - entry_price) / entry_price) * 100)
            if low is not None:
                max_drawdown = min(max_drawdown, ((low - entry_price) / entry_price) * 100)
            exit_row = row
            exit_price = close

            if low is not None and low <= stop:
                exit_price = stop
                exit_reason = "stop_loss"
                break
            if high is not None and high >= target:
                exit_price = target
                exit_reason = "profit_target"
                break
            if holding_days >= config.max_holding_days:
                exit_reason = "max_holding_days"
                break
        else:
            exit_reason = "end_of_data"

        exit_date = str(self.value(exit_row, "date"))
        return_pct = ((exit_price - entry_price) / entry_price) * 100
        return BacktestTradeResult(
            ticker=signal.ticker,
            entry_date=str(self.value(entry_row, "date")),
            exit_date=exit_date,
            entry_price=entry_price,
            exit_price=exit_price,
            return_pct=return_pct,
            max_gain_pct=max_gain,
            max_drawdown_pct=max_drawdown,
            holding_days=(self.date_value(exit_date) - entry_date).days,
            exit_reason=exit_reason,
            final_score=signal.final_score,
            grade=signal.grade,
            confidence_level=signal.confidence_level,
            setup_label=signal.setup_label,
            source_run_id=signal.source_run_id,
            signal_date=signal.signal_date,
            warnings=warnings,
        ), warnings

    def fetch_prices(self, ticker):
        if self.repository is None or not hasattr(self.repository, "fetch_ohlcv"):
            return []
        rows = self.repository.fetch_ohlcv(ticker) or []
        return sorted(rows, key=lambda row: self.date_value(self.value(row, "date")))

    @classmethod
    def entry_index(cls, prices, signal_date):
        requested = cls.date_value(signal_date)
        for index, row in enumerate(prices):
            if cls.date_value(cls.value(row, "date")) > requested:
                return index
        return None

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

    @staticmethod
    def date_value(value):
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return datetime.fromisoformat(str(value)).date()

    @staticmethod
    def unique(values):
        result = []
        for value in values or []:
            if value and value not in result:
                result.append(value)
        return result
