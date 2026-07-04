from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.design_system import DashboardDesignSystem as DesignSystem


class FullUniverseValidationPanel(QWidget):
    HEADERS = ["Category", "Ticker", "Severity", "Message"]

    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.current_result = None
        self.setObjectName("FullUniverseValidationPanel")
        self._build_ui()
        self.set_result(None)

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

        self.title_label = QLabel("Full Universe Validation")
        self.title_label.setObjectName("ResearchPreviewSectionTitle")
        section_layout.addWidget(self.title_label)

        self.run_button = QPushButton("Run Validation")
        self.run_button.setObjectName("PrimaryButton")
        self.run_button.clicked.connect(self.run_validation)
        section_layout.addWidget(self.run_button)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        section_layout.addWidget(self.progress_bar)

        self.summary_label = QLabel("")
        self.summary_label.setObjectName("ResearchPreviewFieldValue")
        self.summary_label.setWordWrap(True)
        section_layout.addWidget(self.summary_label)

        self.message_label = QLabel("")
        self.message_label.setObjectName("EmptyStateLabel")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setWordWrap(True)
        section_layout.addWidget(self.message_label)

        self.issue_table = QTableWidget(0, len(self.HEADERS))
        self.issue_table.setObjectName("FullUniverseValidationIssueTable")
        self.issue_table.setHorizontalHeaderLabels(self.HEADERS)
        self.issue_table.setAlternatingRowColors(True)
        self.issue_table.setSortingEnabled(False)
        self.issue_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.issue_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.issue_table.verticalHeader().setVisible(False)
        self.issue_table.setStyleSheet(DesignSystem.table_style())
        header = self.issue_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        section_layout.addWidget(self.issue_table)

    def run_validation(self):
        if self.controller is None:
            self.set_error("Unable to run full universe validation")
            return None
        try:
            result = self.controller.validate_full_universe(
                progress_callback=self.update_progress
            )
        except Exception:
            self.set_error("Unable to run full universe validation")
            return None
        self.set_result(result)
        return result

    def update_progress(self, progress):
        rate = int(float(self.value(progress, "completion_rate") or 0))
        self.progress_bar.setValue(max(0, min(100, rate)))
        self.message_label.setText(str(self.value(progress, "status_message") or ""))
        self.message_label.show()

    def set_result(self, result):
        self.current_result = result
        self.issue_table.setRowCount(0)
        issues = list(self.value(result, "issues") or [])
        if result is None:
            self.summary_label.clear()
            self.message_label.setText("No full universe validation has been run")
            self.message_label.show()
            self.issue_table.hide()
            self.progress_bar.setValue(0)
            return

        self.progress_bar.setValue(int(float(self.value(result, "completion_rate") or 0)))
        self.summary_label.setText(
            f"Status: {self.display_value(self.value(result, 'status'))} | "
            f"Total: {self.display_value(self.value(result, 'total_symbols'))} | "
            f"Processed: {self.display_value(self.value(result, 'processed_symbols'))} | "
            f"Skipped: {self.display_value(self.value(result, 'skipped_symbols'))} | "
            f"Failed: {self.display_value(self.value(result, 'failed_symbols'))} | "
            f"Completion: {self.display_value(self.value(result, 'completion_rate'))}%"
        )
        if not issues:
            self.message_label.setText("No validation issues detected")
            self.message_label.show()
            self.issue_table.hide()
            return

        self.message_label.clear()
        self.message_label.hide()
        self.issue_table.show()
        self.issue_table.setRowCount(len(issues))
        for row, issue in enumerate(issues):
            values = [
                self.value(issue, "category"),
                self.value(issue, "ticker"),
                self.value(issue, "severity"),
                self.value(issue, "message"),
            ]
            for column, cell_value in enumerate(values):
                item = QTableWidgetItem(self.display_value(cell_value))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.issue_table.setItem(row, column, item)
        self.issue_table.resizeRowsToContents()

    def set_error(self, message):
        self.current_result = None
        self.issue_table.setRowCount(0)
        self.issue_table.hide()
        self.summary_label.clear()
        self.message_label.setText(message or "Unable to run full universe validation")
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
