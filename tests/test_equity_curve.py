import pytest

from backtesting.backtest_models import BacktestTrade
from backtesting.equity_curve import EquityCurve


def trade(
    ticker,
    entry_date,
    exit_date,
    entry_price,
    exit_price,
    shares=1,
):
    return BacktestTrade(
        ticker=ticker,
        entry_date=entry_date,
        exit_date=exit_date,
        entry_price=entry_price,
        exit_price=exit_price,
        shares=shares,
    )


def test_empty_equity_curve_uses_initial_equity_peak():
    curve = EquityCurve.from_trades([])

    assert curve.dates == []
    assert curve.equity_values == []
    assert curve.cumulative_return == 0.0
    assert curve.peak_equity == 100_000.0
    assert curve.drawdown_series == []
    assert curve.recovery_periods == []
    assert curve.rolling_equity_highs == []


def test_equity_curve_for_one_trade():
    curve = EquityCurve.from_trades(
        [
            trade("AAPL", "2026-01-01", "2026-01-06", 100.0, 110.0, shares=10),
        ]
    )

    assert curve.dates == ["2026-01-06"]
    assert curve.equity_values == [100_100.0]
    assert curve.cumulative_return == pytest.approx(0.1)
    assert curve.peak_equity == 100_100.0
    assert curve.drawdown_series == [0.0]
    assert curve.rolling_equity_highs == [100_100.0]
    assert curve.cagr > 0.0


def test_equity_curve_for_multiple_trades_is_chronological_and_cumulative():
    trades = [
        trade("THIRD", "2026-01-03", "2026-01-04", 100.0, 130.0, shares=10),
        trade("FIRST", "2026-01-01", "2026-01-02", 100.0, 110.0, shares=10),
        trade("SECOND", "2026-01-02", "2026-01-03", 100.0, 80.0, shares=10),
    ]

    curve = EquityCurve.from_trades(trades)

    assert curve.dates == ["2026-01-02", "2026-01-03", "2026-01-04"]
    assert curve.equity_values == [100_100.0, 99_900.0, 100_200.0]
    assert curve.cumulative_return == pytest.approx(0.2)
    assert curve.peak_equity == 100_200.0


def test_equity_curve_drawdown_and_recovery_calculation():
    curve = EquityCurve.from_trades(
        [
            trade("WIN", "2026-01-01", "2026-01-02", 100.0, 110.0, shares=10),
            trade("LOSS", "2026-01-02", "2026-01-03", 100.0, 80.0, shares=10),
            trade("RECOVER", "2026-01-03", "2026-01-04", 100.0, 130.0, shares=10),
        ]
    )

    assert curve.drawdown_series == [0.0, -200.0, 0.0]
    assert curve.average_drawdown == pytest.approx(-200.0 / 3.0)
    assert curve.recovery_periods == [1]
    assert curve.rolling_equity_highs == [100_100.0, 100_100.0, 100_200.0]


def test_equity_curve_output_is_deterministic():
    trades = [
        trade("AAPL", "2026-01-01", "2026-01-02", 100.0, 110.0),
        trade("MSFT", "2026-01-02", "2026-01-03", 100.0, 95.0),
    ]

    assert EquityCurve.from_trades(trades) == EquityCurve.from_trades(trades)


def test_equity_curve_rejects_invalid_inputs():
    with pytest.raises(ValueError, match="initial_equity"):
        EquityCurve.from_trades([], initial_equity=0)

    with pytest.raises(TypeError, match="BacktestTrade"):
        EquityCurve.from_trades([{"ticker": "AAPL"}])
