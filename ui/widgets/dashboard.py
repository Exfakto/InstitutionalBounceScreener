from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHeaderView,
    QLabel,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class InstitutionalDashboard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("InstitutionalDashboard")
        self.section_frames = {}
        self.market_labels = {}
        self.opportunity_labels = {}
        self.watchlist_labels = {}
        self.backtesting_labels = {}
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
        root_layout.addWidget(scroll_area)

        content = QWidget()
        content.setObjectName("InstitutionalDashboardContent")
        scroll_area.setWidget(content)

        layout = QGridLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(12)
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
        layout.addWidget(market, 1, 0)
        layout.addWidget(opportunity, 1, 1)

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
        layout.addWidget(best, 2, 0, 1, 2)

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
        layout.addWidget(institutional, 3, 0, 1, 2)

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
        layout.addWidget(watchlist, 4, 0)

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
        layout.addWidget(research, 4, 1)

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
        layout.addWidget(backtesting, 5, 0, 1, 2)

    def _create_metric_section(self, title, fields, target):
        frame = self._create_section_frame(title)
        layout = frame.layout()
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)
        layout.addLayout(grid)

        for row, (key, label_text) in enumerate(fields):
            label = QLabel(label_text)
            label.setObjectName("ResearchPreviewFieldLabel")
            value = QLabel("--")
            value.setObjectName("ResearchPreviewFieldValue")
            value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            value.setTextInteractionFlags(Qt.TextSelectableByMouse)
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

    def _create_section_frame(self, title):
        frame = QFrame()
        frame.setObjectName("ResearchPreviewSection")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(10)

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
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setMinimumHeight(132)
        return table

    def _create_empty_label(self, text):
        label = QLabel(text)
        label.setObjectName("EmptyStateLabel")
        label.setAlignment(Qt.AlignCenter)
        label.setMinimumHeight(88)
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
