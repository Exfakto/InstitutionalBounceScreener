from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class InstitutionalDashboard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("InstitutionalDashboard")
        self.setStyleSheet(self.dashboard_style())
        self.section_frames = {}
        self.market_labels = {}
        self.opportunity_labels = {}
        self.watchlist_labels = {}
        self.backtesting_labels = {}
        self.activity_entries = []
        self._build_ui()
        self.clear()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        scroll_area = QScrollArea()
        scroll_area.setObjectName("InstitutionalDashboardScroll")
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        root_layout.addWidget(scroll_area)
        self.scroll_area = scroll_area

        content = QWidget()
        content.setObjectName("InstitutionalDashboardContent")
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        scroll_area.setWidget(content)

        layout = QGridLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(14)
        layout.setVerticalSpacing(14)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)

        self.empty_state_label = QLabel("No dashboard data available.")
        self.empty_state_label.setObjectName("EmptyStateLabel")
        self.empty_state_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.empty_state_label, 0, 0, 1, 2)

        market = self._create_metric_section(
            "Market Summary",
            [
                ("market_status", "Market Status"),
                ("active_provider", "Active Provider"),
                ("last_refresh", "Last Refresh"),
                ("database_status", "Database Status"),
            ],
            self.market_labels,
        )
        opportunity = self._create_metric_section(
            "Opportunity Summary",
            [
                ("candidates_screened", "Candidates Screened"),
                ("high_conviction", "High Conviction"),
                ("watch_candidates", "Watch Candidates"),
                ("average_opportunity_score", "Avg Opportunity Score"),
            ],
            self.opportunity_labels,
        )
        activity_feed = self._create_activity_feed_section()
        layout.addWidget(activity_feed, 1, 0, 1, 2)

        layout.addWidget(market, 2, 0)
        layout.addWidget(opportunity, 2, 1)

        self.best_opportunities_table = self._create_table(
            ["Ticker", "Company", "Opportunity Score", "Confidence", "Risk/Reward"]
        )
        self.best_opportunities_empty = self._create_empty_label(
            "No ranked opportunities available."
        )
        best = self._create_table_section(
            "Best Opportunities",
            self.best_opportunities_table,
            self.best_opportunities_empty,
        )
        layout.addWidget(best, 3, 0, 1, 2)

        self.institutional_table = self._create_table(
            ["Ticker", "Institutional Score", "Ownership Trend", "Insider Activity", "13F Status"]
        )
        self.institutional_empty = self._create_empty_label(
            "No institutional activity available."
        )
        institutional = self._create_table_section(
            "Institutional Activity",
            self.institutional_table,
            self.institutional_empty,
        )
        layout.addWidget(institutional, 4, 0, 1, 2)

        watchlist = self._create_metric_section(
            "Watchlist Summary",
            [
                ("total_items", "Total Items"),
                ("high_priority", "High Priority"),
                ("action_required", "Action Required"),
                ("average_score", "Average Score"),
            ],
            self.watchlist_labels,
        )
        layout.addWidget(watchlist, 5, 0)

        self.recent_research_table = self._create_table(
            ["Ticker", "Report", "Generated"]
        )
        self.recent_research_empty = self._create_empty_label(
            "No recent research available."
        )
        research = self._create_table_section(
            "Recent Research",
            self.recent_research_table,
            self.recent_research_empty,
        )
        layout.addWidget(research, 5, 1)

        backtesting = self._create_metric_section(
            "Backtesting Snapshot",
            [
                ("last_backtest", "Last Backtest"),
                ("win_rate", "Win Rate"),
                ("total_return", "Total Return"),
                ("max_drawdown", "Max Drawdown"),
            ],
            self.backtesting_labels,
        )
        layout.addWidget(backtesting, 6, 0, 1, 2)

    def _create_metric_section(self, title, fields, target):
        frame = self._create_section_frame(title)
        layout = frame.layout()
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)

        for row, (key, label_text) in enumerate(fields):
            label = QLabel(label_text)
            label.setObjectName("ResearchPreviewFieldLabel")
            value = QLabel("--")
            value.setObjectName("ResearchPreviewFieldValue")
            value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            value.setTextInteractionFlags(Qt.TextSelectableByMouse)
            value.setMinimumWidth(96)
            grid.addWidget(label, row, 0)
            grid.addWidget(value, row, 1)
            target[key] = value

        return frame

    def _create_table_section(self, title, table, empty_label):
        frame = self._create_section_frame(title)
        layout = frame.layout()
        layout.addWidget(table)
        layout.addWidget(empty_label)
        return frame

    def _create_activity_feed_section(self):
        frame = self._create_section_frame("Activity Feed")
        layout = frame.layout()

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.addStretch()

        self.clear_activity_button = QPushButton("Clear Log")
        self.clear_activity_button.setObjectName("ActivityFeedClearButton")
        self.clear_activity_button.setProperty("variant", "secondary")
        self.clear_activity_button.clicked.connect(self.clear_activity)
        header_layout.addWidget(self.clear_activity_button)

        self.activity_feed_table = self._create_table(
            ["Time", "Status", "Message"]
        )
        self.activity_feed_table.setObjectName("ActivityFeedTable")
        self.activity_feed_table.setMinimumHeight(96)
        self.activity_feed_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Interactive
        )
        self.activity_feed_table.setColumnWidth(0, 155)
        self.activity_feed_table.setColumnWidth(1, 88)
        self.activity_feed_table.horizontalHeader().setStretchLastSection(True)

        self.activity_feed_empty = self._create_empty_label(
            "No activity recorded yet."
        )

        layout.addLayout(header_layout)
        layout.addWidget(self.activity_feed_table)
        layout.addWidget(self.activity_feed_empty)

        return frame

    def _create_section_frame(self, title):
        frame = QFrame()
        frame.setObjectName("ResearchPreviewSection")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(9)

        label = QLabel(title)
        label.setObjectName("ResearchPreviewSectionTitle")
        layout.addWidget(label)
        self.section_frames[self._section_key(title)] = frame
        return frame

    def _create_table(self, headers):
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.NoSelection)
        table.setShowGrid(False)
        table.setWordWrap(False)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(34)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setMinimumHeight(88)
        table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        return table

    def _create_empty_label(self, text):
        label = QLabel(text)
        label.setObjectName("EmptyStateLabel")
        label.setAlignment(Qt.AlignCenter)
        label.setMinimumHeight(56)
        label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        return label

    def set_dashboard_data(self, data):
        data = data or {}
        has_data = bool(data)
        self.empty_state_label.setVisible(not has_data)

        self._update_labels(
            self.market_labels,
            data.get("market_summary") or {},
            {
                "market_status": self._format_text,
                "active_provider": self._format_text,
                "last_refresh": self._format_text,
                "database_status": self._format_text,
            },
        )
        self._update_labels(
            self.opportunity_labels,
            data.get("opportunity_summary") or {},
            {
                "candidates_screened": self._format_int,
                "high_conviction": self._format_int,
                "watch_candidates": self._format_int,
                "average_opportunity_score": self._format_score,
            },
        )
        self._populate_table(
            self.best_opportunities_table,
            data.get("best_opportunities") or [],
            ["ticker", "company", "opportunity_score", "confidence", "risk_reward"],
            {
                "opportunity_score": self._format_score,
                "risk_reward": self._format_risk_reward,
            },
        )
        self._toggle_table_empty(
            self.best_opportunities_table,
            self.best_opportunities_empty,
        )

        institutional_rows = data.get("institutional_activity") or []
        self._populate_table(
            self.institutional_table,
            institutional_rows,
            [
                "ticker",
                "institutional_score",
                "ownership_trend",
                "insider_activity",
                "thirteen_f_status",
            ],
            {"institutional_score": self._format_score},
        )
        self._toggle_table_empty(self.institutional_table, self.institutional_empty)
        self.section_frames["institutional_activity"].setVisible(bool(institutional_rows))

        self._update_labels(
            self.watchlist_labels,
            data.get("watchlist_summary") or {},
            {
                "total_items": self._format_int,
                "high_priority": self._format_int,
                "action_required": self._format_int,
                "average_score": self._format_score,
            },
        )

        recent_research = data.get("recent_research") or []
        self._populate_table(
            self.recent_research_table,
            recent_research,
            ["ticker", "title", "generated_at"],
            {},
        )
        self._toggle_table_empty(self.recent_research_table, self.recent_research_empty)
        self.section_frames["recent_research"].setVisible(bool(recent_research))

        backtesting_snapshot = data.get("backtesting_snapshot") or {}
        self._update_labels(
            self.backtesting_labels,
            backtesting_snapshot,
            {
                "last_backtest": self._format_text,
                "win_rate": self._format_percent,
                "total_return": self._format_percent,
                "max_drawdown": self._format_percent,
            },
        )
        self.section_frames["backtesting_snapshot"].setVisible(bool(backtesting_snapshot))

    def refresh(self, data=None):
        self.set_dashboard_data(data or {})

    def clear(self):
        self.set_dashboard_data({})

    def add_activity(self, message, status="info", timestamp=None):
        """
        Append a dashboard activity feed entry.
        """

        timestamp_text = self._format_activity_timestamp(timestamp)
        normalized_status = self._normalize_activity_status(status)
        entry = {
            "timestamp": timestamp_text,
            "status": normalized_status,
            "message": str(message or ""),
        }
        self.activity_entries.append(entry)
        self._append_activity_row(entry)
        self._toggle_table_empty(self.activity_feed_table, self.activity_feed_empty)
        return entry

    def clear_activity(self):
        self.activity_entries = []
        self.activity_feed_table.setRowCount(0)
        self._toggle_table_empty(self.activity_feed_table, self.activity_feed_empty)

    def activity_count(self):
        return len(self.activity_entries)

    def _append_activity_row(self, entry):
        row = self.activity_feed_table.rowCount()
        self.activity_feed_table.insertRow(row)

        values = [
            entry["timestamp"],
            self._activity_status_label(entry["status"]),
            entry["message"],
        ]
        for column, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            if column == 1:
                item.setTextAlignment(Qt.AlignCenter)
            self.activity_feed_table.setItem(row, column, item)
        self.activity_feed_table.scrollToBottom()

    def _update_labels(self, labels, values, formatters):
        for key, label in labels.items():
            formatter = formatters.get(key, self._format_text)
            label.setText(formatter(values.get(key)))

    def _populate_table(self, table, rows, columns, formatters):
        table.setRowCount(0)
        for row_index, row in enumerate(rows):
            table.insertRow(row_index)
            for column_index, key in enumerate(columns):
                value = self._row_value(row, key)
                formatter = formatters.get(key, self._format_text)
                item = QTableWidgetItem(formatter(value))
                item.setTextAlignment(Qt.AlignCenter)
                if column_index in (0, 1):
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                table.setItem(row_index, column_index, item)

    @staticmethod
    def _toggle_table_empty(table, empty_label):
        has_rows = table.rowCount() > 0
        table.setVisible(has_rows)
        empty_label.setVisible(not has_rows)

    @staticmethod
    def _format_activity_timestamp(timestamp):
        timestamp = timestamp or datetime.now()
        if isinstance(timestamp, datetime):
            return timestamp.strftime("%Y-%m-%d %H:%M:%S")
        return str(timestamp)

    @staticmethod
    def _normalize_activity_status(status):
        normalized = str(status or "info").lower()
        if normalized in {"info", "success", "warning", "error", "running"}:
            return normalized
        return "info"

    @staticmethod
    def _activity_status_label(status):
        labels = {
            "info": "INFO",
            "success": "OK",
            "warning": "WARN",
            "error": "ERROR",
            "running": "RUN",
        }
        return labels.get(status, "INFO")

    @staticmethod
    def _row_value(row, key):
        if isinstance(row, dict):
            return row.get(key)
        return getattr(row, key, None)

    @staticmethod
    def _section_key(title):
        return title.lower().replace(" ", "_")

    @staticmethod
    def _format_text(value):
        if value in (None, ""):
            return "--"
        return str(value)

    @staticmethod
    def _format_int(value):
        if value in (None, ""):
            return "0"
        try:
            return f"{int(value):,}"
        except (TypeError, ValueError):
            return str(value)

    @staticmethod
    def _format_score(value):
        if value in (None, ""):
            return "--"
        try:
            return f"{float(value):.1f}"
        except (TypeError, ValueError):
            return str(value)

    @staticmethod
    def _format_risk_reward(value):
        if value in (None, ""):
            return "--"
        try:
            return f"{float(value):.2f}:1"
        except (TypeError, ValueError):
            return str(value)

    @staticmethod
    def _format_percent(value):
        if value in (None, ""):
            return "--"
        try:
            number = float(value)
        except (TypeError, ValueError):
            return str(value)
        if abs(number) <= 1:
            number *= 100
        return f"{number:.1f}%"

    @staticmethod
    def dashboard_style():
        return """
        QWidget#InstitutionalDashboard {
            background-color: transparent;
        }
        QWidget#InstitutionalDashboardContent {
            background-color: transparent;
        }
        QFrame#ResearchPreviewSection {
            background-color: #101923;
            border: 1px solid #2F3E4D;
            border-radius: 8px;
        }
        QLabel#ResearchPreviewSectionTitle {
            color: #D7E0EA;
            font-size: 10pt;
            font-weight: 900;
        }
        QLabel#ResearchPreviewFieldLabel {
            color: #8392A1;
            font-size: 9pt;
            font-weight: 700;
        }
        QLabel#ResearchPreviewFieldValue {
            color: #F3F7FA;
            background-color: #0D151D;
            border: 1px solid #22303D;
            border-radius: 5px;
            padding: 4px 8px;
            font-size: 9pt;
            font-weight: 800;
        }
        QTableWidget {
            background-color: #0F171F;
            alternate-background-color: #141E28;
            border: 1px solid #263645;
            border-radius: 7px;
            color: #E5EEF7;
            gridline-color: transparent;
            selection-background-color: #24537B;
        }
        QTableWidget::item {
            padding: 7px 9px;
            border-bottom: 1px solid #22303D;
        }
        QHeaderView::section {
            background-color: #0A1118;
            color: #AEBCCC;
            border: none;
            border-right: 1px solid #22303D;
            border-bottom: 1px solid #334252;
            padding: 8px 9px;
            font-weight: 900;
        }
        QLabel#EmptyStateLabel {
            color: #9EACBA;
            background-color: #0F171F;
            border: 1px solid #263645;
            border-radius: 8px;
            padding: 14px;
            font-weight: 700;
        }
        """
