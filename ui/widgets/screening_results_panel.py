from PySide6.QtCore import Qt, Signal
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


class ScreeningResultsPanel(QWidget):
    refresh_ranked_candidates_requested = Signal()
    refresh_run_history_requested = Signal()

    RANKED_HEADERS = [
        "Rank",
        "Ticker",
        "Final Score",
        "Grade",
        "Confidence",
        "Setup",
        "Warnings",
        "Rejections",
    ]
    HISTORY_HEADERS = [
        "Run ID",
        "Status",
        "Started",
        "Completed",
        "Requested",
        "Processed",
        "Candidates",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ScreeningResultsPanel")
        self.build_ui()

    def build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            DesignSystem.Spacing.MD,
            DesignSystem.Spacing.MD,
            DesignSystem.Spacing.MD,
            DesignSystem.Spacing.MD,
        )
        layout.setSpacing(DesignSystem.Spacing.MD)

        ranked_section, self.ranked_candidates_table, self.ranked_empty_label = (
            self.build_table_section(
                "Ranked Candidates",
                "No ranked candidates available",
                self.RANKED_HEADERS,
                self.refresh_ranked_candidates_requested,
            )
        )
        history_section, self.run_history_table, self.run_history_empty_label = (
            self.build_table_section(
                "Run History",
                "No screening runs available",
                self.HISTORY_HEADERS,
                self.refresh_run_history_requested,
            )
        )

        layout.addWidget(ranked_section, stretch=3)
        layout.addWidget(history_section, stretch=2)

    def build_table_section(self, title, empty_text, headers, signal):
        section = QFrame()
        section.setObjectName("ResearchPreviewSection")
        section.setStyleSheet(DesignSystem.card_style())
        layout = QVBoxLayout(section)
        layout.setContentsMargins(
            DesignSystem.Spacing.MD,
            DesignSystem.Spacing.MD,
            DesignSystem.Spacing.MD,
            DesignSystem.Spacing.MD,
        )
        layout.setSpacing(DesignSystem.Spacing.SM)

        header = QHBoxLayout()
        label = QLabel(title)
        label.setObjectName("ResearchPreviewSectionTitle")
        refresh_button = QPushButton("Refresh")
        refresh_button.setObjectName("SecondaryButton")
        refresh_button.clicked.connect(signal.emit)
        header.addWidget(label)
        header.addStretch()
        header.addWidget(refresh_button)
        layout.addLayout(header)

        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setAlternatingRowColors(True)
        table.setSortingEnabled(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        table.setStyleSheet(DesignSystem.table_style())
        table.setMinimumHeight(160)
        layout.addWidget(table)

        empty_label = QLabel(empty_text)
        empty_label.setObjectName("EmptyStateLabel")
        empty_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(empty_label)

        return section, table, empty_label

    def populate_ranked_candidates(self, candidates):
        self.populate_table(
            self.ranked_candidates_table,
            [
                [
                    self.value(candidate, "rank"),
                    self.value(candidate, "ticker"),
                    self.value(candidate, "final_score"),
                    self.value(candidate, "grade"),
                    self.value(candidate, "confidence_level"),
                    self.value(candidate, "setup_label"),
                    len(self.value(candidate, "warnings") or []),
                    len(self.value(candidate, "rejection_reasons") or []),
                ]
                for candidate in (candidates or [])
            ],
            numeric_columns={0, 2, 6, 7},
        )
        self.set_empty_state(
            self.ranked_candidates_table,
            self.ranked_empty_label,
            not candidates,
        )

    def populate_run_history(self, runs):
        self.populate_table(
            self.run_history_table,
            [
                [
                    self.value(run, "run_id"),
                    self.value(run, "status"),
                    self.value(run, "started_at"),
                    self.value(run, "completed_at"),
                    self.value(run, "tickers_requested"),
                    self.value(run, "tickers_processed"),
                    self.value(run, "candidate_count"),
                ]
                for run in (runs or [])
            ],
            numeric_columns={4, 5, 6},
        )
        self.set_empty_state(
            self.run_history_table,
            self.run_history_empty_label,
            not runs,
        )

    @staticmethod
    def populate_table(table, rows, numeric_columns=None):
        numeric_columns = numeric_columns or set()
        table.setSortingEnabled(False)
        table.setRowCount(0)
        for row_index, row in enumerate(rows):
            table.insertRow(row_index)
            for column, value in enumerate(row):
                item = QTableWidgetItem(ScreeningResultsPanel.display_value(value))
                if column in numeric_columns:
                    number = ScreeningResultsPanel.number_value(value)
                    item.setData(Qt.UserRole, number)
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                else:
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                table.setItem(row_index, column, item)
        table.resizeColumnsToContents()
        table.setSortingEnabled(True)

    @staticmethod
    def set_empty_state(table, label, is_empty):
        label.setHidden(not is_empty)
        table.setHidden(is_empty)

    @staticmethod
    def display_value(value):
        if value in (None, ""):
            return "N/A"
        if isinstance(value, float):
            return f"{value:.2f}"
        return str(value)

    @staticmethod
    def number_value(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def value(source, key):
        if source is None:
            return None
        if isinstance(source, dict):
            return source.get(key)
        return getattr(source, key, None)
