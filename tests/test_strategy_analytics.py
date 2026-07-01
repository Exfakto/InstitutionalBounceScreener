from types import SimpleNamespace

from analysis.strategy_analytics import StrategyAnalyticsCalculator


def calculate(trades):
    return StrategyAnalyticsCalculator().calculate(trades)


def trade(**overrides):
    item = {
        "ticker": "AAPL",
        "sector": "Technology",
        "opportunity_rating": "Elite Bounce",
        "confidence": "High",
        "entry_price": 100.0,
        "exit_price": 110.0,
        "entry_date": "2026-07-01",
        "exit_date": "2026-07-06",
        "status": "Exited Win",
        "risk_reward": 2.5,
        "expected_return": 8.0,
        "actual_return": None,
        "trade_thesis": "Valid bounce setup.",
        "institutional_checklist_score": 92.0,
    }
    item.update(overrides)
    return item


def test_empty_list_returns_valid_empty_analytics():
    result = calculate([])

    assert result.overall_statistics == {
        "total_trades": 0,
        "completed_trades": 0,
        "win_rate": 0.0,
        "average_return": 0.0,
        "median_return": 0.0,
        "expectancy": 0.0,
        "average_holding_days": 0.0,
    }
    assert result.opportunity_rating_statistics == {}
    assert result.confidence_statistics == {}
    assert result.sector_statistics == {}
    assert result.top_performing_rating is None
    assert result.worst_performing_rating is None
    assert result.top_sector is None
    assert result.worst_sector is None
    assert "No completed trades" in result.warnings


def test_single_trade_statistics():
    result = calculate([trade()])

    assert result.overall_statistics["total_trades"] == 1
    assert result.overall_statistics["completed_trades"] == 1
    assert result.overall_statistics["win_rate"] == 100.0
    assert result.overall_statistics["average_return"] == 10.0
    assert result.overall_statistics["median_return"] == 10.0
    assert result.overall_statistics["expectancy"] == 10.0
    assert result.overall_statistics["average_holding_days"] == 5.0
    assert result.top_performing_rating == "Elite Bounce"
    assert result.top_sector == "Technology"


def test_mixed_trades_overall_expectancy_and_median():
    result = calculate(
        [
            trade(ticker="AAPL", exit_price=110.0),
            trade(ticker="MSFT", exit_price=95.0, status="Exited Loss"),
            trade(ticker="NVDA", exit_price=104.0),
            trade(ticker="OPEN", status="Entered", exit_price=None),
        ]
    )

    assert result.overall_statistics["total_trades"] == 4
    assert result.overall_statistics["completed_trades"] == 3
    assert result.overall_statistics["win_rate"] == 66.666667
    assert result.overall_statistics["average_return"] == 3.0
    assert result.overall_statistics["median_return"] == 4.0
    assert result.expectancy_statistics["expectancy"] == 3.0
    assert result.expectancy_statistics["average_return"] == 3.0
    assert result.expectancy_statistics["positive_expectancy"] is True
    assert result.expectancy_statistics["sample_size"] == 3


def test_multiple_opportunity_ratings_top_and_worst():
    result = calculate(
        [
            trade(opportunity_rating="Elite Bounce", exit_price=115.0),
            trade(opportunity_rating="High Probability", exit_price=104.0),
            trade(opportunity_rating="Weak", exit_price=90.0, status="Exited Loss"),
        ]
    )

    assert result.opportunity_rating_statistics["Elite Bounce"] == {
        "trade_count": 1,
        "win_rate": 100.0,
        "average_return": 15.0,
    }
    assert result.opportunity_rating_statistics["Weak"]["average_return"] == -10.0
    assert result.top_performing_rating == "Elite Bounce"
    assert result.worst_performing_rating == "Weak"


def test_multiple_sectors_top_and_worst():
    result = calculate(
        [
            trade(sector="Technology", exit_price=110.0),
            trade(sector="Healthcare", exit_price=120.0),
            trade(sector="Energy", exit_price=92.0, status="Exited Loss"),
        ]
    )

    assert result.sector_statistics["Healthcare"]["average_return"] == 20.0
    assert result.sector_statistics["Energy"]["win_rate"] == 0.0
    assert result.top_sector == "Healthcare"
    assert result.worst_sector == "Energy"


def test_confidence_groups():
    result = calculate(
        [
            trade(confidence="High", exit_price=110.0),
            trade(confidence="High", exit_price=90.0, status="Exited Loss"),
            trade(confidence="Moderate", exit_price=105.0),
        ]
    )

    assert result.confidence_statistics["High"]["trade_count"] == 2
    assert result.confidence_statistics["High"]["win_rate"] == 50.0
    assert result.confidence_statistics["High"]["average_return"] == 0.0
    assert result.confidence_statistics["Moderate"]["average_return"] == 5.0


def test_holding_time_groups():
    result = calculate(
        [
            trade(entry_date="2026-07-01", exit_date="2026-07-01"),
            trade(entry_date="2026-07-01", exit_date="2026-07-07"),
            trade(entry_date="2026-07-01", exit_date="2026-07-16"),
            trade(entry_date="2026-07-01", exit_date="2026-07-25"),
        ]
    )

    assert result.holding_period_statistics == {
        "0-5 days": 1,
        "6-10 days": 1,
        "11-20 days": 1,
        ">20 days": 1,
    }


def test_risk_reward_groups():
    result = calculate(
        [
            trade(risk_reward=1.2),
            trade(risk_reward=1.5),
            trade(risk_reward=2.4),
            trade(risk_reward=3.2),
            trade(risk_reward=5.5),
        ]
    )

    assert result.risk_reward_statistics["distribution"] == {
        "<1.5": 1,
        "1.5-2": 1,
        "2-3": 1,
        "3-5": 1,
        ">5": 1,
    }
    assert result.risk_reward_statistics["average_risk_reward"] == 2.76


def test_actual_return_takes_precedence_when_available():
    result = calculate(
        [
            trade(entry_price=100.0, exit_price=100.0, actual_return=7.5),
        ]
    )

    assert result.overall_statistics["average_return"] == 7.5
    assert result.opportunity_rating_statistics["Elite Bounce"]["average_return"] == 7.5


def test_missing_data_generates_warnings():
    result = calculate(
        [
            trade(entry_price=None, status="Exited Win"),
            trade(exit_price=None, status="Exited Loss"),
            trade(entry_date=None),
        ]
    )

    assert "Missing entry price" in result.warnings
    assert "Missing exit price" in result.warnings
    assert "Missing dates" in result.warnings


def test_object_input():
    item = SimpleNamespace(
        ticker="AMZN",
        sector="Consumer",
        opportunity_rating="High Probability",
        confidence="Moderate",
        entry_price=100.0,
        exit_price=106.0,
        entry_date="2026-07-01",
        exit_date="2026-07-09",
        status="Exited Win",
        risk_reward=1.8,
    )

    result = calculate([item])

    assert result.sector_statistics["Consumer"]["average_return"] == 6.0
    assert result.confidence_statistics["Moderate"]["win_rate"] == 100.0


def test_deterministic_output():
    trades = [
        trade(ticker="AAPL", sector="Technology", exit_price=110.0),
        trade(ticker="MSFT", sector="Technology", exit_price=95.0, status="Exited Loss"),
        trade(ticker="AMZN", sector="Consumer", exit_price=103.0),
    ]

    first = calculate(trades)
    second = calculate([dict(item) for item in trades])

    assert first == second
