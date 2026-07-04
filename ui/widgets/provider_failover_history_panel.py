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


class ProviderFailoverHistoryPanel(QWidget):
    HEADERS = [
        "Timestamp",
        "Previous Provider",
        "New Provider",
        "Reason",
        "Errors",
        "Latency",
    ]

    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.current_events = []
        self.setObjectName("ProviderFailoverHistoryPanel")
        self._build_ui()
        self.set_events([])

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, DesignSystem.Spacing.SM, 0, 0)
        layout.setSpacing(DesignSystem.Spacing.SM)

        section = QFrame()
        section.setObjectName("ProviderFailoverHistorySection")
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
        self.title_label = QLabel("Provider Failover History")
        self.title_label.setObjectName("ResearchPreviewSectionTitle")
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setObjectName("SecondaryButton")
        self.refresh_button.clicked.connect(self.refresh_history)
        header.addWidget(self.title_label)
        header.addStretch(1)
        header.addWidget(self.refresh_button)
        section_layout.addLayout(header)

        self.message_label = QLabel("")
        self.message_label.setObjectName("EmptyStateLabel")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setWordWrap(True)
        section_layout.addWidget(self.message_label)

        self.history_table = QTableWidget(0, len(self.HEADERS))
        self.history_table.setObjectName("ProviderFailoverHistoryTable")
        self.history_table.setHorizontalHeaderLabels(self.HEADERS)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setSortingEnabled(False)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setStyleSheet(DesignSystem.table_style())
        table_header = self.history_table.horizontalHeader()
        table_header.setSectionResizeMode(QHeaderView.Interactive)
        table_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        table_header.setSectionResizeMode(3, QHeaderView.Stretch)
        section_layout.addWidget(self.history_table)

    def refresh_history(self):
        if self.controller is None:
            self.set_events([])
            return []
        try:
            events = self.controller.provider_failover_history()
        except Exception:
            self.set_error("Unable to load provider failover history")
            return None
        self.set_events(events)
        return events

    def set_events(self, events):
        self.current_events = self.sorted_events(events)
        self.history_table.setRowCount(0)
        self.message_label.setProperty("state", "empty")
        if not self.current_events:
            self.message_label.setText("No provider failover events recorded")
            self.message_label.show()
            self.history_table.hide()
            return

        self.message_label.clear()
        self.message_label.hide()
        self.history_table.show()
        self.history_table.setRowCount(len(self.current_events))
        for row, event in enumerate(self.current_events):
            values = [
                self.value(event, "timestamp"),
                self.value(event, "previous_provider"),
                self.value(event, "new_provider"),
                self.value(event, "reason"),
                self.value(event, "error_count"),
                self.value(event, "latency_seconds"),
            ]
            for column, cell_value in enumerate(values):
                item = QTableWidgetItem(self.display_value(cell_value))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.history_table.setItem(row, column, item)
        self.history_table.resizeRowsToContents()

    def set_error(self, message):
        self.current_events = []
        self.history_table.setRowCount(0)
        self.history_table.hide()
        self.message_label.setText(message or "Unable to load provider failover history")
        self.message_label.setProperty("state", "error")
        self.message_label.show()

    @classmethod
    def sorted_events(cls, events):
        return sorted(
            list(events or []),
            key=lambda event: cls.display_value(cls.value(event, "timestamp")),
            reverse=True,
        )

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
