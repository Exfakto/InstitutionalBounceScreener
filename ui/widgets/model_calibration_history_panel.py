from __future__ import annotations

from PySide6.QtCore import Qt
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


class ModelCalibrationHistoryPanel(QWidget):
    HEADERS = ["Timestamp", "Model Version", "Sample Size", "Overall Score", "Status"]

    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.history_items = []
        self.selected_run = None
        self.setObjectName("ModelCalibrationHistoryPanel")
        self._build_ui()
        self.set_history([])

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

        title = QLabel("Calibration History")
        title.setObjectName("ResearchPreviewSectionTitle")
        section_layout.addWidget(title)

        self.message_label = QLabel("")
        self.message_label.setObjectName("EmptyStateLabel")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setWordWrap(True)
        section_layout.addWidget(self.message_label)

        self.history_table = QTableWidget(0, len(self.HEADERS))
        self.history_table.setObjectName("CalibrationHistoryTable")
        self.history_table.setHorizontalHeaderLabels(self.HEADERS)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setSortingEnabled(False)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setStyleSheet(DesignSystem.table_style())
        self.history_table.itemSelectionChanged.connect(self.handle_selection_changed)
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        section_layout.addWidget(self.history_table)

        self.details_label = QLabel("Select a calibration run to view details.")
        self.details_label.setObjectName("ResearchPreviewFieldValue")
        self.details_label.setWordWrap(True)
        section_layout.addWidget(self.details_label)

    def refresh_history(self):
        if self.controller is None:
            self.set_history([])
            return []
        try:
            history = self.controller.get_calibration_history()
        except Exception:
            self.set_error("Unable to load calibration history")
            return []
        self.set_history(history)
        return history

    def set_history(self, history):
        self.history_items = list(history or [])
        self.selected_run = None
        self.history_table.setRowCount(0)
        self.details_label.setText("Select a calibration run to view details.")
        self.message_label.setProperty("state", "empty")

        if not self.history_items:
            self.message_label.setText("No calibration history available")
            self.message_label.show()
            self.history_table.hide()
            return

        self.message_label.clear()
        self.message_label.hide()
        self.history_table.show()
        self.history_table.setRowCount(len(self.history_items))
        for row, item in enumerate(self.history_items):
            values = [
                self.value(item, "timestamp"),
                self.value(item, "model_version"),
                self.value(item, "sample_size"),
                self.value(item, "overall_score"),
                self.value(item, "status"),
            ]
            for column, cell_value in enumerate(values):
                table_item = QTableWidgetItem(self.display_value(cell_value))
                table_item.setFlags(table_item.flags() & ~Qt.ItemIsEditable)
                if column == 0:
                    table_item.setData(Qt.UserRole, self.value(item, "run_id"))
                self.history_table.setItem(row, column, table_item)
        self.history_table.resizeRowsToContents()

    def handle_selection_changed(self):
        row = self.history_table.currentRow()
        if row < 0 or row >= len(self.history_items):
            self.selected_run = None
            self.details_label.setText("Select a calibration run to view details.")
            return
        run_id = self.value(self.history_items[row], "run_id")
        details = self.history_items[row]
        if self.controller is not None and hasattr(
            self.controller, "get_calibration_run_details"
        ):
            try:
                details = self.controller.get_calibration_run_details(run_id) or details
            except Exception:
                details = self.history_items[row]
        self.set_selected_run(details)

    def set_selected_run(self, run):
        self.selected_run = run
        warnings = self.value(run, "warnings") or []
        errors = self.value(run, "errors") or []
        detail_parts = [
            f"Run: {self.display_value(self.value(run, 'run_id'))}",
            f"Status: {self.display_value(self.value(run, 'status'))}",
            f"Summary: {self.display_value(self.value(run, 'summary'))}",
        ]
        if warnings:
            detail_parts.append(f"Warnings: {'; '.join(str(item) for item in warnings)}")
        if errors:
            detail_parts.append(f"Errors: {'; '.join(str(item) for item in errors)}")
        self.details_label.setText("\n".join(detail_parts))

    def set_error(self, message):
        self.history_items = []
        self.selected_run = None
        self.history_table.setRowCount(0)
        self.history_table.hide()
        self.message_label.setText(message or "Unable to load calibration history")
        self.message_label.setProperty("state", "error")
        self.message_label.show()
        self.details_label.setText("Select a calibration run to view details.")

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
