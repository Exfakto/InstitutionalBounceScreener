from ui.main_window import MainWindow


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


def build_window(ticker=None, chart_controller=None):
    window = MainWindow.__new__(MainWindow)
    window.candidates_table = FakeCandidateTable(ticker)
    window.operations_toolbar = FakeOperationsToolbar()
    window.research_preview = FakeResearchPreview()
    window.price_chart = FakePriceChart()
    window.chart_controller = chart_controller or FakeChartController()
    window.candidates_by_ticker = {"AAPL": "candidate"}
    return window


def test_selection_updates_research_preview_and_price_chart():
    chart_data = {"ticker": "AAPL", "prices": [{"close": 100.0}]}
    chart_controller = FakeChartController(chart_data=chart_data)
    window = build_window("AAPL", chart_controller)

    window.update_open_detail_state()

    assert window.operations_toolbar.open_detail_enabled is True
    assert window.research_preview.candidate == "candidate"
    assert chart_controller.ticker == "AAPL"
    assert window.price_chart.chart_data == chart_data


def test_empty_selection_clears_research_preview_and_price_chart():
    window = build_window(None)

    window.update_open_detail_state()

    assert window.operations_toolbar.open_detail_enabled is False
    assert window.research_preview.cleared is True
    assert window.price_chart.cleared is True


def test_chart_data_failure_does_not_crash_selection_update():
    window = build_window(
        "AAPL",
        FakeChartController(error=RuntimeError("planned failure")),
    )

    window.update_open_detail_state()

    assert window.research_preview.candidate == "candidate"
    assert window.price_chart.chart_data["ticker"] == "AAPL"
    assert window.price_chart.chart_data["prices"] == []
    assert "Chart data unavailable" in window.price_chart.chart_data["warnings"]
