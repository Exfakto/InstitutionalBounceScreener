import pytest

from backtesting import BacktestStatistics, BacktestTrade


def test_backtest_trade_calculates_return_profit_and_hold_days():
    trade = BacktestTrade(
        ticker="AAPL",
        entry_date="2026-01-01",
        exit_date="2026-01-06",
        entry_price=100.0,
        exit_price=112.0,
        shares=2,
    )

    assert trade.return_pct == 12.0
    assert trade.profit_loss == 24.0
    assert trade.hold_days == 5
    assert trade.is_win is True


def test_backtest_trade_rejects_missing_ticker():
    with pytest.raises(ValueError, match="ticker"):
        BacktestTrade(
            ticker="",
            entry_date="2026-01-01",
            exit_date="2026-01-02",
            entry_price=100.0,
            exit_price=101.0,
        )


def test_backtest_trade_rejects_invalid_price_and_dates():
    with pytest.raises(ValueError, match="entry_price"):
        BacktestTrade(
            ticker="MSFT",
            entry_date="2026-01-01",
            exit_date="2026-01-02",
            entry_price=0.0,
            exit_price=101.0,
        )

    with pytest.raises(ValueError, match="before entry_date"):
        BacktestTrade(
            ticker="MSFT",
            entry_date="2026-01-03",
            exit_date="2026-01-02",
            entry_price=100.0,
            exit_price=101.0,
        )


def test_backtest_statistics_defaults_are_zero():
    statistics = BacktestStatistics()

    assert statistics.total_trades == 0
    assert statistics.wins == 0
    assert statistics.losses == 0
    assert statistics.win_rate == 0.0
    assert statistics.expectancy == 0.0
