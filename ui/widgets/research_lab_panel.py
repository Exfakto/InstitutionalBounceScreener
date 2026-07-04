from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
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

from services.score_calibration_service import ScoreCalibrationService
from services.strategy_validation_analytics_service import (
    StrategyValidationAnalyticsService,
)
from ui.design_system import DashboardDesignSystem as DesignSystem


class ResearchLabPanel(QWidget):
    """
    Read-only research workspace for historical strategy validation analytics.
    """

    def __init__(
        self,
        analytics_service=None,
        calibration_service=None,
        parent=None,
    ):
        super().__init__(parent)
        self.analytics_service = analytics_service or StrategyValidationAnalyticsService()
        self.calibration_service = calibration_service or ScoreCalibrationService()
        self.analytics_report = None
        self.calibration_report = None

        self.setObjectName("ResearchLabPanel")
        self.setMinimumSize(420, 320)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.build_ui()
        self.set_reports(None, None)

    def build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(10)

        title_stack = QVBoxLayout()
        title_stack.setSpacing(2)
        self.title_label = QLabel("Research Lab")
        self.title_label.setObjectName("ResearchLabTitle")
        self.title_label.setStyleSheet(
            f"color: {DesignSystem.Colors.TEXT_PRIMARY};"
            "font-size: 15pt;"
            "font-weight: 800;"
        )
        self.strategy_label = QLabel("Strategy: Institutional Bounce")
        self.strategy_label.setObjectName("ResearchLabStrategy")
        self.strategy_label.setStyleSheet(
            f"color: {DesignSystem.Colors.TEXT_SECONDARY};"
            "font-size: 9pt;"
            "font-weight: 600;"
        )
        title_stack.addWidget(self.title_label)
        title_stack.addWidget(self.strategy_label)

        self.status_label = QLabel("No validation analytics loaded")
        self.status_label.setObjectName("ResearchLabStatusLabel")
        self.status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.status_label.setStyleSheet(
            f"color: {DesignSystem.Colors.TEXT_MUTED};"
            "font-size: 9pt;"
        )

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setObjectName("ResearchLabRefreshButton")
        self.refresh_button.setCursor(Qt.PointingHandCursor)
        self.refresh_button.clicked.connect(self.refresh_lab)

        header.addLayout(title_stack, 1)
        header.addWidget(self.status_label, 1)
        header.addWidget(self.refresh_button)
        root.addLayout(header)

        scroll = QScrollArea()
        scroll.setObjectName("ResearchLabScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        content.setObjectName("ResearchLabContent")
        content_layout = QGridLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setHorizontalSpacing(10)
        content_layout.setVerticalSpacing(10)

        self._sections = []
        self.validation_summary_table = self.create_table(
            "Validation Summary",
            ["Metric", "Value"],
            "ValidationSummaryTable",
        )
        self.calibration_summary_table = self.create_table(
            "Score Calibration Summary",
            ["Rank", "Component", "Power", "20d Corr"],
            "ScoreCalibrationSummaryTable",
        )
        self.historical_performance_table = self.create_table(
            "Historical Performance",
            ["Metric", "Value"],
            "HistoricalPerformanceTable",
        )
        self.forward_returns_table = self.create_table(
            "Forward Returns",
            ["Horizon", "Count", "Average", "Median", "Std Dev", "Best", "Worst"],
            "ForwardReturnsTable",
        )
        self.score_buckets_table = self.create_table(
            "Score Buckets",
            ["Bucket", "Count", "Win Rate", "Avg Return", "Drawdown", "Expectancy"],
            "ScoreBucketsTable",
        )
        self.sector_performance_table = self.create_table(
            "Sector Performance",
            ["Sector", "Count", "Win Rate", "Avg Return", "Drawdown", "Expectancy"],
            "SectorPerformanceTable",
        )
        self.recommendations_table = self.create_table(
            "Calibration Recommendations",
            ["Component", "Action", "Power", "Rationale"],
            "CalibrationRecommendationsTable",
        )
        self.chart_placeholders = self.create_chart_placeholders()

        content_layout.addWidget(self.validation_summary_table.parentWidget(), 0, 0)
        content_layout.addWidget(self.calibration_summary_table.parentWidget(), 0, 1)
        content_layout.addWidget(self.historical_performance_table.parentWidget(), 1, 0)
        content_layout.addWidget(self.forward_returns_table.parentWidget(), 1, 1)
        content_layout.addWidget(self.score_buckets_table.parentWidget(), 2, 0)
        content_layout.addWidget(self.sector_performance_table.parentWidget(), 2, 1)
        content_layout.addWidget(self.recommendations_table.parentWidget(), 3, 0, 1, 2)
        content_layout.addWidget(self.chart_placeholders, 4, 0, 1, 2)
        content_layout.setColumnStretch(0, 1)
        content_layout.setColumnStretch(1, 1)

        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        self.setStyleSheet(
            f"""
            QWidget#ResearchLabPanel {{
                background-color: {DesignSystem.Colors.BACKGROUND};
                color: {DesignSystem.Colors.TEXT_PRIMARY};
            }}
            QFrame#ResearchLabSection {{
                background-color: {DesignSystem.Colors.CARD};
                border: 1px solid {DesignSystem.Colors.BORDER_MUTED};
                border-radius: 8px;
            }}
            QLabel#ResearchLabSectionTitle {{
                color: {DesignSystem.Colors.TEXT_SECONDARY};
                font-size: 9pt;
                font-weight: 800;
            }}
            QPushButton#ResearchLabRefreshButton {{
                background-color: {DesignSystem.Colors.ACCENT_SOFT};
                border: 1px solid {DesignSystem.Colors.BORDER_STRONG};
                border-radius: 6px;
                color: {DesignSystem.Colors.TEXT_PRIMARY};
                font-weight: 700;
                padding: 6px 12px;
            }}
            QPushButton#ResearchLabRefreshButton:hover {{
                background-color: {DesignSystem.Colors.ELEVATED};
            }}
            QScrollArea#ResearchLabScrollArea {{
                background: transparent;
            }}
            """
        )

    def create_table(self, title, headers, object_name):
        section = QFrame()
        section.setObjectName("ResearchLabSection")
        section.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._sections.append(section)

        layout = QVBoxLayout(section)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        label = QLabel(title)
        label.setObjectName("ResearchLabSectionTitle")
        layout.addWidget(label)

        table = QTableWidget(0, len(headers))
        table.setObjectName(object_name)
        table.setHorizontalHeaderLabels(headers)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.NoSelection)
        table.setFocusPolicy(Qt.NoFocus)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setShowGrid(False)
        table.setMinimumHeight(150)
        table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        table.setStyleSheet(DesignSystem.table_style())
        layout.addWidget(table)
        return table

    def create_chart_placeholders(self):
        section = QFrame()
        section.setObjectName("ResearchLabSection")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QLabel("Charts")
        title.setObjectName("ResearchLabSectionTitle")
        layout.addWidget(title)

        row = QHBoxLayout()
        row.setSpacing(8)
        for object_name, text in (
            ("ForwardReturnDistributionPlaceholder", "Forward Return Distribution"),
            ("ScoreDistributionPlaceholder", "Score Distribution"),
            ("DrawdownDistributionPlaceholder", "Drawdown Distribution"),
        ):
            label = QLabel(text)
            label.setObjectName(object_name)
            label.setAlignment(Qt.AlignCenter)
            label.setMinimumHeight(92)
            label.setStyleSheet(
                f"background-color: {DesignSystem.Colors.SURFACE};"
                f"border: 1px dashed {DesignSystem.Colors.BORDER};"
                "border-radius: 7px;"
                f"color: {DesignSystem.Colors.TEXT_MUTED};"
                "font-weight: 700;"
            )
            row.addWidget(label, 1)
        layout.addLayout(row)
        return section

    def refresh_lab(self, run_id=None):
        try:
            analytics_report = self.analytics_service.analyze(run_id=run_id)
            calibration_report = self.calibration_service.calibrate(run_id=run_id)
        except Exception as exc:  # pragma: no cover - defensive UI boundary
            self.set_error(str(exc))
            return
        self.set_reports(analytics_report, calibration_report)

    def set_reports(self, analytics_report=None, calibration_report=None):
        self.analytics_report = analytics_report
        self.calibration_report = calibration_report
        self.populate_analytics(analytics_report)
        self.populate_calibration(calibration_report)
        if analytics_report is None and calibration_report is None:
            self.status_label.setText("No validation analytics loaded")
        else:
            completed = self.value(getattr(analytics_report, "overall", None), "completed_samples")
            self.status_label.setText(f"{completed or 0} completed samples")

    def set_error(self, message):
        self.clear_tables()
        self.status_label.setText(f"Research data unavailable: {message}")

    def clear_tables(self):
        for table in (
            self.validation_summary_table,
            self.calibration_summary_table,
            self.historical_performance_table,
            self.forward_returns_table,
            self.score_buckets_table,
            self.sector_performance_table,
            self.recommendations_table,
        ):
            table.setRowCount(0)

    def populate_analytics(self, report):
        overall = getattr(report, "overall", None)
        self.set_table_rows(
            self.validation_summary_table,
            [
                ("Total Samples", self.format_int(self.value(overall, "total_samples"))),
                ("Completed Samples", self.format_int(self.value(overall, "completed_samples"))),
                ("Win Rate", self.format_percent(self.value(overall, "win_rate"))),
                ("Average Return", self.format_return(self.value(overall, "average_return"))),
                ("Drawdown", self.format_return(self.value(overall, "average_drawdown"))),
                ("Profit Factor", self.format_number(self.value(overall, "profit_factor"))),
            ],
        )
        self.set_table_rows(
            self.historical_performance_table,
            [
                ("Median Return", self.format_return(self.value(overall, "median_return"))),
                ("Average Max Gain", self.format_return(self.value(overall, "average_max_gain"))),
                ("Average Drawdown", self.format_return(self.value(overall, "average_drawdown"))),
                ("Expectancy", self.format_return(self.value(overall, "expectancy"))),
            ],
        )
        self.set_table_rows(
            self.forward_returns_table,
            [
                (
                    self.value(summary, "horizon") or horizon,
                    self.format_int(self.value(summary, "count")),
                    self.format_return(self.value(summary, "average")),
                    self.format_return(self.value(summary, "median")),
                    self.format_return(self.value(summary, "std_deviation")),
                    self.format_return(self.value(summary, "best")),
                    self.format_return(self.value(summary, "worst")),
                )
                for horizon, summary in self.sorted_items(getattr(report, "forward_returns", {}))
            ],
        )
        self.set_group_rows(
            self.score_buckets_table,
            getattr(report, "score_buckets", {}),
        )
        self.set_group_rows(
            self.sector_performance_table,
            getattr(report, "sector_performance", {}),
        )

    def populate_calibration(self, report):
        ranked_components = list(getattr(report, "ranked_components", []) or [])
        self.set_table_rows(
            self.calibration_summary_table,
            [
                (
                    self.format_int(self.value(metric, "rank")),
                    self.display_component(self.value(metric, "component")),
                    self.format_number(self.value(metric, "predictive_power")),
                    self.format_correlation(
                        (self.value(metric, "correlations") or {}).get("20d")
                    ),
                )
                for metric in ranked_components[:6]
            ],
        )
        self.set_table_rows(
            self.recommendations_table,
            [
                (
                    self.display_component(self.value(recommendation, "component")),
                    str(self.value(recommendation, "action") or "--").title(),
                    self.format_number(self.value(recommendation, "predictive_power")),
                    self.value(recommendation, "rationale") or "--",
                )
                for recommendation in (getattr(report, "recommendations", []) or [])
            ],
        )

    def set_group_rows(self, table, groups):
        self.set_table_rows(
            table,
            [
                (
                    self.value(summary, "label") or label,
                    self.format_int(self.value(summary, "count")),
                    self.format_percent(self.value(summary, "win_rate")),
                    self.format_return(self.value(summary, "average_return")),
                    self.format_return(self.value(summary, "drawdown")),
                    self.format_return(self.value(summary, "expectancy")),
                )
                for label, summary in self.sorted_items(groups)
            ],
        )

    def set_table_rows(self, table, rows):
        rows = list(rows or [])
        table.setRowCount(len(rows))
        for row_index, row_values in enumerate(rows):
            for column_index, value in enumerate(row_values):
                item = QTableWidgetItem(str(value))
                if column_index > 0:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                else:
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                table.setItem(row_index, column_index, item)
        table.resizeRowsToContents()

    @staticmethod
    def sorted_items(mapping):
        if not mapping:
            return []
        preferred = {"5d": 0, "10d": 1, "20d": 2, "60d": 3}
        return sorted(
            mapping.items(),
            key=lambda item: preferred.get(str(item[0]).lower(), 100),
        )

    @staticmethod
    def value(source, key):
        if source is None:
            return None
        if isinstance(source, dict):
            return source.get(key)
        return getattr(source, key, None)

    @staticmethod
    def format_int(value):
        try:
            return f"{int(value):,}"
        except (TypeError, ValueError):
            return "0"

    @staticmethod
    def format_number(value):
        try:
            return f"{float(value):.2f}"
        except (TypeError, ValueError):
            return "--"

    @staticmethod
    def format_percent(value):
        try:
            return f"{float(value) * 100:.1f}%"
        except (TypeError, ValueError):
            return "--"

    @staticmethod
    def format_return(value):
        try:
            number = float(value)
        except (TypeError, ValueError):
            return "--"
        return f"{number:+.2f}%"

    @staticmethod
    def format_correlation(value):
        try:
            return f"{float(value):+.2f}"
        except (TypeError, ValueError):
            return "--"

    @staticmethod
    def display_component(component):
        if not component:
            return "--"
        return str(component).replace("_", " ").title()
