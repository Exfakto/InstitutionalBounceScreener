from PySide6.QtWidgets import QApplication, QScrollArea, QSizePolicy

from ui.widgets.dashboard import InstitutionalDashboard
from ui.widgets.screening_results_panel import ScreeningResultsPanel


def app():
    return QApplication.instance() or QApplication([])


def test_dashboard_panel_uses_scroll_area_for_overflow():
    app()
    dashboard = InstitutionalDashboard()

    assert isinstance(dashboard.scroll_area, QScrollArea)
    assert dashboard.scroll_area.widgetResizable() is True
    assert dashboard.scroll_area.horizontalScrollBarPolicy().name == "ScrollBarAlwaysOff"


def test_dashboard_panel_compact_table_minimums():
    app()
    dashboard = InstitutionalDashboard()

    assert dashboard.activity_feed_table.minimumHeight() <= 96
    assert dashboard.best_opportunities_table.minimumHeight() <= 88
    assert dashboard.best_opportunities_empty.minimumHeight() <= 56


def test_dashboard_panel_remains_usable_at_small_height():
    app()
    dashboard = InstitutionalDashboard()

    dashboard.resize(900, 220)

    assert dashboard.scroll_area.isVisibleTo(dashboard) is False or dashboard.scroll_area.widget() is not None
    assert dashboard.scroll_area.widgetResizable() is True
    assert dashboard.sizePolicy().horizontalPolicy() in {
        QSizePolicy.Preferred,
        QSizePolicy.Expanding,
    }


def test_screening_results_panel_scrollable_and_compact_tables():
    app()
    panel = ScreeningResultsPanel()

    assert isinstance(panel.scroll_area, QScrollArea)
    assert panel.scroll_area.widgetResizable() is True
    assert panel.ranked_candidates_table.minimumHeight() <= 96
    assert panel.run_history_table.minimumHeight() <= 96
    assert panel.backtest_trades_table.minimumHeight() <= 96
    assert panel.beta_review_table.minimumHeight() <= 96


def test_screening_results_panel_controls_remain_accessible_after_resize():
    app()
    panel = ScreeningResultsPanel()

    panel.resize(900, 520)

    assert panel.run_screening_button is not None
    assert panel.cancel_screening_button is not None
    assert panel.export_candidates_csv_button is not None
    assert panel.scroll_area.widgetResizable() is True
