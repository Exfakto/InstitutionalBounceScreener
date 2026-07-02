from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from backtesting.backtest_models import BacktestTrade


@dataclass(frozen=True)
class TradeReplayStep:
    date: date | datetime | str
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: float | int | None = None
    status: str = "Active"
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TradeReplayResult:
    ticker: str
    entry_date: date | datetime | str
    exit_date: date | datetime | str
    entry_price: float
    exit_price: float
    stop_price: float | None = None
    target_price: float | None = None
    exit_reason: str = "unspecified"
    replay_steps: list[TradeReplayStep] = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


class TradeReplayEngine:
    """
    Deterministic step-by-step replay for a completed historical trade.
    """

    BEFORE_ENTRY = "Before Entry"
    ENTRY_DAY = "Entry Day"
    ACTIVE = "Active"
    TARGET_HIT = "Target Hit"
    STOP_HIT = "Stop Hit"
    EXIT_DAY = "Exit Day"
    AFTER_EXIT = "After Exit"

    def replay_trade(self, trade, historical_price_rows) -> TradeReplayResult:
        normalized_trade = self.normalized_trade(trade)
        warnings = list(normalized_trade.warnings or [])
        rows = self.normalized_rows(historical_price_rows)

        if not rows:
            warnings.append("No historical price rows supplied.")

        replay_steps = [
            self.replay_step(normalized_trade, row)
            for row in rows
        ]
        summary = self.summary(normalized_trade, replay_steps)

        if not any(step.status == self.ENTRY_DAY for step in replay_steps):
            warnings.append("Entry date was not found in supplied price rows.")

        if not any(
            step.status in {self.EXIT_DAY, self.TARGET_HIT, self.STOP_HIT}
            for step in replay_steps
        ):
            warnings.append("Exit date was not found in supplied price rows.")

        return TradeReplayResult(
            ticker=normalized_trade.ticker,
            entry_date=normalized_trade.entry_date,
            exit_date=normalized_trade.exit_date,
            entry_price=normalized_trade.entry_price,
            exit_price=normalized_trade.exit_price,
            stop_price=normalized_trade.stop_price,
            target_price=normalized_trade.target_price,
            exit_reason=normalized_trade.exit_reason,
            replay_steps=replay_steps,
            summary=summary,
            warnings=warnings,
        )

    @classmethod
    def replay_step(cls, trade: BacktestTrade, row: dict) -> TradeReplayStep:
        row_date = cls.date_value(cls.value_for(row, "date"))
        entry_date = cls.date_value(trade.entry_date)
        exit_date = cls.date_value(trade.exit_date)
        high = cls.numeric_value(cls.value_for(row, "high"))
        low = cls.numeric_value(cls.value_for(row, "low"))
        notes = []

        if row_date < entry_date:
            status = cls.BEFORE_ENTRY
        elif row_date == entry_date:
            status = cls.ENTRY_DAY
            notes.append(f"Entry at {trade.entry_price:.2f}")
        elif row_date > exit_date:
            status = cls.AFTER_EXIT
        else:
            status = cls.ACTIVE

        target_hit = (
            trade.target_price is not None
            and high is not None
            and high >= trade.target_price
            and entry_date <= row_date <= exit_date
        )
        stop_hit = (
            trade.stop_price is not None
            and low is not None
            and low <= trade.stop_price
            and entry_date <= row_date <= exit_date
        )

        if stop_hit:
            status = cls.STOP_HIT
            notes.append(f"Stop hit at {trade.stop_price:.2f}")
        elif target_hit:
            status = cls.TARGET_HIT
            notes.append(f"Target hit at {trade.target_price:.2f}")
        elif row_date == exit_date and row_date >= entry_date:
            status = cls.EXIT_DAY
            notes.append(f"Exit at {trade.exit_price:.2f}")

        return TradeReplayStep(
            date=cls.value_for(row, "date"),
            open=cls.numeric_value(cls.value_for(row, "open")),
            high=high,
            low=low,
            close=cls.numeric_value(cls.value_for(row, "close")),
            volume=cls.numeric_value(cls.value_for(row, "volume")),
            status=status,
            notes=notes,
        )

    @classmethod
    def summary(cls, trade: BacktestTrade, steps: list[TradeReplayStep]) -> dict:
        statuses = [step.status for step in steps]

        return {
            "step_count": len(steps),
            "return_pct": trade.return_pct,
            "hold_days": trade.hold_days,
            "entry_seen": cls.ENTRY_DAY in statuses,
            "exit_seen": any(
                status in {cls.EXIT_DAY, cls.TARGET_HIT, cls.STOP_HIT}
                for status in statuses
            ),
            "target_hit": cls.TARGET_HIT in statuses,
            "stop_hit": cls.STOP_HIT in statuses,
        }

    @classmethod
    def normalized_trade(cls, trade) -> BacktestTrade:
        if isinstance(trade, BacktestTrade):
            return trade

        if not isinstance(trade, dict):
            raise TypeError("Trade replay requires a BacktestTrade or trade dictionary.")

        try:
            return BacktestTrade(
                ticker=trade["ticker"],
                entry_date=trade["entry_date"],
                exit_date=trade["exit_date"],
                entry_price=float(trade["entry_price"]),
                exit_price=float(trade["exit_price"]),
                stop_price=cls.optional_float(trade.get("stop_price")),
                target_price=cls.optional_float(trade.get("target_price")),
                exit_reason=trade.get("exit_reason", "unspecified"),
                opportunity_score=cls.optional_float(trade.get("opportunity_score")),
                confidence=trade.get("confidence"),
                warnings=list(trade.get("warnings") or []),
                shares=float(trade.get("shares", 1.0)),
                metadata=trade.get("metadata"),
            )
        except KeyError as exc:
            raise ValueError("Trade dictionary is missing required fields.") from exc

    @classmethod
    def normalized_rows(cls, rows) -> list[dict]:
        if not rows:
            return []

        if not isinstance(rows, list):
            raise TypeError("Historical price rows must be supplied as a list.")

        normalized = []

        for row in rows:
            if isinstance(row, dict):
                row_data = row
            elif hasattr(row, "__dict__"):
                row_data = vars(row)
            else:
                raise TypeError("Historical price rows must be dictionaries or objects.")

            if cls.value_for(row_data, "date") is None:
                continue

            normalized.append(row_data)

        return sorted(
            normalized,
            key=lambda row: cls.date_value(cls.value_for(row, "date")),
        )

    @staticmethod
    def value_for(source, name):
        if isinstance(source, dict):
            return source.get(name)

        return getattr(source, name, None)

    @staticmethod
    def optional_float(value):
        if value is None or value == "":
            return None

        return float(value)

    @staticmethod
    def numeric_value(value):
        if value is None or value == "":
            return None

        return float(value)

    @staticmethod
    def date_value(value) -> date:
        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, date):
            return value

        try:
            return datetime.fromisoformat(str(value)).date()
        except (TypeError, ValueError) as exc:
            raise ValueError("Trade replay dates must be date-like values.") from exc
