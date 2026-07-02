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


class SimulationStrategy(BacktestStrategy):
    def __init__(self, max_hold_days=None):
        self.max_hold_days = max_hold_days

    def generate_trades(self, historical_candidates):
        return []


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
    assert result.equity_curve.equity_values == []
    assert result.equity_curve.peak_equity == 100_000.0
    assert result.portfolio_analytics["total_return"] == 0.0
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
    assert result.statistics.profit_factor == 10.0
    assert result.statistics.largest_winner == 10.0
    assert result.statistics.largest_loser == 0.0
    assert result.equity_curve.dates == ["2026-01-06"]
    assert result.equity_curve.equity_values == [100_010.0]
    assert result.portfolio_analytics["total_return"] == pytest.approx(0.01)
    assert result.portfolio_analytics["average_trade_return"] == 10.0
    assert result.portfolio_analytics["median_trade_return"] == 10.0
    assert result.portfolio_analytics["best_trade"] == 10.0
    assert result.portfolio_analytics["worst_trade"] == 10.0
    assert result.portfolio_analytics["average_holding_period"] == 5.0


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
    assert result.statistics.profit_factor == 2.0
    assert result.statistics.max_drawdown == -5.0
    assert result.statistics.largest_winner == 10.0
    assert result.statistics.largest_loser == -5.0
    assert result.equity_curve.dates == ["2026-01-05", "2026-01-06"]
    assert result.equity_curve.equity_values == [99_995.0, 100_005.0]
    assert result.portfolio_analytics["median_trade_return"] == 2.5
    assert result.portfolio_analytics["max_drawdown"] == -5.0
    assert result.portfolio_analytics["recovery_periods"] == [1]


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


def historical_candidate(**overrides):
    candidate = {
        "ticker": "AAPL",
        "entry_date": "2026-01-01",
        "entry_price": 100.0,
        "stop_price": 95.0,
        "target_price": 110.0,
        "opportunity_score": 82.5,
        "confidence": "High",
        "warnings": ["Test warning"],
        "prices": [
            {
                "date": "2026-01-01",
                "open": 99.0,
                "high": 101.0,
                "low": 98.0,
                "close": 100.0,
            },
            {
                "date": "2026-01-02",
                "open": 101.0,
                "high": 111.0,
                "low": 100.0,
                "close": 110.0,
            },
            {
                "date": "2026-01-03",
                "open": 110.0,
                "high": 112.0,
                "low": 109.0,
                "close": 111.0,
            },
        ],
    }
    candidate.update(overrides)
    return candidate


def test_simulate_trade_exits_when_target_is_hit():
    trade = BacktestEngine().simulate_trade(historical_candidate())

    assert trade.ticker == "AAPL"
    assert trade.entry_date == "2026-01-01"
    assert trade.exit_date == "2026-01-02"
    assert trade.entry_price == 100.0
    assert trade.exit_price == 110.0
    assert trade.stop_price == 95.0
    assert trade.target_price == 110.0
    assert trade.exit_reason == "target_reached"
    assert trade.return_pct == 10.0
    assert trade.hold_days == 1
    assert trade.opportunity_score == 82.5
    assert trade.confidence == "High"
    assert trade.warnings == ["Test warning"]


def test_simulate_trade_exits_when_stop_is_hit():
    candidate = historical_candidate(
        prices=[
            {"date": "2026-01-01", "high": 101.0, "low": 98.0, "close": 100.0},
            {"date": "2026-01-02", "high": 103.0, "low": 94.0, "close": 96.0},
        ]
    )

    trade = BacktestEngine().simulate_trade(candidate)

    assert trade.exit_date == "2026-01-02"
    assert trade.exit_price == 95.0
    assert trade.exit_reason == "stop_reached"
    assert trade.return_pct == -5.0


def test_simulate_trade_exits_at_maximum_holding_period():
    candidate = historical_candidate(
        max_hold_days=2,
        prices=[
            {"date": "2026-01-01", "high": 101.0, "low": 98.0, "close": 100.0},
            {"date": "2026-01-02", "high": 104.0, "low": 97.0, "close": 102.0},
            {"date": "2026-01-03", "high": 105.0, "low": 98.0, "close": 104.0},
            {"date": "2026-01-04", "high": 106.0, "low": 99.0, "close": 105.0},
        ],
    )

    trade = BacktestEngine().simulate_trade(candidate)

    assert trade.exit_date == "2026-01-03"
    assert trade.exit_price == 104.0
    assert trade.exit_reason == "maximum_holding_period"
    assert trade.hold_days == 2


def test_simulate_trade_exits_at_end_of_available_data():
    candidate = historical_candidate(
        target_price=120.0,
        stop_price=90.0,
        prices=[
            {"date": "2026-01-01", "high": 101.0, "low": 98.0, "close": 100.0},
            {"date": "2026-01-02", "high": 104.0, "low": 97.0, "close": 102.0},
            {"date": "2026-01-03", "high": 105.0, "low": 98.0, "close": 103.0},
        ],
    )

    trade = BacktestEngine().simulate_trade(candidate)

    assert trade.exit_date == "2026-01-03"
    assert trade.exit_price == 103.0
    assert trade.exit_reason == "end_of_available_data"


def test_run_backtest_simulates_multiple_candidates_and_statistics():
    candidates = [
        historical_candidate(ticker="WIN"),
        historical_candidate(
            ticker="LOSS",
            prices=[
                {"date": "2026-01-01", "high": 101.0, "low": 98.0, "close": 100.0},
                {"date": "2026-01-02", "high": 103.0, "low": 94.0, "close": 96.0},
            ],
        ),
    ]

    result = BacktestEngine().run_backtest(candidates, SimulationStrategy())

    assert [trade.ticker for trade in result.trades] == ["WIN", "LOSS"]
    assert [trade.exit_reason for trade in result.trades] == [
        "target_reached",
        "stop_reached",
    ]
    assert result.statistics.total_trades == 2
    assert result.statistics.wins == 1
    assert result.statistics.losses == 1
    assert result.statistics.win_rate == 0.5
    assert result.statistics.average_gain == 10.0
    assert result.statistics.average_loss == -5.0
    assert result.statistics.expectancy == 2.5
    assert result.statistics.profit_factor == 2.0


def test_simulated_backtest_output_is_deterministic():
    candidates = [historical_candidate()]
    engine = BacktestEngine()

    first = engine.run_backtest(candidates, SimulationStrategy())
    second = engine.run_backtest(candidates, SimulationStrategy())

    assert first == second


def test_simulate_trade_rejects_invalid_inputs():
    with pytest.raises(ValueError, match="price history"):
        BacktestEngine().simulate_trade(historical_candidate(prices=[]))

    with pytest.raises(ValueError, match="positive entry price"):
        BacktestEngine().simulate_trade(historical_candidate(entry_price=0))

    with pytest.raises(ValueError, match="stop price"):
        BacktestEngine().simulate_trade(historical_candidate(stop_price=None))
