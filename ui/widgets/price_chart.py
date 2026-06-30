from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QDateTime, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

try:
    from PySide6.QtCharts import (
        QChart,
        QChartView,
        QDateTimeAxis,
        QLineSeries,
        QValueAxis,
    )

    CHARTS_AVAILABLE = True
except ImportError:
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

    def __init__(self, parent=None):
        super().__init__(parent)

        self.chart = None
        self.chart_view = None
        self.series = None
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

        points = self.price_points(prices)

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

        self.series = QLineSeries()
        self.series.setName("Close")
        self.series.setPen(QPen(QColor("#4A90E2"), 2))

        for x_value, close in points:
            self.series.append(x_value, close)

        self.chart.addSeries(self.series)
        self.chart.setTitle(self.chart_title(chart_data))

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
        self.apply_y_range(y_axis, [close for _, close in points])

        self.chart.addAxis(x_axis, Qt.AlignBottom)
        self.chart.addAxis(y_axis, Qt.AlignLeft)
        self.series.attachAxis(x_axis)
        self.series.attachAxis(y_axis)

    @classmethod
    def price_points(cls, prices):
        points = []

        for index, price in enumerate(prices):
            close = price.get("close")

            if close is None:
                continue

            points.append(
                (
                    cls.date_to_msecs(price.get("date"), index),
                    float(close),
                )
            )

        return points

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
        self.chart.removeAllSeries()

        for axis in self.chart.axes():
            self.chart.removeAxis(axis)
