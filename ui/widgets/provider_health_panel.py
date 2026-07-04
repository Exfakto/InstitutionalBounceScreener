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
from ui.widgets.provider_failover_history_panel import ProviderFailoverHistoryPanel


class ProviderHealthPanel(QWidget):
    HEADERS = [
        "Provider",
        "Status",
        "Successes",
        "Errors",
        "Avg Latency",
        "Last Failure",
    ]

    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.current_dashboard = None
        self.setObjectName("ProviderHealthPanel")
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
        self.title_label = QLabel("Provider Health")
        self.title_label.setObjectName("ResearchPreviewSectionTitle")
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setObjectName("SecondaryButton")
        self.refresh_button.clicked.connect(self.refresh_health)
        header.addWidget(self.title_label)
        header.addStretch(1)
        header.addWidget(self.refresh_button)
        section_layout.addLayout(header)

        self.summary_label = QLabel("")
        self.summary_label.setObjectName("ResearchPreviewFieldValue")
        self.summary_label.setWordWrap(True)
        section_layout.addWidget(self.summary_label)

        self.message_label = QLabel("")
        self.message_label.setObjectName("EmptyStateLabel")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setWordWrap(True)
        section_layout.addWidget(self.message_label)

        self.health_table = QTableWidget(0, len(self.HEADERS))
        self.health_table.setObjectName("ProviderHealthTable")
        self.health_table.setHorizontalHeaderLabels(self.HEADERS)
        self.health_table.setAlternatingRowColors(True)
        self.health_table.setSortingEnabled(False)
        self.health_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.health_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.health_table.verticalHeader().setVisible(False)
        self.health_table.setStyleSheet(DesignSystem.table_style())
        header = self.health_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        section_layout.addWidget(self.health_table)

        self.failover_history_panel = ProviderFailoverHistoryPanel(
            controller=self.controller
        )
        section_layout.addWidget(self.failover_history_panel)

    def refresh_health(self):
        if self.controller is None:
            self.set_dashboard(None)
            return None
        try:
            dashboard = self.controller.provider_health_dashboard()
        except Exception:
            self.set_error("Unable to load provider health")
            return None
        self.set_dashboard(dashboard)
        return dashboard

    def set_dashboard(self, dashboard):
        self.current_dashboard = dashboard
        providers = list(self.value(dashboard, "providers") or [])
        self.health_table.setRowCount(0)
        self.message_label.setProperty("state", "empty")
        if not providers:
            self.summary_label.clear()
            self.message_label.setText("No providers configured")
            self.message_label.show()
            self.health_table.hide()
            self.failover_history_panel.set_events(
                self.value(dashboard, "failover_events") or []
            )
            return

        self.summary_label.setText(
            f"Active: {self.display_value(self.value(dashboard, 'active_provider'))} | "
            f"Failover: {self.display_value(self.value(dashboard, 'failover_provider'))}"
        )
        self.message_label.clear()
        self.message_label.hide()
        self.health_table.show()
        self.failover_history_panel.set_events(
            self.value(dashboard, "failover_events") or []
        )
        self.health_table.setRowCount(len(providers))
        for row, provider in enumerate(providers):
            values = [
                self.value(provider, "provider_name"),
                self.value(provider, "status"),
                self.value(provider, "success_count"),
                self.value(provider, "error_count"),
                self.value(provider, "average_latency_seconds"),
                self.value(provider, "last_failure_reason"),
            ]
            for column, cell_value in enumerate(values):
                item = QTableWidgetItem(self.display_value(cell_value))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if column == 1:
                    item.setData(Qt.UserRole, self.display_value(cell_value))
                    item.setToolTip(f"Provider is {self.display_value(cell_value)}")
                self.health_table.setItem(row, column, item)
        self.health_table.resizeRowsToContents()

    def set_error(self, message):
        self.current_dashboard = None
        self.summary_label.clear()
        self.health_table.setRowCount(0)
        self.health_table.hide()
        self.message_label.setText(message or "Unable to load provider health")
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
            return f"{raw:.4f}"
        return str(raw)
