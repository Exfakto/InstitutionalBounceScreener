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


class ScreeningDiagnosticsPanel(QWidget):
    STAGE_HEADERS = ["Stage", "Status", "Seconds", "Cache", "Warnings", "Errors"]
    MESSAGE_HEADERS = ["Severity", "Message", "Recommended Action"]

    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.current_diagnostics = None
        self.setObjectName("ScreeningDiagnosticsPanel")
        self._build_ui()
        self.set_diagnostics(None)

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

        title = QLabel("Screening Diagnostics")
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

        self.stage_table = self.create_table(self.STAGE_HEADERS, "ScreeningDiagnosticsStageTable")
        self.message_table = self.create_table(self.MESSAGE_HEADERS, "ScreeningDiagnosticsMessageTable")
        section_layout.addWidget(self.stage_table)
        section_layout.addWidget(self.message_table)

    def create_table(self, headers, object_name):
        table = QTableWidget(0, len(headers))
        table.setObjectName(object_name)
        table.setHorizontalHeaderLabels(headers)
        table.setAlternatingRowColors(True)
        table.setSortingEnabled(False)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.setStyleSheet(DesignSystem.table_style())
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        return table

    def refresh_diagnostics(self):
        if self.controller is None:
            self.set_diagnostics(None)
            return None
        try:
            diagnostics = self.controller.get_screening_diagnostics()
        except Exception:
            self.set_error("Unable to load screening diagnostics")
            return None
        self.set_diagnostics(diagnostics)
        return diagnostics

    def set_diagnostics(self, diagnostics):
        self.current_diagnostics = diagnostics
        stages = list(self.value(diagnostics, "stages") or [])
        messages = list(self.value(diagnostics, "messages") or [])
        self.stage_table.setRowCount(0)
        self.message_table.setRowCount(0)
        self.message_label.setProperty("state", "empty")
        if not stages and not messages:
            self.summary_label.clear()
            self.message_label.setText("No screening diagnostics available")
            self.message_label.show()
            self.stage_table.hide()
            self.message_table.hide()
            return

        self.summary_label.setText(
            f"Run: {self.display_value(self.value(diagnostics, 'run_id'))} | "
            f"Status: {self.display_value(self.value(diagnostics, 'overall_status'))} | "
            f"Symbols: {self.display_value(self.value(diagnostics, 'symbol_count'))} | "
            f"Warnings: {self.display_value(self.value(diagnostics, 'warning_count'))} | "
            f"Errors: {self.display_value(self.value(diagnostics, 'error_count'))}"
        )
        self.message_label.clear()
        self.message_label.hide()
        self.populate_stages(stages)
        self.populate_messages(messages)

    def populate_stages(self, stages):
        self.stage_table.show()
        self.stage_table.setRowCount(len(stages))
        for row, stage in enumerate(stages):
            values = [
                self.value(stage, "stage_name"),
                self.value(stage, "status"),
                self.value(stage, "timing_seconds"),
                self.value(stage, "cache_usage"),
                self.value(stage, "warning_count"),
                self.value(stage, "error_count"),
            ]
            self.set_row(self.stage_table, row, values)
        self.stage_table.resizeRowsToContents()

    def populate_messages(self, messages):
        self.message_table.show()
        self.message_table.setRowCount(len(messages))
        for row, message in enumerate(messages):
            values = [
                self.value(message, "severity"),
                self.value(message, "message"),
                self.value(message, "recommended_action"),
            ]
            self.set_row(self.message_table, row, values)
        self.message_table.resizeRowsToContents()

    def set_row(self, table, row, values):
        for column, cell_value in enumerate(values):
            item = QTableWidgetItem(self.display_value(cell_value))
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            table.setItem(row, column, item)

    def set_error(self, message):
        self.current_diagnostics = None
        self.summary_label.clear()
        self.stage_table.setRowCount(0)
        self.message_table.setRowCount(0)
        self.stage_table.hide()
        self.message_table.hide()
        self.message_label.setText(message or "Unable to load screening diagnostics")
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
        if isinstance(raw, float):
            return f"{raw:.2f}"
        return str(raw)
