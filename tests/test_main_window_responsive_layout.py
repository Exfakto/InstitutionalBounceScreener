from PySide6.QtCore import QSize
from PySide6.QtWidgets import QApplication, QScrollArea

from ui.main_window import MainWindow


def app():
    return QApplication.instance() or QApplication([])


def test_main_window_minimum_size_is_1080p_friendly():
    app()
    window = MainWindow()

    minimum = window.minimumSize()

    assert minimum.width() <= 760
    assert minimum.height() <= 520
    window.close()


def test_main_window_resizes_to_1366_by_768_without_exceeding_viewport():
    app()
    window = MainWindow()

    window.resize(1366, 768)
    window.ensure_window_fits_screen()

    assert window.width() <= 1366
    assert window.height() <= 768
    assert window.minimumSize().width() <= 1366
    assert window.minimumSize().height() <= 768
    assert window.statusBar() is not None
    window.close()


def test_main_window_resizes_to_1920_by_1080_without_clipping_pressure():
    app()
    window = MainWindow()

    window.resize(1920, 1080)
    window.ensure_window_fits_screen()

    assert window.width() <= 1920
    assert window.height() <= 1080
    assert window.centralWidget().sizePolicy().verticalPolicy() is not None
    window.close()


def test_main_window_key_panels_are_scrollable_or_resizable():
    app()
    window = MainWindow()

    assert isinstance(window.screener_filters_panel, QScrollArea)
    assert window.screener_filters_panel.widgetResizable() is True
    assert isinstance(window.screening_results_panel.scroll_area, QScrollArea)
    assert window.screening_results_panel.scroll_area.widgetResizable() is True
    assert window.dashboard.maximumHeight() <= 150
    assert window.candidates_table.minimumSize().height() <= 160
    assert window.price_chart.minimumSize().height() <= 140
    window.close()


def test_main_window_layout_integrity_after_small_resize():
    app()
    window = MainWindow()

    window.resize(QSize(900, 620))

    assert window.header_bar.isVisibleTo(window)
    assert window.kpi_strip.isVisibleTo(window)
    assert window.operations_toolbar.isVisibleTo(window)
    assert window.screener_workspace_splitter.count() == 2
    assert window.statusBar() is not None
    window.close()
