from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.design_system import DashboardDesignSystem as DesignSystem

try:
    from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis
except Exception:  # pragma: no cover - depends on optional QtCharts backend
    QChart = None
    QChartView = None
    QLineSeries = None
    QValueAxis = None


class ModelCalibrationTrendPanel(QWidget):
    HEADERS = [
        "Timestamp",
        "Overall Score",
        "Precision",
        "Recall",
        "F1 Score",
        "Calibration Error",
        "Sample Size",
    ]

    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.current_trend = None
        self.setObjectName("ModelCalibrationTrendPanel")
        self._build_ui()
        self.set_trend(None)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            DesignSystem.Spacing.MD,
            DesignSystem.Spacing.MD,
            DesignSystem.Spacing.MD,
            DesignSystem.Spacing.MD,
        )
        layout.setSpacing(DesignSystem.Spacing.SM)

        section = QFrame()
        section.setObjectName("ResearchPreviewSection")
        section.setStyleSheet(DesignSystem.card_style())
        layout.addWidget(section)

        section_layout = QVBoxLayout(section)
        section_layout.setContentsMargins(
            DesignSystem.Spacing.MD,
            DesignSystem.Spacing.MD,
            DesignSystem.Spacing.MD,
            DesignSystem.Spacing.MD,
        )
        section_layout.setSpacing(DesignSystem.Spacing.SM)

        header = QHBoxLayout()
        title = QLabel("Calibration Trend")
        title.setObjectName("ResearchPreviewSectionTitle")
        self.window_combo = QComboBox()
        self.window_combo.setObjectName("CalibrationTrendWindowCombo")
        self.window_combo.addItems(["Last 10", "Last 25", "Last 50", "All"])
        self.window_combo.setCurrentText("Last 25")
        self.window_combo.currentTextChanged.connect(self.refresh_trend)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.window_combo)
        section_layout.addLayout(header)

        self.message_label = QLabel("")
        self.message_label.setObjectName("EmptyStateLabel")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setWordWrap(True)
        section_layout.addWidget(self.message_label)

        self.trend_table = QTableWidget(0, len(self.HEADERS))
        self.trend_table.setObjectName("CalibrationTrendTable")
        self.trend_table.setHorizontalHeaderLabels(self.HEADERS)
        self.trend_table.setAlternatingRowColors(True)
        self.trend_table.setSortingEnabled(False)
        self.trend_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.trend_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.trend_table.verticalHeader().setVisible(False)
        self.trend_table.setStyleSheet(DesignSystem.table_style())
        table_header = self.trend_table.horizontalHeader()
        table_header.setSectionResizeMode(QHeaderView.Interactive)
        table_header.setSectionResizeMode(0, QHeaderView.Stretch)
        self.chart = None
        self.chart_view = None
        self.chart_placeholder_label = None
        if QChart is not None and QChartView is not None:
            self.chart = QChart()
            self.chart.setTitle("Calibration Performance Trend")
            self.chart.legend().setVisible(True)
            self.chart_view = QChartView(self.chart)
            self.chart_view.setObjectName("CalibrationTrendChartView")
            self.chart_view.setRenderHint(QPainter.Antialiasing)
            section_layout.addWidget(self.chart_view)
        else:
            self.chart_placeholder_label = QLabel("Chart backend unavailable")
            self.chart_placeholder_label.setObjectName("ResearchPreviewFieldValue")
            self.chart_placeholder_label.setAlignment(Qt.AlignCenter)
            section_layout.addWidget(self.chart_placeholder_label)
        section_layout.addWidget(self.trend_table)

    def refresh_trend(self):
        if self.controller is None:
            self.set_trend(None)
            return None
        try:
            trend = self.controller.get_calibration_trend(self.window_combo.currentText())
        except Exception:
            self.set_error("Unable to load calibration trend")
            return None
        self.set_trend(trend)
        return trend

    def set_trend(self, trend):
        self.current_trend = trend
        points = list(self.value(trend, "points") or [])
        self.trend_table.setRowCount(0)
        self.message_label.setProperty("state", "empty")

        if self.value(trend, "insufficient_data") or len(points) < 2:
            self.message_label.setText("Insufficient historical data")
            self.message_label.show()
            self.hide_chart()
            self.trend_table.hide()
            return

        self.message_label.clear()
        self.message_label.hide()
        self.render_chart(points)
        self.trend_table.show()
        self.trend_table.setRowCount(len(points))
        for row, point in enumerate(points):
            values = [
                self.value(point, "timestamp"),
                self.value(point, "overall_score"),
                self.value(point, "precision"),
                self.value(point, "recall"),
                self.value(point, "f1_score"),
                self.value(point, "confidence_calibration_error"),
                self.value(point, "sample_size"),
            ]
            for column, cell_value in enumerate(values):
                item = QTableWidgetItem(self.display_value(cell_value))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.trend_table.setItem(row, column, item)
        self.trend_table.resizeRowsToContents()

    def set_error(self, message):
        self.current_trend = None
        self.trend_table.setRowCount(0)
        self.trend_table.hide()
        self.hide_chart()
        self.message_label.setText(message or "Unable to load calibration trend")
        self.message_label.setProperty("state", "error")
        self.message_label.show()

    def render_chart(self, points):
        if self.chart is None:
            if self.chart_placeholder_label is not None:
                self.chart_placeholder_label.setText("Chart preview unavailable")
                self.chart_placeholder_label.show()
            return

        self.chart.removeAllSeries()
        for axis in list(self.chart.axes()):
            self.chart.removeAxis(axis)
        metrics = [
            ("Overall Score", "overall_score"),
            ("Precision", "precision"),
            ("Recall", "recall"),
            ("F1 Score", "f1_score"),
            ("Calibration Error", "confidence_calibration_error"),
            ("Sample Size", "sample_size"),
        ]
        y_values = []
        for title, field in metrics:
            series = QLineSeries()
            series.setName(title)
            has_points = False
            for index, point in enumerate(points):
                number = self.numeric_value(self.value(point, field))
                if number is None:
                    continue
                series.append(float(index), number)
                y_values.append(number)
                has_points = True
            if has_points:
                self.chart.addSeries(series)

        if not self.chart.series():
            self.hide_chart()
            return

        axis_x = QValueAxis()
        axis_x.setRange(0, max(1, len(points) - 1))
        axis_x.setLabelFormat("%d")
        axis_x.setTitleText("Run")
        axis_y = QValueAxis()
        min_y = min(y_values) if y_values else 0.0
        max_y = max(y_values) if y_values else 1.0
        if min_y == max_y:
            max_y = min_y + 1.0
        axis_y.setRange(min_y, max_y)
        axis_y.setTitleText("Metric Value")
        self.chart.addAxis(axis_x, Qt.AlignBottom)
        self.chart.addAxis(axis_y, Qt.AlignLeft)
        for series in self.chart.series():
            series.attachAxis(axis_x)
            series.attachAxis(axis_y)
        self.chart_view.show()

    def hide_chart(self):
        if self.chart is not None:
            self.chart.removeAllSeries()
            for axis in list(self.chart.axes()):
                self.chart.removeAxis(axis)
        if self.chart_view is not None:
            self.chart_view.hide()
        if self.chart_placeholder_label is not None:
            self.chart_placeholder_label.hide()

    @staticmethod
    def value(source, key):
        if source is None:
            return None
        if isinstance(source, dict):
            return source.get(key)
        return getattr(source, key, None)

    @staticmethod
    def display_value(raw):
        if raw in (None, ""):
            return "N/A"
        return str(raw)

    @staticmethod
    def numeric_value(raw):
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None
