import pytest

from backtesting.backtest_models import BacktestTrade
from backtesting.trade_replay import TradeReplayEngine, TradeReplayResult, TradeReplayStep


def trade(**overrides):
    values = {
        "ticker": "AAPL",
        "entry_date": "2026-01-02",
        "exit_date": "2026-01-04",
        "entry_price": 100.0,
        "exit_price": 104.0,
        "stop_price": 95.0,
        "target_price": 110.0,
        "exit_reason": "maximum_holding_period",
    }
    values.update(overrides)
    return BacktestTrade(**values)


def price_rows():
    return [
        {
            "date": "2026-01-01",
            "open": 98.0,
            "high": 99.0,
            "low": 97.0,
            "close": 98.5,
            "volume": 1000,
        },
        {
            "date": "2026-01-02",
            "open": 99.0,
            "high": 102.0,
            "low": 98.0,
            "close": 101.0,
            "volume": 1100,
        },
        {
            "date": "2026-01-03",
            "open": 101.0,
            "high": 105.0,
            "low": 100.0,
            "close": 103.0,
            "volume": 1200,
        },
        {
            "date": "2026-01-04",
            "open": 103.0,
            "high": 106.0,
            "low": 102.0,
            "close": 104.0,
            "volume": 1300,
        },
        {
            "date": "2026-01-05",
            "open": 104.0,
            "high": 107.0,
            "low": 103.0,
            "close": 106.0,
            "volume": 1400,
        },
    ]


def test_trade_replay_normal_trade():
    result = TradeReplayEngine().replay_trade(trade(), price_rows())

    assert isinstance(result, TradeReplayResult)
    assert result.ticker == "AAPL"
    assert result.entry_date == "2026-01-02"
    assert result.exit_date == "2026-01-04"
    assert result.entry_price == 100.0
    assert result.exit_price == 104.0
    assert result.stop_price == 95.0
    assert result.target_price == 110.0
    assert result.exit_reason == "maximum_holding_period"
    assert [step.status for step in result.replay_steps] == [
        "Before Entry",
        "Entry Day",
        "Active",
        "Exit Day",
        "After Exit",
    ]
    assert result.replay_steps[1].notes == ["Entry at 100.00"]
    assert result.replay_steps[3].notes == ["Exit at 104.00"]
    assert result.summary["step_count"] == 5
    assert result.summary["entry_seen"] is True
    assert result.summary["exit_seen"] is True
    assert result.warnings == []


def test_trade_replay_target_hit():
    target_trade = trade(
        exit_date="2026-01-03",
        exit_price=110.0,
        target_price=105.0,
        exit_reason="target_reached",
    )

    result = TradeReplayEngine().replay_trade(target_trade, price_rows())

    assert result.replay_steps[2].status == "Target Hit"
    assert result.replay_steps[2].notes == ["Target hit at 105.00"]
    assert result.summary["target_hit"] is True
    assert result.summary["stop_hit"] is False


def test_trade_replay_stop_hit():
    stop_trade = trade(
        exit_date="2026-01-03",
        exit_price=95.0,
        stop_price=100.0,
        exit_reason="stop_reached",
    )

    result = TradeReplayEngine().replay_trade(stop_trade, price_rows())

    assert result.replay_steps[2].status == "Stop Hit"
    assert result.replay_steps[2].notes == ["Stop hit at 100.00"]
    assert result.summary["stop_hit"] is True


def test_trade_replay_max_hold_exit_marks_exit_day():
    result = TradeReplayEngine().replay_trade(
        trade(exit_reason="maximum_holding_period"),
        price_rows(),
    )

    assert result.replay_steps[3].status == "Exit Day"
    assert result.summary["target_hit"] is False
    assert result.summary["stop_hit"] is False


def test_trade_replay_handles_missing_price_data():
    result = TradeReplayEngine().replay_trade(trade(), [])

    assert result.replay_steps == []
    assert "No historical price rows supplied." in result.warnings
    assert "Entry date was not found in supplied price rows." in result.warnings
    assert "Exit date was not found in supplied price rows." in result.warnings
    assert result.summary["step_count"] == 0


def test_trade_replay_handles_partial_price_data_without_inventing_prices():
    rows = [
        {"date": "2026-01-02", "close": 101.0},
        {"date": "2026-01-04", "high": 106.0},
    ]

    result = TradeReplayEngine().replay_trade(trade(), rows)

    assert result.replay_steps == [
        TradeReplayStep(
            date="2026-01-02",
            close=101.0,
            status="Entry Day",
            notes=["Entry at 100.00"],
        ),
        TradeReplayStep(
            date="2026-01-04",
            high=106.0,
            status="Exit Day",
            notes=["Exit at 104.00"],
        ),
    ]
    assert result.warnings == []


def test_trade_replay_accepts_trade_like_dictionary():
    result = TradeReplayEngine().replay_trade(
        {
            "ticker": "MSFT",
            "entry_date": "2026-01-02",
            "exit_date": "2026-01-04",
            "entry_price": 100.0,
            "exit_price": 104.0,
            "stop_price": 95.0,
            "target_price": 110.0,
            "exit_reason": "maximum_holding_period",
        },
        price_rows(),
    )

    assert result.ticker == "MSFT"
    assert result.summary["return_pct"] == 4.0


def test_trade_replay_rejects_invalid_trade():
    with pytest.raises(TypeError, match="BacktestTrade"):
        TradeReplayEngine().replay_trade(object(), price_rows())

    with pytest.raises(ValueError, match="missing required fields"):
        TradeReplayEngine().replay_trade({"ticker": "AAPL"}, price_rows())


def test_trade_replay_output_is_deterministic():
    engine = TradeReplayEngine()

    first = engine.replay_trade(trade(), price_rows())
    second = engine.replay_trade(trade(), price_rows())

    assert first == second
