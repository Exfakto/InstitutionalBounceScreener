from PySide6.QtWidgets import QApplication

from services.screening_performance_analytics_service import (
    ScreeningPerformanceAnalytics,
    ScreeningStageTiming,
)
from ui.widgets.screening_performance_panel import ScreeningPerformancePanel


def app():
    return QApplication.instance() or QApplication([])


def analytics():
    stages = [
        ScreeningStageTiming("universe_loading", "Universe loading", 1.0),
        ScreeningStageTiming(
            "technical_indicator_calculation",
            "Technical indicator calculation",
            2.0,
            previous_duration_seconds=3.0,
            delta_seconds=-1.0,
            percent_delta=-33.3333,
            classification="faster",
        ),
    ]
    return ScreeningPerformanceAnalytics(
        run_id="run-1",
        total_screening_time_seconds=3.0,
        average_time_per_symbol_seconds=1.5,
        symbol_count=2,
        slowest_stage=stages[1],
        stages=stages,
    )


def test_screening_performance_panel_renders_analytics():
    app()
    panel = ScreeningPerformancePanel()

    panel.set_analytics(analytics())

    assert panel.message_label.isHidden()
    assert "Total: 3.00s" in panel.summary_label.text()
    assert "Avg/symbol: 1.50s" in panel.summary_label.text()
    assert panel.stage_table.rowCount() == 2
    assert panel.stage_table.item(0, 0).text() == "Universe loading"
    assert panel.stage_table.item(1, 5).text() == "faster"
    if panel.chart_view is not None:
        assert not panel.chart_view.isHidden()
        assert len(panel.chart.series()) == 1


def test_screening_performance_panel_empty_state():
    app()
    panel = ScreeningPerformancePanel()

    panel.set_analytics(None)

    assert panel.message_label.text() == "No screening performance metrics available"
    assert panel.stage_table.isHidden()
    assert panel.stage_table.rowCount() == 0


def test_screening_performance_panel_refresh_uses_controller():
    app()

    class Controller:
        def __init__(self):
            self.called = False

        def get_screening_performance_analytics(self):
            self.called = True
            return analytics()

    controller = Controller()
    panel = ScreeningPerformancePanel(controller=controller)

    loaded = panel.refresh_analytics()

    assert controller.called is True
    assert loaded.run_id == "run-1"
    assert panel.stage_table.rowCount() == 2


def test_screening_performance_panel_error_state():
    app()

    class Controller:
        def get_screening_performance_analytics(self):
            raise RuntimeError("metrics unavailable")

    panel = ScreeningPerformancePanel(controller=Controller())

    assert panel.refresh_analytics() is None
    assert panel.message_label.text() == "Unable to load screening performance analytics"
    assert panel.message_label.property("state") == "error"
