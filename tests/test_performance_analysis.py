import pytest

from backtesting.backtest_models import BacktestTrade
from backtesting.equity_curve import EquityCurve
from backtesting.performance_analysis import PerformanceAnalysis


def trade(ticker, entry_date, exit_date, entry_price, exit_price, shares=1):
    return BacktestTrade(
        ticker=ticker,
        entry_date=entry_date,
        exit_date=exit_date,
        entry_price=entry_price,
        exit_price=exit_price,
        shares=shares,
    )


def test_performance_analysis_handles_empty_equity_curve():
    analysis = PerformanceAnalysis.from_equity_curve(EquityCurve())

    assert analysis.drawdown_analysis["max_drawdown"] == 0.0
    assert analysis.monthly_returns == {}
    assert analysis.yearly_returns == {}
    assert analysis.best_month is None
    assert analysis.worst_year is None
    assert analysis.positive_month_rate == 0.0
    assert analysis.summary["warnings"] == ["No equity curve data available."]


def test_performance_analysis_handles_one_point_equity_curve():
    curve = EquityCurve(
        dates=["2026-01-31"],
        equity_values=[101_000.0],
        cumulative_return=1.0,
        peak_equity=101_000.0,
        drawdown_series=[0.0],
        rolling_equity_highs=[101_000.0],
    )

    analysis = PerformanceAnalysis.from_equity_curve(curve)

    assert analysis.monthly_returns == {"2026-01": 1.0}
    assert analysis.yearly_returns == {"2026": 1.0}
    assert analysis.best_month == ("2026-01", 1.0)
    assert analysis.worst_month == ("2026-01", 1.0)
    assert analysis.positive_months == 1
    assert analysis.negative_months == 0
    assert analysis.positive_month_rate == 1.0


def test_performance_analysis_rising_equity_curve_has_no_drawdown():
    curve = EquityCurve(
        dates=["2026-01-31", "2026-02-28", "2026-03-31"],
        equity_values=[101_000.0, 102_000.0, 103_000.0],
        cumulative_return=3.0,
        peak_equity=103_000.0,
        drawdown_series=[0.0, 0.0, 0.0],
        cagr=12.0,
        rolling_equity_highs=[101_000.0, 102_000.0, 103_000.0],
    )

    analysis = PerformanceAnalysis.from_equity_curve(curve)

    assert analysis.drawdown_analysis["max_drawdown"] == 0.0
    assert analysis.drawdown_analysis["longest_drawdown"] == 0
    assert analysis.summary["total_return"] == 3.0
    assert analysis.summary["annualized_return"] == 12.0


def test_performance_analysis_falling_equity_curve_tracks_current_drawdown():
    curve = EquityCurve(
        dates=["2026-01-31", "2026-02-28", "2026-03-31"],
        equity_values=[99_000.0, 98_000.0, 97_000.0],
        cumulative_return=-3.0,
        peak_equity=100_000.0,
        drawdown_series=[-1_000.0, -2_000.0, -3_000.0],
        rolling_equity_highs=[100_000.0, 100_000.0, 100_000.0],
    )

    analysis = PerformanceAnalysis.from_equity_curve(curve)

    assert analysis.drawdown_analysis["max_drawdown"] == -3_000.0
    assert analysis.drawdown_analysis["average_drawdown"] == -2_000.0
    assert analysis.drawdown_analysis["drawdown_duration"] == 3
    assert analysis.drawdown_analysis["longest_drawdown"] == 3
    assert analysis.drawdown_analysis["current_drawdown"] == -3_000.0
    assert analysis.drawdown_analysis["drawdown_start_date"] == "2026-01-31"
    assert analysis.drawdown_analysis["drawdown_end_date"] == "2026-03-31"
    assert analysis.drawdown_analysis["recovery_date"] is None


def test_performance_analysis_drawdown_and_recovery_dates():
    curve = EquityCurve.from_trades(
        [
            trade("WIN", "2026-01-01", "2026-01-02", 100.0, 110.0, shares=10),
            trade("LOSS", "2026-01-02", "2026-01-03", 100.0, 80.0, shares=10),
            trade("RECOVER", "2026-01-03", "2026-01-04", 100.0, 130.0, shares=10),
        ]
    )

    analysis = PerformanceAnalysis.from_equity_curve(curve)

    assert analysis.drawdown_analysis["max_drawdown"] == -200.0
    assert analysis.drawdown_analysis["drawdown_duration"] == 1
    assert analysis.drawdown_analysis["longest_drawdown"] == 1
    assert analysis.drawdown_analysis["recovery_periods"] == [1]
    assert analysis.drawdown_analysis["drawdown_start_date"] == "2026-01-03"
    assert analysis.drawdown_analysis["drawdown_end_date"] == "2026-01-03"
    assert analysis.drawdown_analysis["recovery_date"] == "2026-01-04"


def test_performance_analysis_monthly_and_yearly_returns():
    curve = EquityCurve(
        dates=["2026-01-31", "2026-02-28", "2026-03-31", "2027-01-31"],
        equity_values=[101_000.0, 99_000.0, 103_000.0, 104_000.0],
        cumulative_return=4.0,
        peak_equity=104_000.0,
        drawdown_series=[0.0, -2_000.0, 0.0, 0.0],
        cagr=4.2,
        rolling_equity_highs=[101_000.0, 101_000.0, 103_000.0, 104_000.0],
    )

    analysis = PerformanceAnalysis.from_equity_curve(curve)

    assert analysis.monthly_returns["2026-01"] == 1.0
    assert analysis.monthly_returns["2026-02"] == pytest.approx(-1.9801980198)
    assert analysis.monthly_returns["2026-03"] == pytest.approx(4.0404040404)
    assert analysis.monthly_returns["2027-01"] == pytest.approx(0.9708737864)
    assert analysis.yearly_returns["2026"] == 3.0
    assert analysis.yearly_returns["2027"] == pytest.approx(0.9708737864)
    assert analysis.best_month == ("2026-03", pytest.approx(4.0404040404))
    assert analysis.worst_month == ("2026-02", pytest.approx(-1.9801980198))
    assert analysis.best_year == ("2026", 3.0)
    assert analysis.worst_year == ("2027", pytest.approx(0.9708737864))
    assert analysis.positive_months == 3
    assert analysis.negative_months == 1
    assert analysis.positive_month_rate == 0.75
    assert analysis.summary["monthly_returns"] == analysis.monthly_returns
    assert analysis.summary["yearly_returns"] == analysis.yearly_returns


def test_performance_analysis_output_is_deterministic():
    curve = EquityCurve(
        dates=["2026-01-31", "2026-02-28"],
        equity_values=[101_000.0, 99_000.0],
        cumulative_return=-1.0,
        peak_equity=101_000.0,
        drawdown_series=[0.0, -2_000.0],
        rolling_equity_highs=[101_000.0, 101_000.0],
    )

    assert (
        PerformanceAnalysis.from_equity_curve(curve)
        == PerformanceAnalysis.from_equity_curve(curve)
    )
