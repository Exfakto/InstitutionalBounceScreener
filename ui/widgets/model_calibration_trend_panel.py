from __future__ import annotations

from PySide6.QtCore import Qt
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
            self.trend_table.hide()
            return

        self.message_label.clear()
        self.message_label.hide()
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
        self.message_label.setText(message or "Unable to load calibration trend")
        self.message_label.setProperty("state", "error")
        self.message_label.show()

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
