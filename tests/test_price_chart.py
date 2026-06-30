import pytest
from PySide6.QtWidgets import QApplication

import ui.widgets.price_chart as price_chart_module
from ui.widgets.price_chart import PriceChart


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance()

    if application is None:
        application = QApplication([])

    return application


def chart_data():
    return {
        "ticker": "AAPL",
        "prices": [
            {
                "date": "2026-01-01",
                "open": 100.0,
                "high": 102.0,
                "low": 99.0,
                "close": 101.0,
                "volume": 1000,
            },
            {
                "date": "2026-01-02",
                "open": 101.0,
                "high": 104.0,
                "low": 100.0,
                "close": 103.5,
                "volume": 1200,
            },
        ],
        "indicators": [],
        "support_zones": [],
        "bounce_validations": [],
        "warnings": [],
    }


def chart_data_with_smas(sma20=True, sma50=False, sma200=False):
    data = chart_data()

    for index, price in enumerate(data["prices"]):
        if sma20:
            price["sma20"] = 100.0 + index

        if sma50:
            price["sma50"] = 99.0 + index

        if sma200:
            price["sma200"] = 95.0 + index

    return data


def test_price_chart_clear_shows_empty_state(app):
    widget = PriceChart()
    widget.set_chart_data(chart_data())

    widget.clear()

    assert widget.summary_label.text() == "Select a candidate to view chart."
    assert widget.chart_data is None

    if widget.chart is not None:
        assert widget.chart.series() == []


def test_price_chart_missing_price_history_shows_message(app):
    widget = PriceChart()

    widget.set_chart_data({"ticker": "EMPTY", "prices": []})

    assert widget.summary_label.text() == "No price history available."

    if widget.chart is not None:
        assert widget.chart.series() == []


def test_price_chart_plots_close_prices_when_qtcharts_available(app):
    widget = PriceChart()

    widget.set_chart_data(chart_data())

    if not price_chart_module.CHARTS_AVAILABLE:
        pytest.skip("QtCharts backend unavailable")

    assert widget.summary_label.isHidden() is True
    assert len(widget.chart.series()) == 1
    assert widget.chart.series()[0].count() == 2
    assert widget.chart.title() == "AAPL Close 103.50"


def test_price_chart_replaces_existing_series_on_update(app):
    widget = PriceChart()

    widget.set_chart_data(chart_data())
    replacement = chart_data()
    replacement["prices"] = replacement["prices"][:1]
    widget.set_chart_data(replacement)

    if not price_chart_module.CHARTS_AVAILABLE:
        pytest.skip("QtCharts backend unavailable")

    assert len(widget.chart.series()) == 1
    assert widget.chart.series()[0].count() == 1


def test_price_chart_plots_price_with_sma20_overlay(app):
    widget = PriceChart()

    widget.set_chart_data(chart_data_with_smas(sma20=True))

    if not price_chart_module.CHARTS_AVAILABLE:
        pytest.skip("QtCharts backend unavailable")

    assert [series.name() for series in widget.chart.series()] == ["Close", "SMA20"]
    assert widget.overlay_series["sma20"].count() == 2


def test_price_chart_plots_price_with_sma20_and_sma50_overlays(app):
    widget = PriceChart()

    widget.set_chart_data(chart_data_with_smas(sma20=True, sma50=True))

    if not price_chart_module.CHARTS_AVAILABLE:
        pytest.skip("QtCharts backend unavailable")

    assert [series.name() for series in widget.chart.series()] == [
        "Close",
        "SMA20",
        "SMA50",
    ]
    assert widget.overlay_series["sma20"].count() == 2
    assert widget.overlay_series["sma50"].count() == 2


def test_price_chart_plots_all_three_sma_overlays(app):
    widget = PriceChart()

    widget.set_chart_data(chart_data_with_smas(sma20=True, sma50=True, sma200=True))

    if not price_chart_module.CHARTS_AVAILABLE:
        pytest.skip("QtCharts backend unavailable")

    assert [series.name() for series in widget.chart.series()] == [
        "Close",
        "SMA20",
        "SMA50",
        "SMA200",
    ]
    assert widget.overlay_series["sma200"].count() == 2


def test_price_chart_ignores_missing_sma_values(app):
    widget = PriceChart()
    data = chart_data_with_smas(sma20=True, sma50=True)
    data["prices"][1]["sma20"] = None
    data["prices"][0]["sma50"] = None

    widget.set_chart_data(data)

    if not price_chart_module.CHARTS_AVAILABLE:
        pytest.skip("QtCharts backend unavailable")

    assert widget.overlay_series["sma20"].count() == 1
    assert widget.overlay_series["sma50"].count() == 1
    assert "sma200" not in widget.overlay_series


def test_price_chart_clear_resets_overlay_series(app):
    widget = PriceChart()
    widget.set_chart_data(chart_data_with_smas(sma20=True, sma50=True, sma200=True))

    widget.clear()

    assert widget.overlay_series == {}
    assert widget.series is None

    if widget.chart is not None:
        assert widget.chart.series() == []


def test_price_chart_placeholder_summary_when_backend_unavailable(app, monkeypatch):
    monkeypatch.setattr(price_chart_module, "CHARTS_AVAILABLE", False)
    widget = PriceChart()

    widget.set_chart_data(chart_data())

    assert "AAPL" in widget.summary_label.text()
    assert "Latest close: 103.5" in widget.summary_label.text()
    assert "Price rows: 2" in widget.summary_label.text()
    assert "Chart rendering backend is unavailable." in widget.summary_label.text()
    assert widget.chart_view is None
