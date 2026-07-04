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


class ProductionReadinessPanel(QWidget):
    HEADERS = ["Subsystem", "Status", "Last Check", "Summary", "Recommended Action"]

    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.current_dashboard = None
        self.setObjectName("ProductionReadinessPanel")
        self._build_ui()
        self.set_dashboard(None)

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
        section.setObjectName("ProductionReadinessSection")
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
        self.title_label = QLabel("Production Readiness")
        self.title_label.setObjectName("ResearchPreviewSectionTitle")
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setObjectName("SecondaryButton")
        self.refresh_button.clicked.connect(self.refresh_dashboard)
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

        self.subsystem_table = QTableWidget(0, len(self.HEADERS))
        self.subsystem_table.setObjectName("ProductionReadinessSubsystemTable")
        self.subsystem_table.setHorizontalHeaderLabels(self.HEADERS)
        self.subsystem_table.setAlternatingRowColors(True)
        self.subsystem_table.setSortingEnabled(False)
        self.subsystem_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.subsystem_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.subsystem_table.verticalHeader().setVisible(False)
        self.subsystem_table.setStyleSheet(DesignSystem.table_style())
        table_header = self.subsystem_table.horizontalHeader()
        table_header.setSectionResizeMode(QHeaderView.Interactive)
        table_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        table_header.setSectionResizeMode(3, QHeaderView.Stretch)
        table_header.setSectionResizeMode(4, QHeaderView.Stretch)
        section_layout.addWidget(self.subsystem_table)

    def refresh_dashboard(self):
        if self.controller is None:
            self.set_dashboard(None)
            return None
        try:
            dashboard = self.controller.get_production_readiness_dashboard()
        except Exception:
            self.set_error("Unable to load production readiness dashboard")
            return None
        self.set_dashboard(dashboard)
        return dashboard

    def set_dashboard(self, dashboard):
        self.current_dashboard = dashboard
        subsystems = list(self.value(dashboard, "subsystems") or [])
        self.subsystem_table.setRowCount(0)
        self.message_label.setProperty("state", "empty")
        if dashboard is None:
            self.status_label.setText("Overall Status: N/A")
            self.message_label.setText("Refresh to check production readiness")
            self.message_label.show()
            self.subsystem_table.hide()
            return

        self.status_label.setText(
            f"Overall Status: {self.display_value(self.value(dashboard, 'overall_status'))} | "
            f"Generated: {self.display_value(self.value(dashboard, 'generated_at'))}"
        )
        self.status_label.setProperty(
            "status",
            str(self.value(dashboard, "overall_status") or "").lower(),
        )
        if not subsystems:
            self.message_label.setText("No production readiness checks available")
            self.message_label.show()
            self.subsystem_table.hide()
            return

        self.message_label.clear()
        self.message_label.hide()
        self.subsystem_table.show()
        self.subsystem_table.setRowCount(len(subsystems))
        for row, subsystem in enumerate(subsystems):
            values = [
                self.value(subsystem, "name"),
                self.value(subsystem, "status"),
                self.value(subsystem, "last_check_time"),
                self.value(subsystem, "summary"),
                self.value(subsystem, "recommended_action"),
            ]
            for column, cell_value in enumerate(values):
                item = QTableWidgetItem(self.display_value(cell_value))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.subsystem_table.setItem(row, column, item)
        self.subsystem_table.resizeRowsToContents()

    def set_error(self, message):
        self.current_dashboard = None
        self.status_label.setText("Overall Status: Not Ready")
        self.status_label.setProperty("status", "not ready")
        self.subsystem_table.setRowCount(0)
        self.subsystem_table.hide()
        self.message_label.setText(message or "Unable to load production readiness dashboard")
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
