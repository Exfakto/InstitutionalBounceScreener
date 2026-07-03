from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QCheckBox,
    QComboBox,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.design_system import DashboardDesignSystem as DesignSystem
from ui.widgets.candidate_chart_panel import CandidateChartPanel


class ScreeningResultsPanel(QWidget):
    SOURCE_ROLE = Qt.UserRole + 1
    refresh_ranked_candidates_requested = Signal()
    refresh_run_history_requested = Signal()
    run_screening_requested = Signal(str)
    cancel_screening_requested = Signal()
    screening_mode_changed = Signal(str)
    scan_preset_changed = Signal(str)
    run_selected = Signal(str)
    candidate_selected = Signal(object)
    export_candidates_csv_requested = Signal()
    export_candidates_json_requested = Signal()
    export_full_run_package_requested = Signal()
    load_more_ranked_candidates_requested = Signal()
    load_more_run_history_requested = Signal()
    refresh_selected_ticker_requested = Signal(str, bool)
    refresh_ticker_list_requested = Signal(str, bool)
    refresh_universe_symbols_requested = Signal(bool)
    cancel_data_refresh_requested = Signal()
    clear_cache_ticker_requested = Signal(str)
    clear_all_cache_requested = Signal()
    provider_diagnostics_requested = Signal()
    data_quality_report_requested = Signal(str)

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

        scroll_area = QScrollArea()
        scroll_area.setObjectName("ScreeningResultsScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(DesignSystem.Spacing.MD)

        content_layout.addWidget(self.build_screening_controls())
        content_layout.addWidget(self.build_market_data_controls())
        content_layout.addWidget(self.build_export_controls())

        ranked_section, self.ranked_candidates_table, self.ranked_empty_label = (
            self.build_table_section(
                "Ranked Candidates",
                "No ranked candidates available",
                self.RANKED_HEADERS,
                self.refresh_ranked_candidates_requested,
                self.load_more_ranked_candidates_requested,
            )
        )
        history_section, self.run_history_table, self.run_history_empty_label = (
            self.build_table_section(
                "Run History",
                "No screening runs available",
                self.HISTORY_HEADERS,
                self.refresh_run_history_requested,
                self.load_more_run_history_requested,
            )
        )

        content_layout.addWidget(ranked_section, stretch=3)
        content_layout.addWidget(history_section, stretch=2)
        content_layout.addWidget(self.build_run_detail_section(), stretch=1)
        content_layout.addWidget(self.build_candidate_detail_section(), stretch=2)
        self.candidate_chart_panel = CandidateChartPanel()
        content_layout.addWidget(self.candidate_chart_panel, stretch=2)
        content_layout.addStretch(1)
        scroll_area.setWidget(content)
        layout.addWidget(scroll_area)
        self.scroll_area = scroll_area

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
        self.scan_preset_combo = QComboBox()
        self.scan_preset_combo.setObjectName("ScanPresetCombo")
        self.scan_preset_combo.currentTextChanged.connect(self.scan_preset_changed.emit)
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
        self.screening_status_label.setProperty("status", "ready")
        self.screening_status_label.setWordWrap(True)
        self.universe_count_label = QLabel("Universe: --")
        self.universe_count_label.setObjectName("ResearchPreviewFieldValue")
        self.preset_description_label = QLabel("Preset: --")
        self.preset_description_label.setObjectName("ResearchPreviewFieldValue")
        self.preset_description_label.setWordWrap(True)
        self.active_filter_summary_label = QLabel("Filters: --")
        self.active_filter_summary_label.setObjectName("ResearchPreviewFieldValue")
        self.active_filter_summary_label.setWordWrap(True)

        layout.addWidget(self.screening_mode_combo)
        layout.addWidget(self.scan_preset_combo)
        layout.addWidget(label)
        layout.addWidget(self.ticker_input, stretch=1)
        layout.addWidget(self.run_screening_button)
        layout.addWidget(self.cancel_screening_button)
        layout.addWidget(self.universe_count_label)
        layout.addWidget(self.screening_status_label)
        layout.addWidget(self.preset_description_label, stretch=1)
        layout.addWidget(self.active_filter_summary_label, stretch=1)
        return section

    def build_export_controls(self):
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

        label = QLabel("Exports")
        label.setObjectName("ResearchPreviewFieldLabel")
        self.export_candidates_csv_button = QPushButton("Export Candidates CSV")
        self.export_candidates_csv_button.setObjectName("SecondaryButton")
        self.export_candidates_csv_button.clicked.connect(
            self.export_candidates_csv_requested.emit
        )
        self.export_candidates_json_button = QPushButton("Export Candidates JSON")
        self.export_candidates_json_button.setObjectName("SecondaryButton")
        self.export_candidates_json_button.clicked.connect(
            self.export_candidates_json_requested.emit
        )
        self.export_full_run_package_button = QPushButton(
            "Export Full Run Package JSON"
        )
        self.export_full_run_package_button.setObjectName("SecondaryButton")
        self.export_full_run_package_button.clicked.connect(
            self.export_full_run_package_requested.emit
        )
        self.export_status_label = QLabel("No exportable results")
        self.export_status_label.setObjectName("ResearchPreviewFieldValue")
        self.export_status_label.setProperty("status", "empty")
        self.export_status_label.setWordWrap(True)

        layout.addWidget(label)
        layout.addWidget(self.export_candidates_csv_button)
        layout.addWidget(self.export_candidates_json_button)
        layout.addWidget(self.export_full_run_package_button)
        layout.addWidget(self.export_status_label, stretch=1)
        self.set_export_enabled(False)
        return section

    def build_market_data_controls(self):
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

        label = QLabel("Market Data")
        label.setObjectName("ResearchPreviewFieldLabel")
        self.data_refresh_ticker_input = QLineEdit()
        self.data_refresh_ticker_input.setObjectName("DataRefreshTickerInput")
        self.data_refresh_ticker_input.setPlaceholderText("Ticker or CSV list")
        self.force_refresh_checkbox = QCheckBox("Force")
        self.force_refresh_checkbox.setObjectName("ForceRefreshCheckbox")
        self.refresh_selected_ticker_button = QPushButton("Refresh Ticker")
        self.refresh_selected_ticker_button.setObjectName("SecondaryButton")
        self.refresh_selected_ticker_button.clicked.connect(
            self.emit_refresh_selected_ticker
        )
        self.refresh_ticker_list_button = QPushButton("Refresh List")
        self.refresh_ticker_list_button.setObjectName("SecondaryButton")
        self.refresh_ticker_list_button.clicked.connect(self.emit_refresh_ticker_list)
        self.refresh_universe_symbols_button = QPushButton("Refresh Universe")
        self.refresh_universe_symbols_button.setObjectName("SecondaryButton")
        self.refresh_universe_symbols_button.clicked.connect(
            self.emit_refresh_universe_symbols
        )
        self.cancel_data_refresh_button = QPushButton("Cancel Refresh")
        self.cancel_data_refresh_button.setObjectName("SecondaryButton")
        self.cancel_data_refresh_button.setEnabled(False)
        self.cancel_data_refresh_button.clicked.connect(
            self.cancel_data_refresh_requested.emit
        )
        self.cache_coverage_button = QPushButton("Cache Coverage")
        self.cache_coverage_button.setObjectName("SecondaryButton")
        self.cache_coverage_button.clicked.connect(self.emit_data_quality_report)
        self.clear_cache_ticker_button = QPushButton("Clear Ticker Cache")
        self.clear_cache_ticker_button.setObjectName("SecondaryButton")
        self.clear_cache_ticker_button.clicked.connect(self.emit_clear_cache_ticker)
        self.clear_all_cache_button = QPushButton("Clear All Cache")
        self.clear_all_cache_button.setObjectName("SecondaryButton")
        self.clear_all_cache_button.clicked.connect(self.clear_all_cache_requested.emit)
        self.provider_diagnostics_button = QPushButton("Provider Diagnostics")
        self.provider_diagnostics_button.setObjectName("SecondaryButton")
        self.provider_diagnostics_button.clicked.connect(
            self.provider_diagnostics_requested.emit
        )
        self.market_data_status_label = QLabel("Market data ready")
        self.market_data_status_label.setObjectName("ResearchPreviewFieldValue")
        self.market_data_status_label.setWordWrap(True)
        self.cache_coverage_label = QLabel("Cache: --")
        self.cache_coverage_label.setObjectName("ResearchPreviewFieldValue")
        self.cache_coverage_label.setWordWrap(True)

        layout.addWidget(label)
        layout.addWidget(self.data_refresh_ticker_input, stretch=1)
        layout.addWidget(self.force_refresh_checkbox)
        layout.addWidget(self.refresh_selected_ticker_button)
        layout.addWidget(self.refresh_ticker_list_button)
        layout.addWidget(self.refresh_universe_symbols_button)
        layout.addWidget(self.cancel_data_refresh_button)
        layout.addWidget(self.cache_coverage_button)
        layout.addWidget(self.clear_cache_ticker_button)
        layout.addWidget(self.clear_all_cache_button)
        layout.addWidget(self.provider_diagnostics_button)
        layout.addWidget(self.cache_coverage_label, stretch=1)
        layout.addWidget(self.market_data_status_label, stretch=1)
        return section

    def emit_refresh_selected_ticker(self):
        ticker = self.data_refresh_ticker_input.text().strip() or self.selected_candidate_ticker()
        self.refresh_selected_ticker_requested.emit(
            ticker,
            self.force_refresh_checkbox.isChecked(),
        )

    def emit_refresh_ticker_list(self):
        self.refresh_ticker_list_requested.emit(
            self.data_refresh_ticker_input.text(),
            self.force_refresh_checkbox.isChecked(),
        )

    def emit_refresh_universe_symbols(self):
        self.refresh_universe_symbols_requested.emit(self.force_refresh_checkbox.isChecked())

    def emit_clear_cache_ticker(self):
        ticker = self.data_refresh_ticker_input.text().strip() or self.selected_candidate_ticker()
        self.clear_cache_ticker_requested.emit(ticker)

    def emit_data_quality_report(self):
        self.data_quality_report_requested.emit(self.data_refresh_ticker_input.text())

    def selected_candidate_ticker(self):
        row = self.selected_row(self.ranked_candidates_table)
        if row is None:
            return ""
        item = self.ranked_candidates_table.item(row, 1)
        return item.text() if item is not None and item.text() != "N/A" else ""

    def set_data_refresh_active(self, active, status_text=None):
        for button in (
            self.refresh_selected_ticker_button,
            self.refresh_ticker_list_button,
            self.refresh_universe_symbols_button,
        ):
            button.setEnabled(not active)
        self.cancel_data_refresh_button.setEnabled(bool(active))
        if status_text is not None:
            self.set_market_data_status(status_text)

    def set_market_data_status(self, status_text):
        self.market_data_status_label.setText(status_text or "")
        self.apply_status_property(self.market_data_status_label, status_text)

    def set_cache_coverage_summary(self, coverage_rows):
        rows = list(coverage_rows or [])
        total_tickers = len(rows)
        total_rows = sum(int(self.value(row, "row_count") or 0) for row in rows)
        stale_count = sum(1 for row in rows if self.value(row, "stale"))
        if total_tickers == 0:
            self.cache_coverage_label.setText("Cache: empty")
        else:
            self.cache_coverage_label.setText(
                f"Cache: {total_tickers} tickers / {total_rows} rows / {stale_count} stale"
            )

    def emit_run_screening(self):
        self.run_screening_requested.emit(self.ticker_input.text())

    def handle_mode_changed(self, mode):
        self.ticker_input.setEnabled(not self.is_universe_scan_mode())
        self.screening_mode_changed.emit(mode)

    def is_universe_scan_mode(self):
        return self.screening_mode_combo.currentText() == "Universe scan mode"

    def set_universe_count(self, count):
        self.universe_count_label.setText(f"Universe: {count}")

    def set_scan_presets(self, presets):
        current = self.scan_preset_combo.currentText()
        self.scan_preset_combo.blockSignals(True)
        self.scan_preset_combo.clear()
        for preset in presets or []:
            self.scan_preset_combo.addItem(preset.name)
        if current:
            index = self.scan_preset_combo.findText(current)
            if index >= 0:
                self.scan_preset_combo.setCurrentIndex(index)
        self.scan_preset_combo.blockSignals(False)

    def selected_scan_preset_name(self):
        return self.scan_preset_combo.currentText()

    def set_preset_description(self, text):
        self.preset_description_label.setText(text or "Preset: --")

    def set_active_filter_summary(self, text):
        self.active_filter_summary_label.setText(text or "Filters: --")

    def set_screening_active(self, active, status_text=None):
        self.run_screening_button.setEnabled(not active)
        self.cancel_screening_button.setEnabled(active)
        if status_text is not None:
            self.set_screening_status(status_text)

    def set_screening_status(self, status_text):
        self.screening_status_label.setText(status_text)
        self.apply_status_property(self.screening_status_label, status_text)

    def set_export_enabled(self, enabled):
        for button in (
            self.export_candidates_csv_button,
            self.export_candidates_json_button,
            self.export_full_run_package_button,
        ):
            button.setEnabled(bool(enabled))

    def set_export_status(self, status_text):
        self.export_status_label.setText(status_text or "")
        self.apply_status_property(self.export_status_label, status_text)

    def build_table_section(self, title, empty_text, headers, signal, load_more_signal):
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
        count_label = QLabel("Loaded 0")
        count_label.setObjectName("ResearchPreviewFieldValue")
        load_more_button = QPushButton("Load More")
        load_more_button.setObjectName("SecondaryButton")
        load_more_button.clicked.connect(load_more_signal.emit)
        header.addWidget(label)
        header.addStretch()
        header.addWidget(count_label)
        header.addWidget(load_more_button)
        header.addWidget(refresh_button)
        layout.addLayout(header)

        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setAlternatingRowColors(True)
        table.setSortingEnabled(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setShowGrid(False)
        table.setWordWrap(False)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(30)
        table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        table.horizontalHeader().setMinimumSectionSize(72)
        if title == "Ranked Candidates":
            table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        else:
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.setStyleSheet(DesignSystem.table_style())
        table.setMinimumHeight(128)
        layout.addWidget(table)

        empty_label = QLabel(empty_text)
        empty_label.setObjectName("EmptyStateLabel")
        empty_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(empty_label)

        if title == "Ranked Candidates":
            self.ranked_count_label = count_label
            self.ranked_load_more_button = load_more_button
        else:
            self.run_history_count_label = count_label
            self.run_history_load_more_button = load_more_button

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

    def populate_ranked_candidates(self, candidates, total_count=None, append=False):
        self.current_candidates = (
            [*self.current_candidates, *(candidates or [])]
            if append
            else list(candidates or [])
        )
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
                for candidate in self.current_candidates
            ],
            numeric_columns={0, 2, 6, 7},
            source_rows=self.current_candidates,
        )
        self.set_empty_state(
            self.ranked_candidates_table,
            self.ranked_empty_label,
            not self.current_candidates,
        )
        self.update_loaded_count(
            self.ranked_count_label,
            self.ranked_load_more_button,
            len(self.current_candidates),
            total_count,
        )
        self.clear_candidate_detail()

    def populate_run_history(self, runs, total_count=None, append=False):
        self.current_runs = (
            [*self.current_runs, *(runs or [])]
            if append
            else list(runs or [])
        )
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
                for run in self.current_runs
            ],
            numeric_columns={4, 5, 6},
            source_rows=self.current_runs,
        )
        self.set_empty_state(
            self.run_history_table,
            self.run_history_empty_label,
            not self.current_runs,
        )
        self.update_loaded_count(
            self.run_history_count_label,
            self.run_history_load_more_button,
            len(self.current_runs),
            total_count,
        )
        if not self.current_runs:
            self.clear_run_detail()

    @staticmethod
    def update_loaded_count(label, button, loaded_count, total_count=None):
        total = total_count if total_count is not None else loaded_count
        label.setText(f"Loaded {loaded_count} of {total}")
        button.setEnabled(total_count is None and loaded_count > 0 or loaded_count < total)

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
        if hasattr(self, "candidate_chart_panel"):
            self.candidate_chart_panel.clear()

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
        self.candidate_chart_panel.set_candidate(candidate)
        if candidate is not None:
            self.candidate_selected.emit(candidate)

    def set_candidate_chart_model(self, chart_model):
        self.candidate_chart_panel.set_chart_model(chart_model)

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
                role = ScreeningResultsPanel.status_role(value)
                if role:
                    item.setData(Qt.UserRole + 2, role)
                    item.setForeground(ScreeningResultsPanel.status_brush(role))
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

    @staticmethod
    def apply_status_property(label, text):
        normalized = str(text or "").lower()
        if any(word in normalized for word in ["failed", "error", "unable"]):
            role = "error"
        elif any(word in normalized for word in ["warning", "limited", "cancel"]):
            role = "warning"
        elif any(word in normalized for word in ["complete", "saved", "ready"]):
            role = "success"
        elif any(word in normalized for word in ["processing", "starting"]):
            role = "running"
        else:
            role = "empty"
        label.setProperty("status", role)
        label.style().unpolish(label)
        label.style().polish(label)

    @staticmethod
    def status_role(value):
        text = str(value or "").upper()
        if text in {"A+", "A", "HIGH", "COMPLETED", "COMPLETE"}:
            return "success"
        if text in {"B", "C", "MEDIUM", "PARTIAL", "WATCH"}:
            return "warning"
        if text in {"D", "REJECT", "LOW", "FAILED", "CANCELLED", "PARTIAL_CANCELLED"}:
            return "error"
        return None

    @staticmethod
    def status_brush(role):
        from PySide6.QtGui import QColor, QBrush

        colors = {
            "success": "#4ade80",
            "warning": "#facc15",
            "error": "#fb7185",
        }
        return QBrush(QColor(colors.get(role, "#cbd5e1")))
