from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QDateTime, QPointF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QGraphicsSimpleTextItem,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

try:
    from PySide6.QtCharts import (
        QAreaSeries,
        QChart,
        QChartView,
        QDateTimeAxis,
        QLineSeries,
        QValueAxis,
    )

    CHARTS_AVAILABLE = True
except ImportError:
    QAreaSeries = None
    QChart = None
    QChartView = None
    QDateTimeAxis = None
    QLineSeries = None
    QValueAxis = None
    CHARTS_AVAILABLE = False

try:
    from PySide6.QtCharts import QCandlestickSeries, QCandlestickSet

    CANDLESTICKS_AVAILABLE = True
except ImportError:
    QCandlestickSeries = None
    QCandlestickSet = None
    CANDLESTICKS_AVAILABLE = False


class PriceChart(QWidget):
    """
    Reusable read-only price chart widget.
    """

    EMPTY_MESSAGE = "Select a candidate to view chart."
    NO_PRICE_MESSAGE = "No price history available."
    BACKEND_UNAVAILABLE_MESSAGE = "Chart rendering backend is unavailable."
    READOUT_EMPTY_MESSAGE = "No price selected."
    COLOR_BACKGROUND = "#15181C"
    COLOR_PLOT_BACKGROUND = "#1E242B"
    COLOR_TEXT = "#F4F7FA"
    COLOR_MUTED_TEXT = "#A8B3C1"
    COLOR_GRID = "#3D4652"
    COLOR_CLOSE = "#4F8FDB"
    COLOR_SMA20 = "#41B883"
    COLOR_SMA50 = "#D6A23A"
    COLOR_SMA200 = "#E05A5A"
    COLOR_SUPPORT_VALIDATED = "#41B883"
    COLOR_SUPPORT_NORMAL = "#778391"
    COLOR_CANDLE_UP = "#41B883"
    COLOR_CANDLE_DOWN = "#E05A5A"
    SERIES_DEFINITIONS = [
        ("close", "Close", COLOR_CLOSE, 2),
        ("sma20", "SMA20", COLOR_SMA20, 1),
        ("sma50", "SMA50", COLOR_SMA50, 1),
        ("sma200", "SMA200", COLOR_SMA200, 1),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)

        self.chart = None
        self.chart_view = None
        self.series = None
        self.candlestick_series = None
        self.render_mode = None
        self.overlay_series = {}
        self.support_band_series = []
        self.support_labels = []
        self.chart_data = None
        self.last_pan_direction = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.summary_label = QLabel("")
        self.summary_label.setObjectName("PriceChartSummary")
        self.summary_label.setAlignment(Qt.AlignCenter)
        self.summary_label.setWordWrap(True)

        layout.addWidget(self.summary_label)
        self.controls_layout = QHBoxLayout()
        self.controls_layout.setContentsMargins(0, 0, 0, 0)
        self.controls_layout.setSpacing(8)

        self.reset_button = self.create_control_button("Reset", self.reset_view)
        self.zoom_in_button = self.create_control_button("Zoom +", self.zoom_in)
        self.zoom_out_button = self.create_control_button("Zoom -", self.zoom_out)
        self.pan_left_button = self.create_control_button("Pan <", self.pan_left)
        self.pan_right_button = self.create_control_button("Pan >", self.pan_right)

        for button in [
            self.reset_button,
            self.zoom_in_button,
            self.zoom_out_button,
            self.pan_left_button,
            self.pan_right_button,
        ]:
            self.controls_layout.addWidget(button)

        self.controls_layout.addStretch(1)
        layout.addLayout(self.controls_layout)

        self.readout_label = QLabel("")
        self.readout_label.setObjectName("PriceChartReadout")
        self.readout_label.setAlignment(Qt.AlignLeft)
        self.readout_label.setWordWrap(True)
        layout.addWidget(self.readout_label)

        if CHARTS_AVAILABLE:
            self.chart = self.create_chart()
            self.chart_view = QChartView(self.chart)
            self.chart_view.setRenderHint(QPainter.Antialiasing)
            self.chart_view.hide()
            layout.addWidget(self.chart_view, stretch=1)

        self.clear()

    def clear(self):
        """
        Reset the widget to its empty state.
        """

        self.chart_data = None
        self.summary_label.setText(self.EMPTY_MESSAGE)
        self.summary_label.show()
        self.readout_label.setText(self.READOUT_EMPTY_MESSAGE)

        if self.chart is not None:
            self.clear_chart()

        if self.chart_view is not None:
            self.chart_view.hide()

    def set_chart_data(self, chart_data):
        """
        Display chart data supplied by an external service/controller.
        """

        self.chart_data = chart_data or {}
        prices = self.chart_data.get("prices") or []

        if not prices:
            self.summary_label.setText(self.NO_PRICE_MESSAGE)
            self.summary_label.show()
            self.readout_label.setText(self.READOUT_EMPTY_MESSAGE)

            if self.chart is not None:
                self.clear_chart()

            if self.chart_view is not None:
                self.chart_view.hide()

            return

        if not CHARTS_AVAILABLE:
            self.update_readout(prices)
            self.summary_label.setText(self.placeholder_summary(self.chart_data))
            self.summary_label.show()
            return

        points = self.series_points(prices, "close")

        if not points:
            self.summary_label.setText(self.NO_PRICE_MESSAGE)
            self.summary_label.show()
            self.readout_label.setText(self.READOUT_EMPTY_MESSAGE)
            self.chart_view.hide()
            return

        self.update_readout(prices)
        self.render_chart(self.chart_data, points)
        self.summary_label.hide()
        self.chart_view.show()
        self.reset_view()

    def render_chart(self, chart_data, points):
        self.chart.removeAllSeries()
        for axis in self.chart.axes():
            self.chart.removeAxis(axis)

        self.series = None
        self.candlestick_series = None
        self.overlay_series = {}
        prices = chart_data.get("prices") or []
        support_zones = chart_data.get("support_zones") or []
        chart_series = []
        has_candlesticks = self.should_render_candlesticks(prices)

        support_band_series = self.create_support_band_series(
            support_zones,
            points[0][0],
            points[-1][0],
        )

        for support_band in support_band_series:
            chart_series.append(support_band)
            self.chart.addSeries(support_band)

        self.support_band_series = support_band_series

        if has_candlesticks:
            self.render_mode = "candlestick"
            candlesticks = self.create_candlestick_series(prices)
            chart_series.append(candlesticks)
            self.chart.addSeries(candlesticks)
            self.candlestick_series = candlesticks
            self.series = candlesticks
            series_definitions = self.SERIES_DEFINITIONS[1:]
        else:
            self.render_mode = "line"
            series_definitions = self.SERIES_DEFINITIONS

        for key, name, color, width in series_definitions:
            series_points = points if key == "close" else self.series_points(prices, key)

            if not series_points:
                continue

            series = self.create_series(name, color, width, series_points)
            chart_series.append(series)
            self.chart.addSeries(series)

            if key == "close":
                self.series = series
            else:
                self.overlay_series[key] = series

        self.chart.setTitle(self.chart_title(chart_data))
        self.chart.legend().setVisible(len(chart_series) > 1)
        self.chart.legend().setLabelColor(QColor(self.COLOR_TEXT))

        x_axis = QDateTimeAxis()
        x_axis.setFormat("MMM d")
        x_axis.setTitleText("Date")
        x_axis.setLabelsColor(QColor(self.COLOR_TEXT))
        x_axis.setTitleBrush(QColor(self.COLOR_MUTED_TEXT))
        x_axis.setGridLineColor(QColor(self.COLOR_GRID))
        x_axis.setRange(
            QDateTime.fromMSecsSinceEpoch(points[0][0]),
            QDateTime.fromMSecsSinceEpoch(points[-1][0]),
        )

        y_axis = QValueAxis()
        y_axis.setTitleText("Close")
        y_axis.setLabelFormat("%.2f")
        y_axis.setLabelsColor(QColor(self.COLOR_TEXT))
        y_axis.setTitleBrush(QColor(self.COLOR_MUTED_TEXT))
        y_axis.setGridLineColor(QColor(self.COLOR_GRID))
        line_values = [
            value
            for series_points in [
                self.series_points(prices, key)
                for key, _, _, _ in self.SERIES_DEFINITIONS
            ]
            for _, value in series_points
        ]
        self.apply_y_range(
            y_axis,
            line_values
            + self.ohlc_values(prices)
            + self.support_zone_values(support_zones),
        )

        self.chart.addAxis(x_axis, Qt.AlignBottom)
        self.chart.addAxis(y_axis, Qt.AlignLeft)
        for series in chart_series:
            series.attachAxis(x_axis)
            series.attachAxis(y_axis)

        self.add_support_labels(support_zones, points[0][0], points[-1][0])

    @classmethod
    def series_points(cls, prices, key):
        points = []

        for index, price in enumerate(prices):
            value = price.get(key)

            if value is None:
                continue

            points.append(
                (
                    cls.date_to_msecs(price.get("date"), index),
                    float(value),
                )
            )

        return points

    @staticmethod
    def create_series(name, color, width, points):
        series = QLineSeries()
        series.setName(name)
        series.setPen(QPen(QColor(color), width))

        for x_value, value in points:
            series.append(x_value, value)

        return series

    @classmethod
    def create_candlestick_series(cls, prices):
        series = QCandlestickSeries()
        series.setName("Price")
        series.setIncreasingColor(QColor(cls.COLOR_CANDLE_UP))
        series.setDecreasingColor(QColor(cls.COLOR_CANDLE_DOWN))

        for index, price in enumerate(prices):
            if not cls.has_ohlc(price):
                continue

            candle = QCandlestickSet(
                float(price.get("open")),
                float(price.get("high")),
                float(price.get("low")),
                float(price.get("close")),
                cls.date_to_msecs(price.get("date"), index),
            )
            series.append(candle)

        return series

    @classmethod
    def should_render_candlesticks(cls, prices):
        if not CHARTS_AVAILABLE or not CANDLESTICKS_AVAILABLE:
            return False

        return bool(prices) and all(cls.has_ohlc(price) for price in prices)

    @staticmethod
    def has_ohlc(price):
        return all(
            price.get(key) is not None
            for key in ["open", "high", "low", "close"]
        )

    @classmethod
    def create_support_band_series(cls, support_zones, start_x, end_x):
        bands = []

        for index, zone in enumerate(support_zones):
            low = zone.get("support_low")
            high = zone.get("support_high")

            if low is None or high is None:
                continue

            lower = QLineSeries()
            upper = QLineSeries()

            lower.append(start_x, float(low))
            lower.append(end_x, float(low))
            upper.append(start_x, float(high))
            upper.append(end_x, float(high))

            band = QAreaSeries(upper, lower)
            band.boundary_series = (upper, lower)
            band.setName(f"Support {index + 1}")
            band.setPen(QPen(Qt.NoPen))
            band.setBrush(cls.support_zone_brush(zone))
            bands.append(band)

        return bands

    @staticmethod
    def support_zone_brush(zone):
        color = QColor(
            PriceChart.COLOR_SUPPORT_VALIDATED
            if zone.get("validated")
            else PriceChart.COLOR_SUPPORT_NORMAL
        )
        color.setAlpha(70 if zone.get("validated") else 55)

        return QBrush(color)

    @staticmethod
    def support_zone_values(support_zones):
        values = []

        for zone in support_zones:
            for key in ["support_low", "support_high"]:
                value = zone.get(key)

                if value is not None:
                    values.append(float(value))

        return values

    @staticmethod
    def ohlc_values(prices):
        values = []

        for price in prices:
            for key in ["open", "high", "low", "close"]:
                value = price.get(key)

                if value is not None:
                    values.append(float(value))

        return values

    def add_support_labels(self, support_zones, start_x, end_x):
        self.clear_support_labels()

        if not self.series:
            return

        label_x = start_x + ((end_x - start_x) * 0.02)

        for zone in support_zones:
            high = zone.get("support_high")

            if high is None:
                continue

            label = QGraphicsSimpleTextItem(self.support_label_text(zone))
            label.setBrush(QBrush(QColor(self.COLOR_MUTED_TEXT)))
            label.setFont(QFont("Segoe UI", 8))
            label.setZValue(5)
            position = self.chart.mapToPosition(QPointF(label_x, float(high)))
            label.setPos(position)
            self.chart.scene().addItem(label)
            self.support_labels.append(label)

    @staticmethod
    def support_label_text(zone):
        if zone.get("validated"):
            successful_bounces = zone.get("successful_bounces")
            if successful_bounces is None:
                successful_bounces = zone.get("bounce_count")

            total_touches = zone.get("total_touches")
            success_rate = zone.get("bounce_success_rate")
            if success_rate is None:
                success_rate = zone.get("success_rate")

            parts = []

            if successful_bounces is not None and total_touches is not None:
                parts.append(
                    f"{int(successful_bounces)}/{int(total_touches)} bounces"
                )

            if success_rate is not None:
                parts.append(f"{float(success_rate):.0f}%")

            if parts:
                return f"Validated: {' - '.join(parts)}"

            return "Validated support"

        return "Support"

    @staticmethod
    def create_control_button(text, callback):
        button = QPushButton(text)
        button.setObjectName(f"PriceChart{text.replace(' ', '').replace('+', 'In').replace('-', 'Out')}")
        button.setFixedHeight(28)
        button.clicked.connect(callback)

        return button

    def reset_view(self):
        if self.chart is not None and hasattr(self.chart, "zoomReset"):
            self.chart.zoomReset()

    def zoom_in(self):
        if self.chart is not None and hasattr(self.chart, "zoom"):
            self.chart.zoom(1.2)

    def zoom_out(self):
        if self.chart is not None and hasattr(self.chart, "zoom"):
            self.chart.zoom(0.8)

    def pan_left(self):
        self.last_pan_direction = "left"
        self.scroll_chart(-40, 0)

    def pan_right(self):
        self.last_pan_direction = "right"
        self.scroll_chart(40, 0)

    def scroll_chart(self, dx, dy):
        return None

    def update_readout(self, prices):
        latest = prices[-1] if prices else None

        if not latest:
            self.readout_label.setText(self.READOUT_EMPTY_MESSAGE)
            return

        self.readout_label.setText(self.latest_readout_text(latest))

    @classmethod
    def latest_readout_text(cls, price):
        parts = [f"Latest: {price.get('date') or 'N/A'}"]

        for label, key in [
            ("O", "open"),
            ("H", "high"),
            ("L", "low"),
            ("C", "close"),
        ]:
            parts.append(f"{label} {cls.format_readout_value(price.get(key))}")

        if price.get("volume") is not None:
            parts.append(f"Vol {cls.format_readout_value(price.get('volume'))}")

        return " | ".join(parts)

    @staticmethod
    def format_readout_value(value):
        if value is None:
            return "N/A"

        if isinstance(value, float):
            return f"{value:.2f}"

        return str(value)

    @staticmethod
    def date_to_msecs(value, index):
        try:
            parsed = datetime.fromisoformat(str(value))
        except (TypeError, ValueError):
            parsed = datetime.fromtimestamp(index * 86400)

        return int(parsed.timestamp() * 1000)

    @staticmethod
    def apply_y_range(axis, values):
        low = min(values)
        high = max(values)

        if low == high:
            axis.setRange(low - 1.0, high + 1.0)
            return

        padding = (high - low) * 0.08
        axis.setRange(low - padding, high + padding)

    @staticmethod
    def placeholder_summary(chart_data):
        prices = chart_data.get("prices") or []
        latest_close = prices[-1].get("close") if prices else None

        return "\n".join(
            [
                str(chart_data.get("ticker") or ""),
                f"Latest close: {latest_close}",
                f"Price rows: {len(prices)}",
                PriceChart.BACKEND_UNAVAILABLE_MESSAGE,
            ]
        )

    @staticmethod
    def chart_title(chart_data):
        ticker = chart_data.get("ticker") or "Price"
        prices = chart_data.get("prices") or []
        latest_close = prices[-1].get("close") if prices else None

        if latest_close is None:
            return str(ticker)

        return f"{ticker} Close {float(latest_close):.2f}"

    @staticmethod
    def create_chart():
        chart = QChart()
        chart.legend().hide()
        chart.setBackgroundBrush(QColor(PriceChart.COLOR_BACKGROUND))
        chart.setPlotAreaBackgroundBrush(QColor(PriceChart.COLOR_PLOT_BACKGROUND))
        chart.setPlotAreaBackgroundVisible(True)
        chart.setTitleBrush(QColor(PriceChart.COLOR_TEXT))

        return chart

    def clear_chart(self):
        self.series = None
        self.candlestick_series = None
        self.render_mode = None
        self.overlay_series = {}
        self.support_band_series = []
        self.clear_support_labels()
        self.chart.removeAllSeries()

        for axis in self.chart.axes():
            self.chart.removeAxis(axis)

    def clear_support_labels(self):
        for label in self.support_labels:
            scene = label.scene()

            if scene is not None:
                scene.removeItem(label)

        self.support_labels = []
