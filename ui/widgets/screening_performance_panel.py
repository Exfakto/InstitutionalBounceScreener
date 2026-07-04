from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QFrame,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.design_system import DashboardDesignSystem as DesignSystem

try:
    from PySide6.QtCharts import QBarCategoryAxis, QBarSeries, QBarSet, QChart, QChartView, QValueAxis
except Exception:  # pragma: no cover
    QBarCategoryAxis = None
    QBarSeries = None
    QBarSet = None
    QChart = None
    QChartView = None
    QValueAxis = None


class ScreeningPerformancePanel(QWidget):
    HEADERS = ["Stage", "Seconds", "Previous", "Delta", "% Delta", "Comparison"]

    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.current_analytics = None
        self.setObjectName("ScreeningPerformancePanel")
        self._build_ui()
        self.set_analytics(None)

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

        title = QLabel("Screening Performance")
        title.setObjectName("ResearchPreviewSectionTitle")
        section_layout.addWidget(title)

        self.summary_label = QLabel("")
        self.summary_label.setObjectName("ResearchPreviewFieldValue")
        self.summary_label.setWordWrap(True)
        section_layout.addWidget(self.summary_label)

        self.message_label = QLabel("")
        self.message_label.setObjectName("EmptyStateLabel")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setWordWrap(True)
        section_layout.addWidget(self.message_label)

        self.chart = None
        self.chart_view = None
        self.chart_placeholder_label = None
        if QChart is not None and QChartView is not None:
            self.chart = QChart()
            self.chart.setTitle("Stage Timing")
            self.chart.legend().setVisible(False)
            self.chart_view = QChartView(self.chart)
            self.chart_view.setObjectName("ScreeningPerformanceChartView")
            self.chart_view.setRenderHint(QPainter.Antialiasing)
            section_layout.addWidget(self.chart_view)
        else:
            self.chart_placeholder_label = QLabel("Chart backend unavailable")
            self.chart_placeholder_label.setObjectName("ResearchPreviewFieldValue")
            self.chart_placeholder_label.setAlignment(Qt.AlignCenter)
            section_layout.addWidget(self.chart_placeholder_label)

        self.stage_table = QTableWidget(0, len(self.HEADERS))
        self.stage_table.setObjectName("ScreeningPerformanceTable")
        self.stage_table.setHorizontalHeaderLabels(self.HEADERS)
        self.stage_table.setAlternatingRowColors(True)
        self.stage_table.setSortingEnabled(False)
        self.stage_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.stage_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.stage_table.verticalHeader().setVisible(False)
        self.stage_table.setStyleSheet(DesignSystem.table_style())
        header = self.stage_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        section_layout.addWidget(self.stage_table)

    def refresh_analytics(self):
        if self.controller is None:
            self.set_analytics(None)
            return None
        try:
            analytics = self.controller.get_screening_performance_analytics()
        except Exception:
            self.set_error("Unable to load screening performance analytics")
            return None
        self.set_analytics(analytics)
        return analytics

    def set_analytics(self, analytics):
        self.current_analytics = analytics
        stages = list(self.value(analytics, "stages") or [])
        self.stage_table.setRowCount(0)
        self.message_label.setProperty("state", "empty")
        if not stages:
            self.summary_label.clear()
            self.message_label.setText("No screening performance metrics available")
            self.message_label.show()
            self.hide_chart()
            self.stage_table.hide()
            return

        slowest = self.value(analytics, "slowest_stage")
        slowest_name = self.value(slowest, "stage_name") or "N/A"
        self.summary_label.setText(
            "Total: "
            f"{self.display_value(self.value(analytics, 'total_screening_time_seconds'))}s | "
            "Avg/symbol: "
            f"{self.display_value(self.value(analytics, 'average_time_per_symbol_seconds'))}s | "
            f"Slowest: {slowest_name}"
        )
        self.message_label.clear()
        self.message_label.hide()
        self.render_chart(stages)
        self.stage_table.show()
        self.stage_table.setRowCount(len(stages))
        for row, stage in enumerate(stages):
            values = [
                self.value(stage, "stage_name"),
                self.value(stage, "duration_seconds"),
                self.value(stage, "previous_duration_seconds"),
                self.value(stage, "delta_seconds"),
                self.value(stage, "percent_delta"),
                self.value(stage, "classification"),
            ]
            for column, cell_value in enumerate(values):
                item = QTableWidgetItem(self.display_value(cell_value, percent=column == 4))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.stage_table.setItem(row, column, item)
        self.stage_table.resizeRowsToContents()

    def render_chart(self, stages):
        if self.chart is None:
            if self.chart_placeholder_label is not None:
                self.chart_placeholder_label.setText("Chart preview unavailable")
                self.chart_placeholder_label.show()
            return
        self.chart.removeAllSeries()
        for axis in list(self.chart.axes()):
            self.chart.removeAxis(axis)
        bar_set = QBarSet("Seconds")
        labels = []
        for stage in stages:
            bar_set.append(float(self.value(stage, "duration_seconds") or 0.0))
            labels.append(str(self.value(stage, "stage_name") or "Stage"))
        series = QBarSeries()
        series.append(bar_set)
        self.chart.addSeries(series)
        axis_x = QBarCategoryAxis()
        axis_x.append(labels)
        axis_y = QValueAxis()
        max_value = max([float(self.value(stage, "duration_seconds") or 0.0) for stage in stages] or [1.0])
        axis_y.setRange(0, max(1.0, max_value))
        axis_y.setTitleText("Seconds")
        self.chart.addAxis(axis_x, Qt.AlignBottom)
        self.chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_x)
        series.attachAxis(axis_y)
        self.chart_view.show()

    def set_error(self, message):
        self.current_analytics = None
        self.summary_label.clear()
        self.stage_table.setRowCount(0)
        self.stage_table.hide()
        self.hide_chart()
        self.message_label.setText(message or "Unable to load screening performance analytics")
        self.message_label.setProperty("state", "error")
        self.message_label.show()

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
    def display_value(raw, percent=False):
        if raw in (None, ""):
            return "N/A"
        if isinstance(raw, float):
            return f"{raw:.2f}%" if percent else f"{raw:.2f}"
        return str(raw)
