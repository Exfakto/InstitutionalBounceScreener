from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.design_system import DashboardDesignSystem as DesignSystem


class ModelCalibrationComparisonPanel(QWidget):
    HEADERS = [
        "Metric",
        "Base Run",
        "Comparison Run",
        "Delta",
        "% Delta",
        "Classification",
    ]

    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.current_comparison = None
        self.setObjectName("ModelCalibrationComparisonPanel")
        self._build_ui()
        self.set_comparison(None)

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
        title = QLabel("Calibration Version Comparison")
        title.setObjectName("ResearchPreviewSectionTitle")
        self.base_run_input = QLineEdit()
        self.base_run_input.setObjectName("CalibrationBaseRunInput")
        self.base_run_input.setPlaceholderText("Base run ID")
        self.comparison_run_input = QLineEdit()
        self.comparison_run_input.setObjectName("CalibrationComparisonRunInput")
        self.comparison_run_input.setPlaceholderText("Comparison run ID")
        self.compare_button = QPushButton("Compare")
        self.compare_button.setObjectName("SecondaryButton")
        self.compare_button.clicked.connect(self.compare_selected_runs)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.base_run_input)
        header.addWidget(self.comparison_run_input)
        header.addWidget(self.compare_button)
        section_layout.addLayout(header)

        self.message_label = QLabel("")
        self.message_label.setObjectName("EmptyStateLabel")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setWordWrap(True)
        section_layout.addWidget(self.message_label)

        self.comparison_table = QTableWidget(0, len(self.HEADERS))
        self.comparison_table.setObjectName("CalibrationComparisonTable")
        self.comparison_table.setHorizontalHeaderLabels(self.HEADERS)
        self.comparison_table.setAlternatingRowColors(True)
        self.comparison_table.setSortingEnabled(False)
        self.comparison_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.comparison_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.comparison_table.verticalHeader().setVisible(False)
        self.comparison_table.setStyleSheet(DesignSystem.table_style())
        table_header = self.comparison_table.horizontalHeader()
        table_header.setSectionResizeMode(QHeaderView.Interactive)
        table_header.setSectionResizeMode(0, QHeaderView.Stretch)
        section_layout.addWidget(self.comparison_table)

    def compare_selected_runs(self):
        if self.controller is None:
            self.set_comparison(None)
            return None
        try:
            comparison = self.controller.compare_calibration_runs(
                self.base_run_input.text().strip(),
                self.comparison_run_input.text().strip(),
            )
        except Exception:
            self.set_error("Unable to compare calibration runs")
            return None
        self.set_comparison(comparison)
        return comparison

    def set_comparison(self, comparison):
        self.current_comparison = comparison
        self.comparison_table.setRowCount(0)
        self.message_label.setProperty("state", "empty")
        metrics = list(self.value(comparison, "metrics") or [])

        if comparison is None:
            self.message_label.setText("Select two calibration runs to compare")
            self.message_label.show()
            self.comparison_table.hide()
            return
        if self.value(comparison, "missing_run"):
            warnings = self.value(comparison, "warnings") or []
            self.message_label.setText(
                "; ".join(str(item) for item in warnings)
                or "Unable to load one or more calibration runs"
            )
            self.message_label.show()
            self.comparison_table.hide()
            return
        if not metrics:
            self.message_label.setText("No comparison metrics available")
            self.message_label.show()
            self.comparison_table.hide()
            return

        self.message_label.clear()
        self.message_label.hide()
        self.comparison_table.show()
        self.comparison_table.setRowCount(len(metrics))
        for row, metric in enumerate(metrics):
            values = [
                self.value(metric, "label"),
                self.value(metric, "base_value"),
                self.value(metric, "comparison_value"),
                self.value(metric, "delta"),
                self.value(metric, "percent_delta"),
                self.value(metric, "classification"),
            ]
            for column, cell_value in enumerate(values):
                item = QTableWidgetItem(self.display_value(cell_value, percent=column == 4))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.comparison_table.setItem(row, column, item)
        self.comparison_table.resizeRowsToContents()

    def set_error(self, message):
        self.current_comparison = None
        self.comparison_table.setRowCount(0)
        self.comparison_table.hide()
        self.message_label.setText(message or "Unable to compare calibration runs")
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
    def display_value(raw, percent=False):
        if raw in (None, ""):
            return "N/A"
        if isinstance(raw, float):
            return f"{raw:.2f}%" if percent else f"{raw:.2f}"
        return str(raw)
