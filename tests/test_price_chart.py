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


def close_only_chart_data():
    data = chart_data()

    for price in data["prices"]:
        price["open"] = None
        price["high"] = None
        price["low"] = None

    return data


def incomplete_ohlc_chart_data():
    data = chart_data()
    data["prices"][1]["high"] = None

    return data


def chart_data_with_support_zones(zones):
    data = chart_data()
    data["support_zones"] = zones
    return data


def price_series_name():
    if price_chart_module.CANDLESTICKS_AVAILABLE:
        return "Price"

    return "Close"


def validated_support_zone():
    return {
        "support_level_id": 1,
        "support_low": 99.0,
        "support_high": 100.0,
        "support_strength": 85.0,
        "validated": True,
        "total_touches": 6,
        "successful_bounces": 5,
        "failed_breakdowns": 1,
        "neutral_touches": 0,
        "bounce_success_rate": 83.333,
        "average_bounce_pct": 6.5,
        "median_bounce_pct": 6.0,
        "average_days_to_bounce_peak": 8.0,
        "bounce_count": 5,
        "success_rate": 83.333,
    }


def missing_field_validated_support_zone():
    zone = validated_support_zone()

    for key in [
        "total_touches",
        "successful_bounces",
        "bounce_success_rate",
        "bounce_count",
        "success_rate",
    ]:
        zone[key] = None

    return zone


def non_validated_support_zone():
    return {
        "support_level_id": 2,
        "support_low": 97.5,
        "support_high": 98.5,
        "support_strength": 60.0,
        "validated": False,
        "bounce_count": None,
        "success_rate": None,
    }


def test_price_chart_clear_shows_empty_state(app):
    widget = PriceChart()
    widget.set_chart_data(chart_data())

    widget.clear()

    assert widget.summary_label.text() == (
        "No chart data available.\nSync historical data or select another ticker."
    )
    assert widget.readout_label.text() == "No price selected."
    assert widget.header_title_label.text() == "Price Chart"
    assert widget.header_meta_label.text() == "No ticker selected"
    assert widget.chart_data is None

    if widget.chart is not None:
        assert widget.chart.series() == []


def test_price_chart_controls_exist(app):
    widget = PriceChart()

    assert widget.reset_button.text() == "Reset"
    assert widget.zoom_in_button.text() == "Zoom +"
    assert widget.zoom_out_button.text() == "Zoom -"
    assert widget.pan_left_button.text() == "Pan <"
    assert widget.pan_right_button.text() == "Pan >"
    assert widget.controls_layout.count() == 6


def test_price_chart_interaction_methods_are_callable(app):
    widget = PriceChart()
    widget.set_chart_data(chart_data())

    widget.reset_view()
    widget.zoom_in()
    widget.zoom_out()
    widget.pan_left()
    widget.pan_right()

    assert widget.chart_data["ticker"] == "AAPL"


def test_price_chart_missing_price_history_shows_message(app):
    widget = PriceChart()

    widget.set_chart_data({"ticker": "EMPTY", "prices": []})

    assert widget.summary_label.text() == (
        "No chart data available.\nSync historical data or select another ticker."
    )
    assert widget.readout_label.text() == "No price selected."
    assert widget.header_title_label.text() == "EMPTY"
    assert widget.header_meta_label.text() == "No data | 0 support zones"
    assert widget.support_band_series == []
    assert widget.support_labels == []

    if widget.chart is not None:
        assert widget.chart.series() == []


def test_price_chart_plots_close_prices_when_qtcharts_available(app):
    widget = PriceChart()

    widget.set_chart_data(chart_data())

    if not price_chart_module.CHARTS_AVAILABLE:
        pytest.skip("QtCharts backend unavailable")

    assert widget.summary_label.isHidden() is True
    assert len(widget.chart.series()) == 1
    assert widget.chart.series()[0].name() == price_series_name()
    assert widget.chart.title() == ""
    assert widget.header_title_label.text() == "AAPL"
    assert "2026-01-01 to 2026-01-02" in widget.header_meta_label.text()
    assert "Last close 103.50" in widget.header_meta_label.text()
    assert "0 support zones" in widget.header_meta_label.text()

    if price_chart_module.CANDLESTICKS_AVAILABLE:
        assert widget.render_mode == "candlestick"
        assert widget.candlestick_series is widget.chart.series()[0]
    else:
        assert widget.render_mode == "line"
        assert widget.chart.series()[0].count() == 2


def test_price_chart_set_chart_data_updates_latest_readout(app):
    widget = PriceChart()

    widget.set_chart_data(chart_data())

    assert "Latest: 2026-01-02" in widget.readout_label.text()
    assert "O 101.00" in widget.readout_label.text()
    assert "H 104.00" in widget.readout_label.text()
    assert "L 100.00" in widget.readout_label.text()
    assert "C 103.50" in widget.readout_label.text()
    assert "Vol 1200" in widget.readout_label.text()


def test_price_chart_close_only_data_falls_back_to_line_mode(app):
    widget = PriceChart()

    widget.set_chart_data(close_only_chart_data())

    if not price_chart_module.CHARTS_AVAILABLE:
        pytest.skip("QtCharts backend unavailable")

    assert widget.render_mode == "line"
    assert widget.candlestick_series is None
    assert [series.name() for series in widget.chart.series()] == ["Close"]
    assert widget.chart.series()[0].count() == 2
    assert "O N/A" in widget.readout_label.text()
    assert "C 103.50" in widget.readout_label.text()


def test_price_chart_missing_ohlc_data_falls_back_to_line_mode(app):
    widget = PriceChart()

    widget.set_chart_data(incomplete_ohlc_chart_data())

    if not price_chart_module.CHARTS_AVAILABLE:
        pytest.skip("QtCharts backend unavailable")

    assert widget.render_mode == "line"
    assert widget.candlestick_series is None
    assert [series.name() for series in widget.chart.series()] == ["Close"]
    assert "H N/A" in widget.readout_label.text()


def test_price_chart_replaces_existing_series_on_update(app):
    widget = PriceChart()

    widget.set_chart_data(chart_data())
    replacement = chart_data()
    replacement["prices"] = replacement["prices"][:1]
    widget.set_chart_data(replacement)

    if not price_chart_module.CHARTS_AVAILABLE:
        pytest.skip("QtCharts backend unavailable")

    assert len(widget.chart.series()) == 1
    assert widget.chart.series()[0].name() == price_series_name()
    assert "Latest: 2026-01-01" in widget.readout_label.text()
    assert "2026-01-01" in widget.header_meta_label.text()
    assert "Last close 101.00" in widget.header_meta_label.text()


def test_price_chart_plots_price_with_sma20_overlay(app):
    widget = PriceChart()

    widget.set_chart_data(chart_data_with_smas(sma20=True))

    if not price_chart_module.CHARTS_AVAILABLE:
        pytest.skip("QtCharts backend unavailable")

    assert [series.name() for series in widget.chart.series()] == [
        price_series_name(),
        "SMA20",
    ]
    assert widget.overlay_series["sma20"].count() == 2


def test_price_chart_plots_price_with_sma20_and_sma50_overlays(app):
    widget = PriceChart()

    widget.set_chart_data(chart_data_with_smas(sma20=True, sma50=True))

    if not price_chart_module.CHARTS_AVAILABLE:
        pytest.skip("QtCharts backend unavailable")

    assert [series.name() for series in widget.chart.series()] == [
        price_series_name(),
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
        price_series_name(),
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
    data = chart_data_with_smas(sma20=True, sma50=True, sma200=True)
    data["support_zones"] = [validated_support_zone()]
    widget.set_chart_data(data)

    widget.clear()

    assert widget.overlay_series == {}
    assert widget.support_band_series == []
    assert widget.support_labels == []
    assert widget.series is None
    assert widget.candlestick_series is None
    assert widget.render_mode is None

    if widget.chart is not None:
        assert widget.chart.series() == []


def test_price_chart_renders_single_validated_support_zone(app):
    widget = PriceChart()

    widget.set_chart_data(chart_data_with_support_zones([validated_support_zone()]))

    if not price_chart_module.CHARTS_AVAILABLE:
        pytest.skip("QtCharts backend unavailable")

    assert len(widget.support_band_series) == 1
    assert widget.support_band_series[0].name() == "Support 1"
    assert len(widget.support_labels) == 1
    assert "Validated: 5/6 bounces" in widget.support_labels[0].text()
    assert "83%" in widget.support_labels[0].text()
    assert [series.name() for series in widget.chart.series()] == [
        "Support 1",
        price_series_name(),
    ]


def test_price_chart_renders_multiple_support_zones(app):
    widget = PriceChart()

    widget.set_chart_data(
        chart_data_with_support_zones(
            [
                validated_support_zone(),
                non_validated_support_zone(),
            ]
        )
    )

    if not price_chart_module.CHARTS_AVAILABLE:
        pytest.skip("QtCharts backend unavailable")

    assert len(widget.support_band_series) == 2
    assert [series.name() for series in widget.support_band_series] == [
        "Support 1",
        "Support 2",
    ]
    assert len(widget.support_labels) == 2


def test_price_chart_renders_multiple_validated_support_zone_labels(app):
    widget = PriceChart()
    second_zone = validated_support_zone()
    second_zone["support_level_id"] = 3
    second_zone["support_low"] = 96.0
    second_zone["support_high"] = 97.0
    second_zone["total_touches"] = 4
    second_zone["successful_bounces"] = 4
    second_zone["bounce_success_rate"] = 100.0

    widget.set_chart_data(
        chart_data_with_support_zones(
            [
                validated_support_zone(),
                second_zone,
            ]
        )
    )

    if not price_chart_module.CHARTS_AVAILABLE:
        pytest.skip("QtCharts backend unavailable")

    label_texts = [label.text() for label in widget.support_labels]

    assert len(label_texts) == 2
    assert "Validated: 5/6 bounces - 83%" in label_texts
    assert "Validated: 4/4 bounces - 100%" in label_texts


def test_price_chart_renders_non_validated_support_zone(app):
    widget = PriceChart()

    widget.set_chart_data(chart_data_with_support_zones([non_validated_support_zone()]))

    if not price_chart_module.CHARTS_AVAILABLE:
        pytest.skip("QtCharts backend unavailable")

    assert len(widget.support_band_series) == 1
    assert widget.support_labels[0].text() == "Support"


def test_price_chart_renders_validated_support_label_with_missing_fields(app):
    widget = PriceChart()

    widget.set_chart_data(
        chart_data_with_support_zones([missing_field_validated_support_zone()])
    )

    if not price_chart_module.CHARTS_AVAILABLE:
        pytest.skip("QtCharts backend unavailable")

    assert len(widget.support_band_series) == 1
    assert widget.support_labels[0].text() == "Validated support"


def test_price_chart_no_support_zones_renders_only_price_series(app):
    widget = PriceChart()

    widget.set_chart_data(chart_data())

    if not price_chart_module.CHARTS_AVAILABLE:
        pytest.skip("QtCharts backend unavailable")

    assert widget.support_band_series == []
    assert widget.support_labels == []
    assert [series.name() for series in widget.chart.series()] == [price_series_name()]


def test_price_chart_replaces_support_zones_on_repeated_update(app):
    widget = PriceChart()
    widget.set_chart_data(
        chart_data_with_support_zones(
            [
                validated_support_zone(),
                non_validated_support_zone(),
            ]
        )
    )

    widget.set_chart_data(chart_data_with_support_zones([validated_support_zone()]))

    if not price_chart_module.CHARTS_AVAILABLE:
        pytest.skip("QtCharts backend unavailable")

    assert len(widget.support_band_series) == 1
    assert len(widget.support_labels) == 1
    assert "1 support zones" in widget.header_meta_label.text()


def test_price_chart_repeated_updates_do_not_duplicate_controls(app):
    widget = PriceChart()

    widget.set_chart_data(chart_data())
    widget.set_chart_data(chart_data_with_smas(sma20=True, sma50=True))
    widget.set_chart_data(chart_data_with_support_zones([validated_support_zone()]))

    assert widget.controls_layout.count() == 6
    assert widget.reset_button.text() == "Reset"
    assert widget.header_title_label.text() == "AAPL"


def test_price_chart_placeholder_summary_when_backend_unavailable(app, monkeypatch):
    monkeypatch.setattr(price_chart_module, "CHARTS_AVAILABLE", False)
    widget = PriceChart()

    widget.set_chart_data(chart_data())

    assert "AAPL" in widget.summary_label.text()
    assert "Latest close: 103.5" in widget.summary_label.text()
    assert "Price rows: 2" in widget.summary_label.text()
    assert "Chart rendering backend is unavailable." in widget.summary_label.text()
    assert widget.header_title_label.text() == "AAPL"
    assert "Chart unavailable" in widget.header_meta_label.text()
    assert widget.chart_view is None


def test_price_chart_header_handles_missing_optional_fields(app):
    widget = PriceChart()
    data = {
        "prices": [
            {
                "date": "2026-01-03",
                "close": 10.0,
            }
        ]
    }

    widget.set_chart_data(data)

    assert widget.header_title_label.text() == "Price Chart"
    assert "Last close 10.00" in widget.header_meta_label.text()
    assert "0 support zones" in widget.header_meta_label.text()
