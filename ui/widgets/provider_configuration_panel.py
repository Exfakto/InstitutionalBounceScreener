from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.design_system import DashboardDesignSystem as DesignSystem


class ProviderConfigurationPanel(QWidget):
    HEADERS = ["Status", "Message", "Setting", "Recommended Fix"]

    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.current_result = None
        self.setObjectName("ProviderConfigurationPanel")
        self._build_ui()
        self.set_validation_result(None)

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
        section.setObjectName("ProviderConfigurationSection")
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
        self.title_label = QLabel("Provider Configuration Validation")
        self.title_label.setObjectName("ResearchPreviewSectionTitle")
        self.refresh_button = QPushButton("Validate")
        self.refresh_button.setObjectName("SecondaryButton")
        self.refresh_button.clicked.connect(self.refresh_validation)
        header.addWidget(self.title_label)
        header.addStretch(1)
        header.addWidget(self.refresh_button)
        section_layout.addLayout(header)

        self.status_label = QLabel("")
        self.status_label.setObjectName("ResearchPreviewFieldValue")
        self.status_label.setWordWrap(True)
        section_layout.addWidget(self.status_label)

        self.message_label = QLabel("")
        self.message_label.setObjectName("EmptyStateLabel")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setWordWrap(True)
        section_layout.addWidget(self.message_label)

        self.validation_table = QTableWidget(0, len(self.HEADERS))
        self.validation_table.setObjectName("ProviderConfigurationValidationTable")
        self.validation_table.setHorizontalHeaderLabels(self.HEADERS)
        self.validation_table.setAlternatingRowColors(True)
        self.validation_table.setSortingEnabled(False)
        self.validation_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.validation_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.validation_table.verticalHeader().setVisible(False)
        self.validation_table.setStyleSheet(DesignSystem.table_style())
        table_header = self.validation_table.horizontalHeader()
        table_header.setSectionResizeMode(QHeaderView.Interactive)
        table_header.setSectionResizeMode(1, QHeaderView.Stretch)
        table_header.setSectionResizeMode(3, QHeaderView.Stretch)
        section_layout.addWidget(self.validation_table)

    def refresh_validation(self):
        if self.controller is None:
            self.set_validation_result(None)
            return None
        try:
            result = self.controller.validate_provider_configuration()
        except Exception:
            self.set_error("Unable to validate provider configuration")
            return None
        self.set_validation_result(result)
        return result

    def set_validation_result(self, result):
        self.current_result = result
        self.validation_table.setRowCount(0)
        self.message_label.setProperty("state", "empty")

        if result is None:
            self.status_label.setText("Status: N/A")
            self.message_label.setText("Run validation to check provider configuration")
            self.message_label.show()
            self.validation_table.hide()
            return

        status = self.value(result, "status") or "N/A"
        issues = list(self.value(result, "issues") or [])
        self.status_label.setText(f"Status: {status}")
        self.status_label.setProperty("status", str(status).lower())

        if not issues:
            self.message_label.setText("Provider configuration passed validation")
            self.message_label.show()
            self.validation_table.hide()
            return

        self.message_label.clear()
        self.message_label.hide()
        self.validation_table.show()
        self.validation_table.setRowCount(len(issues))
        for row, issue in enumerate(issues):
            values = [
                self.value(issue, "status"),
                self.value(issue, "message"),
                self.value(issue, "affected_setting"),
                self.value(issue, "recommended_fix"),
            ]
            for column, cell_value in enumerate(values):
                item = QTableWidgetItem(self.display_value(cell_value))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.validation_table.setItem(row, column, item)
        self.validation_table.resizeRowsToContents()

    def set_error(self, message):
        self.current_result = None
        self.status_label.setText("Status: Failed")
        self.status_label.setProperty("status", "failed")
        self.validation_table.setRowCount(0)
        self.validation_table.hide()
        self.message_label.setText(message or "Unable to validate provider configuration")
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
