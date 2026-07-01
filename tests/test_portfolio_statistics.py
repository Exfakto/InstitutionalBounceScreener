from types import SimpleNamespace

from analysis.portfolio_statistics import PortfolioStatisticsCalculator


def calculate(trades):
    return PortfolioStatisticsCalculator().calculate(trades)


def winning_trade(**overrides):
    trade = {
        "ticker": "AAPL",
        "entry_date": "2026-07-01",
        "entry_price": 100.0,
        "stop_price": 95.0,
        "target_price": 115.0,
        "exit_date": "2026-07-06",
        "exit_price": 110.0,
        "status": "Exited Win",
        "shares": 10,
        "risk_reward": 2.0,
        "opportunity_rating": "Elite Bounce",
        "confidence": "High",
    }
    trade.update(overrides)
    return trade


def losing_trade(**overrides):
    trade = {
        "ticker": "MSFT",
        "entry_date": "2026-07-01",
        "entry_price": 100.0,
        "stop_price": 95.0,
        "target_price": 115.0,
        "exit_date": "2026-07-04",
        "exit_price": 95.0,
        "status": "Exited Loss",
        "shares": 5,
        "risk_reward": 1.5,
        "opportunity_rating": "High Probability",
        "confidence": "Moderate",
    }
    trade.update(overrides)
    return trade


def test_empty_trade_list():
    result = calculate([])

    assert result.total_trades == 0
    assert result.open_trades == 0
    assert result.closed_trades == 0
    assert result.win_rate == 0.0
    assert result.average_return_pct == 0.0
    assert result.best_trade is None
    assert result.worst_trade is None
    assert result.average_holding_days is None
    assert "No closed trades" in result.warnings


def test_one_winning_trade():
    result = calculate([winning_trade()])

    assert result.total_trades == 1
    assert result.closed_trades == 1
    assert result.winning_trades == 1
    assert result.losing_trades == 0
    assert result.win_rate == 100.0
    assert result.average_gain_pct == 10.0
    assert result.average_return_pct == 10.0
    assert result.total_return_pct == 10.0
    assert result.profit_factor is None
    assert result.expectancy == 10.0
    assert result.best_trade["ticker"] == "AAPL"
    assert result.worst_trade["ticker"] == "AAPL"
    assert result.average_holding_days == 5.0


def test_one_losing_trade():
    result = calculate([losing_trade()])

    assert result.closed_trades == 1
    assert result.winning_trades == 0
    assert result.losing_trades == 1
    assert result.loss_rate == 100.0
    assert result.average_loss_pct == -5.0
    assert result.average_return_pct == -5.0
    assert result.profit_factor == 0.0
    assert result.worst_trade["ticker"] == "MSFT"


def test_mixed_wins_losses_profit_factor_and_expectancy():
    result = calculate(
        [
            winning_trade(ticker="AAPL", exit_price=110.0),
            winning_trade(ticker="NVDA", exit_price=105.0),
            losing_trade(ticker="MSFT", exit_price=95.0),
        ]
    )

    assert result.closed_trades == 3
    assert result.winning_trades == 2
    assert result.losing_trades == 1
    assert result.win_rate == 66.666667
    assert result.loss_rate == 33.333333
    assert result.average_gain_pct == 7.5
    assert result.average_loss_pct == -5.0
    assert result.average_return_pct == 3.333333
    assert result.total_return_pct == 10.0
    assert result.profit_factor == 3.0
    assert result.expectancy == 3.333333
    assert result.average_risk_reward == 1.833333


def test_open_trades_excluded_from_closed_performance():
    result = calculate(
        [
            winning_trade(),
            {
                "ticker": "TSLA",
                "status": "Entered",
                "entry_price": 200.0,
                "shares": 3,
            },
        ]
    )

    assert result.total_trades == 2
    assert result.open_trades == 1
    assert result.closed_trades == 1
    assert result.average_return_pct == 10.0


def test_cancelled_trades_counted_separately():
    result = calculate(
        [
            winning_trade(),
            {"ticker": "META", "status": "Cancelled"},
        ]
    )

    assert result.cancelled_trades == 1
    assert result.closed_trades == 1
    assert result.by_status["Cancelled"] == 1


def test_missing_prices_generate_warnings():
    result = calculate(
        [
            winning_trade(entry_price=None),
            losing_trade(exit_price=None),
            winning_trade(ticker="BAD", entry_price=0, exit_price=10),
        ]
    )

    assert result.closed_trades == 3
    assert result.average_return_pct == 0.0
    assert "Missing entry price" in result.warnings
    assert "Missing exit price" in result.warnings
    assert "Invalid price data" in result.warnings


def test_missing_dates_generate_warnings():
    result = calculate([winning_trade(entry_date=None), losing_trade(exit_date=None)])

    assert result.average_holding_days is None
    assert result.max_holding_days is None
    assert result.min_holding_days is None
    assert "Missing dates" in result.warnings


def test_best_and_worst_trade():
    result = calculate(
        [
            winning_trade(ticker="BEST", exit_price=125.0),
            losing_trade(ticker="WORST", exit_price=90.0),
            winning_trade(ticker="MID", exit_price=105.0),
        ]
    )

    assert result.best_trade == {
        "ticker": "BEST",
        "status": "Exited Win",
        "return_pct": 25.0,
    }
    assert result.worst_trade == {
        "ticker": "WORST",
        "status": "Exited Loss",
        "return_pct": -10.0,
    }


def test_breakdowns_by_opportunity_rating_and_confidence():
    result = calculate(
        [
            winning_trade(opportunity_rating="Elite Bounce", confidence="High"),
            losing_trade(opportunity_rating="Elite Bounce", confidence="Moderate"),
            winning_trade(opportunity_rating=None, confidence=None),
        ]
    )

    assert result.by_opportunity_rating["Elite Bounce"] == 2
    assert result.by_opportunity_rating["Unknown"] == 1
    assert result.by_confidence["High"] == 1
    assert result.by_confidence["Moderate"] == 1
    assert result.by_confidence["Unknown"] == 1


def test_status_inference_from_prices_when_status_unavailable():
    result = calculate(
        [
            winning_trade(status=None, exit_price=105.0),
            losing_trade(status="", exit_price=90.0),
        ]
    )

    assert result.closed_trades == 2
    assert result.winning_trades == 1
    assert result.losing_trades == 1
    assert result.by_status["Unknown"] == 2


def test_object_input_and_missing_shares_warning():
    trade = SimpleNamespace(
        ticker="AMZN",
        entry_date="2026-07-01",
        entry_price=100.0,
        exit_date="2026-07-02",
        exit_price=101.0,
        status="Exited Win",
        shares=None,
        risk_reward=1.2,
        opportunity_rating="Acceptable",
        confidence="Low",
    )

    result = calculate([trade])

    assert result.total_trades == 1
    assert result.best_trade["ticker"] == "AMZN"
    assert "Missing shares" in result.warnings


def test_deterministic_output():
    trades = [
        winning_trade(ticker="AAPL"),
        losing_trade(ticker="MSFT"),
        {"ticker": "TSLA", "status": "Entered", "entry_price": 200.0},
    ]

    first = calculate(trades)
    second = calculate([dict(trade) for trade in trades])

    assert first == second
