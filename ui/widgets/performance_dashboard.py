from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class PerformanceDashboard(QWidget):
    """
    Read-only display for precomputed portfolio and strategy statistics.
    """

    MISSING_VALUE = "-"
    RATING_ROWS = [
        ("\u2605\u2605\u2605\u2605\u2605", ("★★★★★", "Elite Bounce")),
        ("\u2605\u2605\u2605\u2605\u2606", ("★★★★☆", "High Probability")),
        ("\u2605\u2605\u2605\u2606\u2606", ("★★★☆☆", "Acceptable")),
    ]
    CONFIDENCE_ROWS = ["Very High", "High", "Moderate", "Low", "Very Low"]
    RISK_REWARD_ROWS = ["<1.5", "1.5-2", "2-3", "3-5", ">5"]
    HOLDING_ROWS = ["0-5 days", "6-10 days", "11-20 days", ">20 days"]

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.group = QGroupBox("Performance Dashboard")
        self.group.setObjectName("ResearchPreviewCard")
        group_layout = QVBoxLayout()
        group_layout.setContentsMargins(10, 14, 10, 10)
        group_layout.setSpacing(8)

        self.empty_state_label = QLabel("No performance statistics available.")
        self.empty_state_label.setWordWrap(True)

        self.dashboard_frame = QFrame()
        self.dashboard_frame.setObjectName("ResearchPreviewDashboard")
        dashboard_layout = QVBoxLayout(self.dashboard_frame)
        dashboard_layout.setContentsMargins(0, 0, 0, 0)
        dashboard_layout.setSpacing(8)

        summary_section, summary_layout = self.create_titled_section(
            "Portfolio Summary"
        )
        self.summary_labels = {}
        for key, label in [
            ("total_trades", "Total Trades"),
            ("open_trades", "Open Trades"),
            ("closed_trades", "Closed Trades"),
            ("win_rate", "Win Rate"),
            ("average_return", "Average Return"),
            ("profit_factor", "Profit Factor"),
            ("expectancy", "Expectancy"),
        ]:
            self.summary_labels[key] = self.add_value_row(summary_layout, label)
        dashboard_layout.addWidget(summary_section)

        self.rating_table = self.create_table(
            ["Rating", "Win Rate", "Average Return"],
            len(self.RATING_ROWS),
        )
        rating_section, rating_layout = self.create_titled_section(
            "Opportunity Rating Performance"
        )
        rating_layout.addWidget(self.rating_table)
        dashboard_layout.addWidget(rating_section)

        self.confidence_table = self.create_table(
            ["Confidence", "Win Rate", "Average Return"],
            len(self.CONFIDENCE_ROWS),
        )
        confidence_section, confidence_layout = self.create_titled_section(
            "Confidence Performance"
        )
        confidence_layout.addWidget(self.confidence_table)
        dashboard_layout.addWidget(confidence_section)

        self.sector_table = self.create_table(
            ["Sector", "Trade Count", "Win Rate", "Average Return"],
            5,
        )
        sector_section, sector_layout = self.create_titled_section(
            "Sector Performance"
        )
        sector_layout.addWidget(self.sector_table)
        dashboard_layout.addWidget(sector_section)

        self.risk_reward_table = self.create_table(["Risk/Reward", "Trades"], 5)
        rr_section, rr_layout = self.create_titled_section(
            "Risk / Reward Distribution"
        )
        rr_layout.addWidget(self.risk_reward_table)
        dashboard_layout.addWidget(rr_section)

        self.holding_table = self.create_table(["Holding Period", "Trades"], 4)
        holding_section, holding_layout = self.create_titled_section(
            "Holding Period Distribution"
        )
        holding_layout.addWidget(self.holding_table)
        dashboard_layout.addWidget(holding_section)

        group_layout.addWidget(self.empty_state_label)
        group_layout.addWidget(self.dashboard_frame)
        group_layout.addStretch()

        self.group.setLayout(group_layout)
        layout.addWidget(self.group)

        self.clear()

    def clear(self):
        self.empty_state_label.show()
        self.dashboard_frame.hide()

        for label in self.summary_labels.values():
            label.setText(self.MISSING_VALUE)

        self.populate_table(
            self.rating_table,
            [[label, self.MISSING_VALUE, self.MISSING_VALUE] for label, _ in self.RATING_ROWS],
        )
        self.populate_table(
            self.confidence_table,
            [[label, self.MISSING_VALUE, self.MISSING_VALUE] for label in self.CONFIDENCE_ROWS],
        )
        self.populate_table(
            self.sector_table,
            [["", self.MISSING_VALUE, self.MISSING_VALUE, self.MISSING_VALUE] for _ in range(5)],
        )
        self.populate_table(
            self.risk_reward_table,
            [[label, self.MISSING_VALUE] for label in self.RISK_REWARD_ROWS],
        )
        self.populate_table(
            self.holding_table,
            [[label, self.MISSING_VALUE] for label in self.HOLDING_ROWS],
        )

    def set_statistics(self, portfolio_stats, strategy_stats):
        if portfolio_stats is None and strategy_stats is None:
            self.clear()
            return

        self.empty_state_label.hide()
        self.dashboard_frame.show()

        self.set_summary(portfolio_stats)
        self.set_rating_performance(strategy_stats)
        self.set_confidence_performance(strategy_stats)
        self.set_sector_performance(strategy_stats)
        self.set_risk_reward_distribution(strategy_stats)
        self.set_holding_distribution(strategy_stats)

    def set_summary(self, portfolio_stats):
        summary_map = {
            "total_trades": self.value_for(portfolio_stats, "total_trades"),
            "open_trades": self.value_for(portfolio_stats, "open_trades"),
            "closed_trades": self.value_for(portfolio_stats, "closed_trades"),
            "win_rate": self.value_for(portfolio_stats, "win_rate"),
            "average_return": self.first_value(
                portfolio_stats,
                ("average_return_pct", "average_return"),
            ),
            "profit_factor": self.value_for(portfolio_stats, "profit_factor"),
            "expectancy": self.value_for(portfolio_stats, "expectancy"),
        }

        for key, value in summary_map.items():
            percent = key in {"win_rate", "average_return", "expectancy"}
            self.summary_labels[key].setText(self.format_value(value, percent=percent))

    def set_rating_performance(self, strategy_stats):
        stats = self.value_for(strategy_stats, "opportunity_rating_statistics") or {}
        rows = []

        for label, keys in self.RATING_ROWS:
            item = self.first_mapping(stats, keys)
            rows.append(
                [
                    label,
                    self.format_value(self.value_for(item, "win_rate"), percent=True),
                    self.format_value(
                        self.value_for(item, "average_return"),
                        percent=True,
                    ),
                ]
            )

        self.populate_table(self.rating_table, rows)

    def set_confidence_performance(self, strategy_stats):
        stats = self.value_for(strategy_stats, "confidence_statistics") or {}
        rows = []

        for label in self.CONFIDENCE_ROWS:
            item = self.value_for(stats, label) or {}
            rows.append(
                [
                    label,
                    self.format_value(self.value_for(item, "win_rate"), percent=True),
                    self.format_value(
                        self.value_for(item, "average_return"),
                        percent=True,
                    ),
                ]
            )

        self.populate_table(self.confidence_table, rows)

    def set_sector_performance(self, strategy_stats):
        stats = self.value_for(strategy_stats, "sector_statistics") or {}
        rows = []

        for sector, values in list(stats.items())[:5]:
            rows.append(
                [
                    sector,
                    self.format_value(self.value_for(values, "trade_count")),
                    self.format_value(self.value_for(values, "win_rate"), percent=True),
                    self.format_value(
                        self.value_for(values, "average_return"),
                        percent=True,
                    ),
                ]
            )

        while len(rows) < 5:
            rows.append(["", self.MISSING_VALUE, self.MISSING_VALUE, self.MISSING_VALUE])

        self.populate_table(self.sector_table, rows)

    def set_risk_reward_distribution(self, strategy_stats):
        risk_reward = self.value_for(strategy_stats, "risk_reward_statistics") or {}
        distribution = self.value_for(risk_reward, "distribution") or {}

        self.populate_table(
            self.risk_reward_table,
            [
                [label, self.format_value(self.value_for(distribution, label))]
                for label in self.RISK_REWARD_ROWS
            ],
        )

    def set_holding_distribution(self, strategy_stats):
        distribution = (
            self.value_for(strategy_stats, "holding_period_statistics") or {}
        )

        self.populate_table(
            self.holding_table,
            [
                [label, self.format_value(self.value_for(distribution, label))]
                for label in self.HOLDING_ROWS
            ],
        )

    @classmethod
    def create_titled_section(cls, title):
        section = QFrame()
        section.setObjectName("ResearchPreviewSection")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setObjectName("ResearchPreviewSectionTitle")
        layout.addWidget(title_label)

        return section, layout

    @staticmethod
    def add_value_row(parent_layout, label_text):
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        name_label = QLabel(label_text)
        name_label.setObjectName("ResearchPreviewFieldLabel")
        value_label = QLabel(PerformanceDashboard.MISSING_VALUE)
        value_label.setObjectName("ResearchPreviewFieldValue")

        row_layout.addWidget(name_label, stretch=1)
        row_layout.addWidget(value_label, stretch=1)
        parent_layout.addWidget(row)

        return value_label

    @staticmethod
    def create_table(headers, rows):
        table = QTableWidget(rows, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.NoSelection)
        table.setAlternatingRowColors(True)
        table.setShowGrid(False)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(24)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(True)
        table.setFixedHeight((rows + 1) * 28)
        return table

    @classmethod
    def populate_table(cls, table, rows):
        table.setRowCount(len(rows))

        for row_index, row in enumerate(rows):
            for column, value in enumerate(row):
                table.setItem(row_index, column, QTableWidgetItem(str(value)))

        table.resizeColumnsToContents()
        table.horizontalHeader().setStretchLastSection(True)

    @classmethod
    def first_mapping(cls, source, keys):
        for key in keys:
            value = cls.value_for(source, key)
            if value is not None:
                return value
        return None

    @classmethod
    def first_value(cls, source, keys):
        for key in keys:
            value = cls.value_for(source, key)
            if value is not None:
                return value
        return None

    @staticmethod
    def value_for(source, key):
        if source is None:
            return None

        if isinstance(source, dict):
            return source.get(key)

        return getattr(source, key, None)

    @classmethod
    def format_value(cls, value, percent=False):
        if value is None or value == "":
            return cls.MISSING_VALUE

        if isinstance(value, float):
            text = f"{value:.2f}"
        else:
            text = str(value)

        if percent and text != cls.MISSING_VALUE:
            return f"{text}%"

        return text
