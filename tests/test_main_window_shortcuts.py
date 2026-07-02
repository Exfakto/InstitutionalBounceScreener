import pytest
from PySide6.QtWidgets import QApplication, QMainWindow

from ui import main_window as main_window_module
from ui.main_window import MainWindow


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance()

    if application is None:
        application = QApplication([])

    return application


def build_shortcut_window(app):
    window = MainWindow.__new__(MainWindow)
    QMainWindow.__init__(window)
    window.calls = []

    for _, _, _, handler_name in MainWindow.SHORTCUT_ACTIONS:
        setattr(
            window,
            handler_name,
            lambda name=handler_name: window.calls.append(name),
        )

    return window


def test_main_window_shortcuts_are_registered(app):
    window = build_shortcut_window(app)

    window.register_shortcuts()

    shortcuts = {
        action.shortcut().toString(): action.text()
        for action in window.shortcut_actions.values()
    }

    assert shortcuts["Ctrl+R"] == "Run Screener"
    assert shortcuts["Ctrl+U"] == "Update Universe"
    assert shortcuts["Ctrl+D"] == "Download Prices"
    assert shortcuts["Ctrl+I"] == "Calculate Indicators"
    assert shortcuts["Ctrl+S"] == "Detect Support"
    assert shortcuts["Ctrl+B"] == "Validate Bounces"
    assert shortcuts["Ctrl+O"] == "Open Selected Stock Detail"
    assert shortcuts["Ctrl+W"] == "Add Selected Candidate to Watchlist"
    assert shortcuts["Ctrl+E"] == "Open Export Center"
    assert shortcuts["Ctrl+,"] == "Open Settings"
    assert shortcuts["F1"] == "Open About & Diagnostics"
    assert shortcuts["Esc"] == "Clear Selection"


def test_shortcut_actions_call_existing_handlers(app):
    window = build_shortcut_window(app)
    window.register_shortcuts()

    window.run_screener_action.trigger()
    window.update_universe_action.trigger()
    window.download_prices_action.trigger()

    assert window.calls == [
        "run_screener",
        "update_universe",
        "download_prices",
    ]


def test_no_duplicate_shortcuts_after_repeated_registration(app):
    window = build_shortcut_window(app)

    window.register_shortcuts()
    initial_actions = list(window.actions())
    window.register_shortcuts()

    assert window.actions() == initial_actions
    assert len(window.shortcut_actions) == len(MainWindow.SHORTCUT_ACTIONS)


class FakeCandidateTable:
    def __init__(self, ticker=None):
        self.ticker = ticker
        self.cleared = False

    def selected_ticker(self):
        return self.ticker

    def clearSelection(self):
        self.cleared = True
        self.ticker = None


def test_unavailable_selected_candidate_shortcut_does_not_crash(app):
    window = MainWindow.__new__(MainWindow)
    QMainWindow.__init__(window)
    window.candidates_table = FakeCandidateTable(None)
    window.opened = False
    window.open_stock_detail = lambda ticker: setattr(window, "opened", True)

    window.open_selected_stock_detail()

    assert window.opened is False


def test_escape_clears_current_selection(app):
    window = MainWindow.__new__(MainWindow)
    QMainWindow.__init__(window)
    window.candidates_table = FakeCandidateTable("AAPL")
    window.updated = False
    window.update_open_detail_state = lambda: setattr(window, "updated", True)

    window.clear_current_selection()

    assert window.candidates_table.cleared is True
    assert window.updated is True


class FakeDialog:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.executed = False

    def exec(self):
        self.executed = True
        return 0


def test_dialog_shortcuts_are_wired_safely(app, monkeypatch):
    window = MainWindow.__new__(MainWindow)
    QMainWindow.__init__(window)

    monkeypatch.setattr(main_window_module, "ExportDialog", FakeDialog)
    monkeypatch.setattr(main_window_module, "SettingsDialog", FakeDialog)
    monkeypatch.setattr(main_window_module, "AboutDialog", FakeDialog)

    window.open_export_dialog()
    window.open_settings_dialog()
    window.open_about_dialog()

    assert window.export_dialog.executed is True
    assert window.settings_dialog.executed is True
    assert window.about_dialog.executed is True
