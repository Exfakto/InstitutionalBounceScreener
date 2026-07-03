from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QComboBox,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.design_system import DashboardDesignSystem as DesignSystem


class ScreeningResultsPanel(QWidget):
    SOURCE_ROLE = Qt.UserRole + 1
    refresh_ranked_candidates_requested = Signal()
    refresh_run_history_requested = Signal()
    run_screening_requested = Signal(str)
    cancel_screening_requested = Signal()
    screening_mode_changed = Signal(str)
    run_selected = Signal(str)
    candidate_selected = Signal(object)

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
        self.current_candidates = []
        self.current_runs = []
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

        layout.addWidget(self.build_screening_controls())

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
        layout.addWidget(self.build_run_detail_section(), stretch=1)
        layout.addWidget(self.build_candidate_detail_section(), stretch=2)

        self.ranked_candidates_table.itemSelectionChanged.connect(
            self.handle_candidate_selection
        )
        self.run_history_table.itemSelectionChanged.connect(
            self.handle_run_selection
        )

    def build_screening_controls(self):
        section = QFrame()
        section.setObjectName("ResearchPreviewSection")
        section.setStyleSheet(DesignSystem.card_style())
        layout = QHBoxLayout(section)
        layout.setContentsMargins(
            DesignSystem.Spacing.MD,
            DesignSystem.Spacing.SM,
            DesignSystem.Spacing.MD,
            DesignSystem.Spacing.SM,
        )
        layout.setSpacing(DesignSystem.Spacing.SM)

        label = QLabel("Tickers")
        label.setObjectName("ResearchPreviewFieldLabel")
        self.screening_mode_combo = QComboBox()
        self.screening_mode_combo.setObjectName("ScreeningModeCombo")
        self.screening_mode_combo.addItems(["Manual ticker input", "Universe scan mode"])
        self.screening_mode_combo.currentTextChanged.connect(self.handle_mode_changed)
        self.ticker_input = QLineEdit()
        self.ticker_input.setObjectName("ScreeningTickerInput")
        self.ticker_input.setPlaceholderText("AAPL, MSFT, NVDA")
        self.run_screening_button = QPushButton("Run Screening")
        self.run_screening_button.setObjectName("PrimaryButton")
        self.run_screening_button.clicked.connect(self.emit_run_screening)
        self.cancel_screening_button = QPushButton("Cancel Screening")
        self.cancel_screening_button.setObjectName("SecondaryButton")
        self.cancel_screening_button.setEnabled(False)
        self.cancel_screening_button.clicked.connect(self.cancel_screening_requested.emit)
        self.screening_status_label = QLabel("Ready")
        self.screening_status_label.setObjectName("ResearchPreviewFieldValue")
        self.universe_count_label = QLabel("Universe: --")
        self.universe_count_label.setObjectName("ResearchPreviewFieldValue")

        layout.addWidget(self.screening_mode_combo)
        layout.addWidget(label)
        layout.addWidget(self.ticker_input, stretch=1)
        layout.addWidget(self.run_screening_button)
        layout.addWidget(self.cancel_screening_button)
        layout.addWidget(self.universe_count_label)
        layout.addWidget(self.screening_status_label)
        return section

    def emit_run_screening(self):
        self.run_screening_requested.emit(self.ticker_input.text())

    def handle_mode_changed(self, mode):
        self.ticker_input.setEnabled(not self.is_universe_scan_mode())
        self.screening_mode_changed.emit(mode)

    def is_universe_scan_mode(self):
        return self.screening_mode_combo.currentText() == "Universe scan mode"

    def set_universe_count(self, count):
        self.universe_count_label.setText(f"Universe: {count}")

    def set_screening_active(self, active, status_text=None):
        self.run_screening_button.setEnabled(not active)
        self.cancel_screening_button.setEnabled(active)
        if status_text is not None:
            self.screening_status_label.setText(status_text)

    def set_screening_status(self, status_text):
        self.screening_status_label.setText(status_text)

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

    def build_run_detail_section(self):
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

        title = QLabel("Run Detail")
        title.setObjectName("ResearchPreviewSectionTitle")
        layout.addWidget(title)

        self.run_detail_empty_label = QLabel("No selected run")
        self.run_detail_empty_label.setObjectName("EmptyStateLabel")
        self.run_detail_empty_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.run_detail_empty_label)

        self.run_detail_content = QWidget()
        grid = QGridLayout(self.run_detail_content)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(DesignSystem.Spacing.LG)
        grid.setVerticalSpacing(DesignSystem.Spacing.XS)
        self.run_detail_labels = {}
        for index, (key, title_text) in enumerate(
            [
                ("run_id", "Run ID"),
                ("status", "Status"),
                ("started_at", "Started"),
                ("completed_at", "Completed"),
                ("tickers_requested", "Requested"),
                ("tickers_processed", "Processed"),
                ("candidate_count", "Candidates"),
                ("warnings", "Warnings"),
                ("errors", "Errors"),
            ]
        ):
            row = index // 3
            col = (index % 3) * 2
            label = QLabel(title_text)
            label.setObjectName("ResearchPreviewFieldLabel")
            value = QLabel("N/A")
            value.setObjectName("ResearchPreviewFieldValue")
            value.setTextInteractionFlags(Qt.TextSelectableByMouse)
            grid.addWidget(label, row, col)
            grid.addWidget(value, row, col + 1)
            self.run_detail_labels[key] = value
        layout.addWidget(self.run_detail_content)
        self.run_detail_content.hide()
        return section

    def build_candidate_detail_section(self):
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

        title = QLabel("Candidate Detail")
        title.setObjectName("ResearchPreviewSectionTitle")
        layout.addWidget(title)

        self.candidate_detail_empty_label = QLabel("No selected candidate")
        self.candidate_detail_empty_label.setObjectName("EmptyStateLabel")
        self.candidate_detail_empty_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.candidate_detail_empty_label)

        self.candidate_detail_content = QWidget()
        grid = QGridLayout(self.candidate_detail_content)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(DesignSystem.Spacing.LG)
        grid.setVerticalSpacing(DesignSystem.Spacing.XS)
        self.candidate_detail_labels = {}
        for index, (key, title_text) in enumerate(
            [
                ("ticker", "Ticker"),
                ("rank", "Rank"),
                ("final_score", "Final Score"),
                ("grade", "Grade"),
                ("confidence_level", "Confidence"),
                ("setup_label", "Setup"),
                ("explanation", "Explanations"),
                ("warnings", "Warnings"),
                ("rejection_reasons", "Rejections"),
            ]
        ):
            row = index
            label = QLabel(title_text)
            label.setObjectName("ResearchPreviewFieldLabel")
            value = QLabel("N/A")
            value.setObjectName("ResearchPreviewFieldValue")
            value.setWordWrap(True)
            value.setTextInteractionFlags(Qt.TextSelectableByMouse)
            grid.addWidget(label, row, 0)
            grid.addWidget(value, row, 1)
            self.candidate_detail_labels[key] = value
        layout.addWidget(self.candidate_detail_content)
        self.candidate_detail_content.hide()
        return section

    def populate_ranked_candidates(self, candidates):
        self.current_candidates = list(candidates or [])
        if not candidates:
            self.ranked_empty_label.setText("No ranked candidates available")
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
            source_rows=self.current_candidates,
        )
        self.set_empty_state(
            self.ranked_candidates_table,
            self.ranked_empty_label,
            not candidates,
        )
        self.clear_candidate_detail()

    def populate_run_history(self, runs):
        self.current_runs = list(runs or [])
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
            source_rows=self.current_runs,
        )
        self.set_empty_state(
            self.run_history_table,
            self.run_history_empty_label,
            not runs,
        )
        if not runs:
            self.clear_run_detail()

    def show_ranked_empty_message(self, message):
        self.ranked_empty_label.setText(message)
        self.set_empty_state(self.ranked_candidates_table, self.ranked_empty_label, True)

    def set_run_detail(self, run):
        if not run:
            self.clear_run_detail()
            return

        for key, label in self.run_detail_labels.items():
            value = self.value(run, key)
            if key in {"warnings", "errors"}:
                value = self.list_text(value)
            label.setText(self.display_value(value))
        self.run_detail_empty_label.hide()
        self.run_detail_content.show()

    def clear_run_detail(self, message="No selected run"):
        self.run_detail_empty_label.setText(message)
        self.run_detail_empty_label.show()
        self.run_detail_content.hide()

    def set_candidate_detail(self, candidate):
        if not candidate:
            self.clear_candidate_detail()
            return

        for key, label in self.candidate_detail_labels.items():
            value = self.value(candidate, key)
            if key in {"explanation", "warnings", "rejection_reasons"}:
                value = self.list_text(value)
            label.setText(self.display_value(value))
        self.candidate_detail_empty_label.hide()
        self.candidate_detail_content.show()

    def clear_candidate_detail(self, message="No selected candidate"):
        self.candidate_detail_empty_label.setText(message)
        self.candidate_detail_empty_label.show()
        self.candidate_detail_content.hide()

    def handle_run_selection(self):
        row = self.selected_row(self.run_history_table)
        if row is None:
            self.clear_run_detail()
            return
        item = self.run_history_table.item(row, 0)
        run = item.data(self.SOURCE_ROLE) if item is not None else None
        if run is None:
            self.clear_run_detail()
            return
        self.set_run_detail(run)
        run_id = self.value(run, "run_id")
        if run_id not in (None, ""):
            self.run_selected.emit(str(run_id))

    def handle_candidate_selection(self):
        row = self.selected_row(self.ranked_candidates_table)
        if row is None:
            self.clear_candidate_detail()
            return
        item = self.ranked_candidates_table.item(row, 1)
        candidate = item.data(self.SOURCE_ROLE) if item is not None else None
        self.set_candidate_detail(candidate)
        if candidate is not None:
            self.candidate_selected.emit(candidate)

    @staticmethod
    def selected_row(table):
        indexes = table.selectionModel().selectedRows()
        return indexes[0].row() if indexes else None

    @staticmethod
    def populate_table(table, rows, numeric_columns=None, source_rows=None):
        numeric_columns = numeric_columns or set()
        source_rows = source_rows or []
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
                if row_index < len(source_rows):
                    item.setData(ScreeningResultsPanel.SOURCE_ROLE, source_rows[row_index])
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
    def list_text(value):
        if not value:
            return "N/A"
        if isinstance(value, (list, tuple)):
            return "\n".join(str(item) for item in value) if value else "N/A"
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
