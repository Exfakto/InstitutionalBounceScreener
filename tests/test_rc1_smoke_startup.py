from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def app():
    return QApplication.instance() or QApplication([])


def test_rc1_smoke_application_startup_and_main_window_load():
    app()

    window = MainWindow()

    assert window.windowTitle() == "Institutional Bounce Screener"
    assert window.centralWidget() is not None
    assert window.dashboard is not None
    assert window.screening_results_panel is not None
    assert window.statusBar() is not None
    assert window.minimumSize().width() <= 760
    assert window.minimumSize().height() <= 520
    window.close()
