import pytest

from backtesting import BacktestEngine, BacktestResult, BacktestStrategy, BacktestTrade


class FixedTradeStrategy(BacktestStrategy):
    def __init__(self, trades):
        self.trades = trades

    def generate_trades(self, historical_candidates):
        return list(self.trades)


class CandidateEchoStrategy(BacktestStrategy):
    def generate_trades(self, historical_candidates):
        trades = []

        for candidate in historical_candidates:
            trades.append(
                BacktestTrade(
                    ticker=candidate["ticker"],
                    entry_date=candidate["entry_date"],
                    exit_date=candidate["exit_date"],
                    entry_price=candidate["entry_price"],
                    exit_price=candidate["exit_price"],
                )
            )

        return trades


class InvalidTradeStrategy(BacktestStrategy):
    def generate_trades(self, historical_candidates):
        return [{"ticker": "AAPL"}]


def winning_trade():
    return BacktestTrade(
        ticker="AAPL",
        entry_date="2026-01-01",
        exit_date="2026-01-06",
        entry_price=100.0,
        exit_price=110.0,
    )


def losing_trade():
    return BacktestTrade(
        ticker="MSFT",
        entry_date="2026-01-02",
        exit_date="2026-01-05",
        entry_price=100.0,
        exit_price=95.0,
    )


def test_backtest_engine_empty_dataset_returns_empty_result():
    result = BacktestEngine().run_backtest([], FixedTradeStrategy([]))

    assert isinstance(result, BacktestResult)
    assert result.trades == []
    assert result.statistics.total_trades == 0
    assert result.statistics.max_drawdown == 0.0
    assert result.warnings == ["No historical candidates supplied."]


def test_backtest_engine_single_trade_statistics():
    result = BacktestEngine().run_backtest([{"ticker": "AAPL"}], FixedTradeStrategy([winning_trade()]))

    assert result.trades == [winning_trade()]
    assert result.statistics.total_trades == 1
    assert result.statistics.wins == 1
    assert result.statistics.losses == 0
    assert result.statistics.win_rate == 1.0
    assert result.statistics.average_gain == 10.0
    assert result.statistics.average_loss == 0.0
    assert result.statistics.expectancy == 10.0
    assert result.statistics.average_hold_days == 5.0
    assert result.statistics.largest_winner == 10.0
    assert result.statistics.largest_loser == 0.0


def test_backtest_engine_multiple_trade_statistics():
    result = BacktestEngine().run_backtest(
        [{"ticker": "AAPL"}, {"ticker": "MSFT"}],
        FixedTradeStrategy([winning_trade(), losing_trade()]),
    )

    assert result.statistics.total_trades == 2
    assert result.statistics.wins == 1
    assert result.statistics.losses == 1
    assert result.statistics.win_rate == 0.5
    assert result.statistics.average_gain == 10.0
    assert result.statistics.average_loss == -5.0
    assert result.statistics.expectancy == 2.5
    assert result.statistics.average_hold_days == 4.0
    assert result.statistics.max_drawdown == -5.0
    assert result.statistics.largest_winner == 10.0
    assert result.statistics.largest_loser == -5.0


def test_backtest_engine_output_is_deterministic():
    candidates = [
        {
            "ticker": "AAPL",
            "entry_date": "2026-01-01",
            "exit_date": "2026-01-06",
            "entry_price": 100.0,
            "exit_price": 110.0,
        }
    ]
    engine = BacktestEngine()

    first = engine.run_backtest(candidates, CandidateEchoStrategy())
    second = engine.run_backtest(candidates, CandidateEchoStrategy())

    assert first == second


def test_backtest_engine_rejects_invalid_strategy():
    with pytest.raises(TypeError, match="BacktestStrategy"):
        BacktestEngine().run_backtest([], object())


def test_backtest_engine_rejects_invalid_trade():
    with pytest.raises(TypeError, match="invalid trade"):
        BacktestEngine().run_backtest([{"ticker": "AAPL"}], InvalidTradeStrategy())
