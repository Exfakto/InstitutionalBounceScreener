from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication, QLabel, QTableWidget

from ui.widgets.performance_dashboard import PerformanceDashboard


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance()

    if application is None:
        application = QApplication([])

    return application


def portfolio_stats(**overrides):
    stats = {
        "total_trades": 12,
        "open_trades": 3,
        "closed_trades": 9,
        "win_rate": 66.666667,
        "average_return_pct": 4.25,
        "profit_factor": 2.1,
        "expectancy": 3.4,
    }
    stats.update(overrides)
    return stats


def strategy_stats(**overrides):
    stats = {
        "opportunity_rating_statistics": {
            "Elite Bounce": {
                "trade_count": 4,
                "win_rate": 75.0,
                "average_return": 8.5,
            },
            "High Probability": {
                "trade_count": 3,
                "win_rate": 66.666667,
                "average_return": 4.0,
            },
            "Acceptable": {
                "trade_count": 2,
                "win_rate": 50.0,
                "average_return": 1.5,
            },
        },
        "confidence_statistics": {
            "Very High": {"trade_count": 2, "win_rate": 100.0, "average_return": 9.0},
            "High": {"trade_count": 4, "win_rate": 75.0, "average_return": 6.0},
            "Moderate": {"trade_count": 2, "win_rate": 50.0, "average_return": 1.0},
            "Low": {"trade_count": 1, "win_rate": 0.0, "average_return": -3.0},
        },
        "sector_statistics": {
            "Technology": {"trade_count": 5, "win_rate": 80.0, "average_return": 7.5},
            "Healthcare": {"trade_count": 2, "win_rate": 50.0, "average_return": 2.0},
            "Energy": {"trade_count": 1, "win_rate": 0.0, "average_return": -4.0},
            "Financials": {"trade_count": 1, "win_rate": 100.0, "average_return": 3.0},
            "Consumer": {"trade_count": 1, "win_rate": 100.0, "average_return": 2.5},
            "Utilities": {"trade_count": 1, "win_rate": 100.0, "average_return": 1.0},
        },
        "risk_reward_statistics": {
            "average_risk_reward": 2.4,
            "distribution": {
                "<1.5": 1,
                "1.5-2": 2,
                "2-3": 3,
                "3-5": 2,
                ">5": 1,
            },
        },
        "holding_period_statistics": {
            "0-5 days": 2,
            "6-10 days": 3,
            "11-20 days": 2,
            ">20 days": 1,
        },
    }
    stats.update(overrides)
    return stats


def table_text(table, row, column):
    item = table.item(row, column)
    return "" if item is None else item.text()


def test_performance_dashboard_empty_state(app):
    dashboard = PerformanceDashboard()

    assert dashboard.empty_state_label.text() == "No performance statistics available."
    assert dashboard.empty_state_label.isHidden() is False
    assert dashboard.dashboard_frame.isHidden() is True
    assert dashboard.summary_labels["total_trades"].text() == "-"
    assert table_text(dashboard.risk_reward_table, 0, 0) == "<1.5"
    assert table_text(dashboard.risk_reward_table, 0, 1) == "-"


def test_performance_dashboard_populated(app):
    dashboard = PerformanceDashboard()

    dashboard.set_statistics(portfolio_stats(), strategy_stats())

    assert dashboard.empty_state_label.isHidden() is True
    assert dashboard.dashboard_frame.isHidden() is False
    assert dashboard.summary_labels["total_trades"].text() == "12"
    assert dashboard.summary_labels["win_rate"].text() == "66.67%"
    assert dashboard.summary_labels["average_return"].text() == "4.25%"
    assert dashboard.summary_labels["profit_factor"].text() == "2.10"
    assert dashboard.summary_labels["expectancy"].text() == "3.40%"
    assert table_text(dashboard.rating_table, 0, 0) == "★★★★★"
    assert table_text(dashboard.rating_table, 0, 1) == "75.00%"
    assert table_text(dashboard.confidence_table, 1, 0) == "High"
    assert table_text(dashboard.confidence_table, 1, 2) == "6.00%"
    assert table_text(dashboard.sector_table, 0, 0) == "Technology"
    assert table_text(dashboard.sector_table, 0, 1) == "5"
    assert table_text(dashboard.risk_reward_table, 2, 1) == "3"
    assert table_text(dashboard.holding_table, 3, 1) == "1"


def test_performance_dashboard_accepts_object_statistics(app):
    dashboard = PerformanceDashboard()
    portfolio = SimpleNamespace(**portfolio_stats())
    strategy = SimpleNamespace(**strategy_stats())

    dashboard.set_statistics(portfolio, strategy)

    assert dashboard.summary_labels["closed_trades"].text() == "9"
    assert table_text(dashboard.rating_table, 1, 1) == "66.67%"


def test_performance_dashboard_missing_statistics(app):
    dashboard = PerformanceDashboard()

    dashboard.set_statistics(portfolio_stats(total_trades=None), None)

    assert dashboard.empty_state_label.isHidden() is True
    assert dashboard.summary_labels["total_trades"].text() == "-"
    assert dashboard.summary_labels["open_trades"].text() == "3"
    assert table_text(dashboard.rating_table, 0, 1) == "-"
    assert table_text(dashboard.confidence_table, 4, 2) == "-"


def test_performance_dashboard_repeated_updates_do_not_duplicate_widgets(app):
    dashboard = PerformanceDashboard()
    initial_label_count = len(dashboard.findChildren(QLabel))
    initial_table_count = len(dashboard.findChildren(QTableWidget))

    dashboard.set_statistics(portfolio_stats(total_trades=4), strategy_stats())
    dashboard.set_statistics(portfolio_stats(total_trades=8), strategy_stats())
    dashboard.set_statistics(None, None)

    assert len(dashboard.findChildren(QLabel)) == initial_label_count
    assert len(dashboard.findChildren(QTableWidget)) == initial_table_count
    assert dashboard.summary_labels["total_trades"].text() == "-"


def test_performance_dashboard_clear(app):
    dashboard = PerformanceDashboard()
    dashboard.set_statistics(portfolio_stats(), strategy_stats())

    dashboard.clear()

    assert dashboard.empty_state_label.isHidden() is False
    assert dashboard.dashboard_frame.isHidden() is True
    assert all(label.text() == "-" for label in dashboard.summary_labels.values())
    assert table_text(dashboard.rating_table, 0, 1) == "-"
    assert table_text(dashboard.sector_table, 0, 0) == ""


def test_performance_dashboard_layout_stability(app):
    dashboard = PerformanceDashboard()

    dashboard.set_statistics(portfolio_stats(), strategy_stats())

    assert dashboard.rating_table.rowCount() == 3
    assert dashboard.confidence_table.rowCount() == 5
    assert dashboard.sector_table.rowCount() == 5
    assert dashboard.risk_reward_table.rowCount() == 5
    assert dashboard.holding_table.rowCount() == 4
