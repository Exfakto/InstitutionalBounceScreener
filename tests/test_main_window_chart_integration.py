from PySide6.QtWidgets import QApplication, QSplitter, QTabWidget

from ui.main_window import MainWindow


def test_main_window_uses_professional_splitter_layout():
    app = QApplication.instance() or QApplication([])
    window = MainWindow()

    try:
        assert isinstance(window.workspace_splitter, QSplitter)
        assert isinstance(window.center_splitter, QSplitter)
        assert isinstance(window.bottom_splitter, QSplitter)
        assert isinstance(window.bottom_left_tabs, QTabWidget)
        assert isinstance(window.bottom_right_tabs, QTabWidget)

        assert window.workspace_splitter.count() == 2
        assert window.center_splitter.count() == 2
        assert window.bottom_splitter.count() == 2

        assert window.center_splitter.widget(0) is window.price_chart
        assert window.center_splitter.widget(1) is window.decision_panel

        assert window.bottom_left_tabs.tabText(0) == "Candidates"
        assert window.bottom_left_tabs.tabText(1) == "Watchlist"
        assert window.bottom_left_tabs.tabText(2) == "Portfolio"
        assert window.bottom_left_tabs.tabText(3) == "Trade Journal"
        assert window.bottom_right_tabs.tabText(0) == "Activity"
    finally:
        window.close()


class FakeTradeCard:

    def __init__(self):
        self.card = None
        self.placeholder = None
        self.cleared = False
        self.set_count = 0

    def set_trade_card(self, card):
        self.card = card
        self.placeholder = None
        self.cleared = False
        self.set_count += 1

    def set_placeholder(self, text):
        self.placeholder = text
        self.card = None
        self.cleared = False

    def clear(self):
        self.cleared = True
        self.card = None
        self.placeholder = None


class FakeOperationsToolbar:

    def __init__(self):
        self.open_detail_enabled = None

    def set_open_detail_enabled(self, enabled):
        self.open_detail_enabled = enabled


class FakeCandidateTable:

    def __init__(self, ticker=None):
        self.ticker = ticker

    def selected_ticker(self):
        return self.ticker


class FakeResearchPreview:

    def __init__(self):
        self.candidate = None
        self.cleared = False

    def set_candidate(self, candidate):
        self.candidate = candidate

    def clear(self):
        self.cleared = True


class FakePriceChart:

    def __init__(self):
        self.chart_data = None
        self.cleared = False

    def set_chart_data(self, chart_data):
        self.chart_data = chart_data

    def clear(self):
        self.cleared = True


class FakeChartController:

    def __init__(self, chart_data=None, error=None):
        self.chart_data = chart_data or {"ticker": "AAPL", "prices": []}
        self.error = error
        self.ticker = None

    def get_chart_data(self, ticker):
        self.ticker = ticker

        if self.error is not None:
            raise self.error

        return self.chart_data


def build_window(ticker=None, chart_controller=None, candidate="candidate"):
    window = MainWindow.__new__(MainWindow)
    window.candidates_table = FakeCandidateTable(ticker)
    window.operations_toolbar = FakeOperationsToolbar()
    window.research_preview = FakeResearchPreview()
    window.trade_card = FakeTradeCard()
    window.price_chart = FakePriceChart()
    window.chart_controller = chart_controller or FakeChartController()
    window.candidates_by_ticker = {"AAPL": candidate}
    return window


def test_selection_updates_research_preview_and_price_chart():
    chart_data = {"ticker": "AAPL", "prices": [{"close": 100.0}]}
    chart_controller = FakeChartController(chart_data=chart_data)
    candidate = type("Candidate", (), {"trade_card": {"ticker": "AAPL"}})()
    window = build_window("AAPL", chart_controller, candidate=candidate)

    window.update_open_detail_state()

    assert window.operations_toolbar.open_detail_enabled is True
    assert window.research_preview.candidate == candidate
    assert window.trade_card.card == {"ticker": "AAPL"}
    assert chart_controller.ticker == "AAPL"
    assert window.price_chart.chart_data == chart_data


def test_empty_selection_clears_research_preview_and_price_chart():
    window = build_window(None)

    window.update_open_detail_state()

    assert window.operations_toolbar.open_detail_enabled is False
    assert window.research_preview.cleared is True
    assert window.trade_card.cleared is True
    assert window.price_chart.cleared is True


def test_chart_data_failure_does_not_crash_selection_update():
    window = build_window(
        "AAPL",
        FakeChartController(error=RuntimeError("planned failure")),
    )

    window.update_open_detail_state()

    assert window.research_preview.candidate == "candidate"
    assert window.trade_card.placeholder == "No trade plan available."
    assert window.price_chart.chart_data["ticker"] == "AAPL"
    assert window.price_chart.chart_data["prices"] == []
    assert "Chart data unavailable" in window.price_chart.chart_data["warnings"]


def test_selection_without_trade_card_shows_placeholder():
    window = build_window("AAPL")

    window.update_open_detail_state()

    assert window.trade_card.card is None
    assert window.trade_card.placeholder == "No trade plan available."


def test_repeated_selections_update_existing_trade_card_widget():
    first_candidate = type("Candidate", (), {"trade_card": {"ticker": "AAPL"}})()
    second_candidate = type("Candidate", (), {"trade_card": {"ticker": "MSFT"}})()
    window = build_window("AAPL", candidate=first_candidate)
    trade_card_widget = window.trade_card

    window.update_open_detail_state()
    window.candidates_by_ticker["AAPL"] = second_candidate
    window.update_open_detail_state()

    assert window.trade_card is trade_card_widget
    assert window.trade_card.card == {"ticker": "MSFT"}
    assert window.trade_card.set_count == 2
