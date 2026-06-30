from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QDateTime, QPointF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QGraphicsSimpleTextItem, QLabel, QVBoxLayout, QWidget

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


class PriceChart(QWidget):
    """
    Reusable read-only price chart widget.
    """

    EMPTY_MESSAGE = "Select a candidate to view chart."
    NO_PRICE_MESSAGE = "No price history available."
    BACKEND_UNAVAILABLE_MESSAGE = "Chart rendering backend is unavailable."
    SERIES_DEFINITIONS = [
        ("close", "Close", "#4A90E2", 2),
        ("sma20", "SMA20", "#3FB950", 1),
        ("sma50", "SMA50", "#D29922", 1),
        ("sma200", "SMA200", "#F85149", 1),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)

        self.chart = None
        self.chart_view = None
        self.series = None
        self.overlay_series = {}
        self.support_band_series = []
        self.support_labels = []
        self.chart_data = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.summary_label = QLabel("")
        self.summary_label.setObjectName("PriceChartSummary")
        self.summary_label.setAlignment(Qt.AlignCenter)
        self.summary_label.setWordWrap(True)

        layout.addWidget(self.summary_label)

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

            if self.chart is not None:
                self.clear_chart()

            if self.chart_view is not None:
                self.chart_view.hide()

            return

        if not CHARTS_AVAILABLE:
            self.summary_label.setText(self.placeholder_summary(self.chart_data))
            self.summary_label.show()
            return

        points = self.series_points(prices, "close")

        if not points:
            self.summary_label.setText(self.NO_PRICE_MESSAGE)
            self.summary_label.show()
            self.chart_view.hide()
            return

        self.render_line_chart(self.chart_data, points)
        self.summary_label.hide()
        self.chart_view.show()

    def render_line_chart(self, chart_data, points):
        self.chart.removeAllSeries()
        for axis in self.chart.axes():
            self.chart.removeAxis(axis)

        self.overlay_series = {}
        prices = chart_data.get("prices") or []
        support_zones = chart_data.get("support_zones") or []
        chart_series = []

        support_band_series = self.create_support_band_series(
            support_zones,
            points[0][0],
            points[-1][0],
        )

        for support_band in support_band_series:
            chart_series.append(support_band)
            self.chart.addSeries(support_band)

        self.support_band_series = support_band_series

        for key, name, color, width in self.SERIES_DEFINITIONS:
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
        self.chart.legend().setLabelColor(QColor("#F2F2F2"))

        x_axis = QDateTimeAxis()
        x_axis.setFormat("MMM d")
        x_axis.setTitleText("Date")
        x_axis.setLabelsColor(QColor("#F2F2F2"))
        x_axis.setTitleBrush(QColor("#B0B0B0"))
        x_axis.setGridLineColor(QColor("#4A4A4A"))
        x_axis.setRange(
            QDateTime.fromMSecsSinceEpoch(points[0][0]),
            QDateTime.fromMSecsSinceEpoch(points[-1][0]),
        )

        y_axis = QValueAxis()
        y_axis.setTitleText("Close")
        y_axis.setLabelFormat("%.2f")
        y_axis.setLabelsColor(QColor("#F2F2F2"))
        y_axis.setTitleBrush(QColor("#B0B0B0"))
        y_axis.setGridLineColor(QColor("#4A4A4A"))
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
            line_values + self.support_zone_values(support_zones),
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
        color = QColor("#3FB950" if zone.get("validated") else "#8B949E")
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
            label.setBrush(QBrush(QColor("#B0B0B0")))
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
        chart.setBackgroundBrush(QColor("#1E1E1E"))
        chart.setPlotAreaBackgroundBrush(QColor("#2A2A2A"))
        chart.setPlotAreaBackgroundVisible(True)
        chart.setTitleBrush(QColor("#F2F2F2"))

        return chart

    def clear_chart(self):
        self.series = None
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
