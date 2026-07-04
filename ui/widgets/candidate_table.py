from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
)

from ui.design_system import DashboardDesignSystem as DesignSystem
from ui.widgets.ticker_logo import TickerLogoProvider


class CandidateTable(QTableWidget):
    """
    Read-only ranked candidate table.
    """

    COLUMNS = [
        "Rank",
        "Ticker",
        "Overall Score",
        "Signal",
        "Quality",
        "Institutional",
        "Technical",
        "Support",
        "Bounce",
        "Distance to Support",
        "Support Strength",
        "Last Bounce",
        "Detail",
    ]

    ticker_double_clicked = Signal(str)
    detail_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(0, len(self.COLUMNS), parent)

        self._display_candidates = []
        self._populating = False
        self._sort_column = 2
        self._sort_order = Qt.DescendingOrder
        self.setObjectName("CandidateTable")
        self.setHorizontalHeaderLabels(self.COLUMNS)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.setMouseTracking(True)
        self.setIconSize(QSize(32, 32))
        self.setSortingEnabled(False)
        self.setWordWrap(False)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(46)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setMinimumSectionSize(104)
        self.horizontalHeader().setSectionsClickable(True)
        self.horizontalHeader().sectionClicked.connect(self.handle_header_sort)
        self.apply_default_column_widths()
        self.setStyleSheet(self.grid_style())
        self.cellDoubleClicked.connect(self.emit_double_clicked_ticker)
        self.cellClicked.connect(self.emit_detail_requested)

    def isSortingEnabled(self):
        return True

    def populate(self, candidates):
        """
        Populate table rows from CandidateScore objects.
        """

        self._display_candidates = self.sorted_candidates(candidates)
        self._populate_rows(self._display_candidates)

    def _populate_rows(self, candidates):
        self._populating = True
        self.setSortingEnabled(False)
        self.setRowCount(0)

        for row, candidate in enumerate(candidates or []):
            self.insertRow(row)

            for column, (value, role) in enumerate(self.row_values(candidate, row)):
                item = QTableWidgetItem(value)
                sort_value = self.sort_value_for_column(candidate, column)
                if column == 0:
                    sort_value = row + 1
                if sort_value is not None:
                    item.setData(Qt.UserRole, sort_value)
                item.setTextAlignment(self.alignment_for_column(column))
                if column == 1:
                    item.setIcon(TickerLogoProvider.icon_for(value, size=32))
                self.apply_item_style(item, role)
                self.setItem(row, column, item)

        self.apply_default_column_widths()
        self.horizontalHeader().setStretchLastSection(True)
        self._populating = False

    def handle_header_sort(self, column):
        if column == self._sort_column and self._sort_order == Qt.AscendingOrder:
            order = Qt.DescendingOrder
        else:
            order = Qt.AscendingOrder
        self.sortItems(column, order)

    def sortItems(self, column, order=Qt.AscendingOrder):
        if self._populating:
            return

        self._sort_column = column
        self._sort_order = order
        reverse = order == Qt.DescendingOrder

        def key(candidate):
            sort_value = self.sort_value_for_column(candidate, column)
            if sort_value is not None:
                return (0, sort_value)
            display = self.row_values(candidate)[column][0]
            return (1, str(display or "").lower())

        self._display_candidates = sorted(
            self._display_candidates,
            key=key,
            reverse=reverse,
        )
        self._populate_rows(self._display_candidates)
        self.horizontalHeader().setSortIndicator(column, order)

    def selected_ticker(self):
        """
        Return the selected ticker, if one is selected.
        """

        selected_rows = self.selectionModel().selectedRows()

        if not selected_rows:
            return None

        ticker_item = self.item(selected_rows[0].row(), 1)

        if ticker_item is None:
            return None

        return ticker_item.text()

    def ticker_at_row(self, row):
        """
        Return the ticker displayed at a row.
        """

        ticker_item = self.item(row, 1)

        if ticker_item is None:
            return None

        return ticker_item.text()

    def emit_double_clicked_ticker(self, row, column):
        """
        Emit the ticker for the double-clicked row.
        """

        ticker = self.ticker_at_row(row)

        if ticker is not None:
            self.ticker_double_clicked.emit(ticker)

    def emit_detail_requested(self, row, column):
        """
        Emit the ticker when the detail action column is clicked.
        """

        if column != len(self.COLUMNS) - 1:
            return

        ticker = self.ticker_at_row(row)

        if ticker is not None:
            self.detail_requested.emit(ticker)

    def row_values(self, candidate, row=None):
        scores = getattr(candidate, "score_map", {}) or {}
        metrics = getattr(candidate, "metrics", {}) or {}
        overall = self.number_value(getattr(candidate, "primary_score_value", None))
        signal = self.opportunity_display(candidate, overall)
        distance_to_support = self.first_existing(
            metrics.get("distance_to_support"),
            metrics.get("distance_from_support"),
            metrics.get("support_distance"),
            getattr(candidate, "distance_to_support", None),
            getattr(candidate, "distance_from_support", None),
        )
        support_strength = self.first_existing(
            metrics.get("support_strength"),
            metrics.get("strength_score"),
            getattr(candidate, "support_strength", None),
        )
        last_bounce = self.first_existing(
            metrics.get("last_bounce"),
            metrics.get("last_bounce_date"),
            getattr(candidate, "last_bounce", None),
            getattr(candidate, "last_bounce_date", None),
        )

        return [
            (str((row or 0) + 1), "rank"),
            (str(getattr(candidate, "ticker", "--") or "--"), "text"),
            (self.format_score(overall), self.score_role(overall)),
            (signal, self.opportunity_role(signal, overall)),
            (self.format_score(scores.get("quality_score")), self.score_role(scores.get("quality_score"))),
            (self.format_score(scores.get("institutional_score")), self.score_role(scores.get("institutional_score"))),
            (self.format_score(scores.get("technical_score")), self.score_role(scores.get("technical_score"))),
            (self.format_score(scores.get("support_score")), self.score_role(scores.get("support_score"))),
            (self.format_score(scores.get("bounce_score")), self.score_role(scores.get("bounce_score"))),
            (self.format_percent(distance_to_support), self.distance_role(distance_to_support)),
            (self.format_score(support_strength), self.score_role(support_strength)),
            (self.format_text(last_bounce), "text" if last_bounce else "missing"),
            ("View", "detail"),
        ]

    @classmethod
    def sort_value_for_column(cls, candidate, column):
        scores = getattr(candidate, "score_map", {}) or {}
        metrics = getattr(candidate, "metrics", {}) or {}

        if column == 0:
            return None
        if column == 1:
            return None
        if column == 2:
            return cls.number_value(getattr(candidate, "primary_score_value", None))
        if column == 3:
            opportunity = getattr(candidate, "opportunity_rating", None)
            return cls.number_value(
                cls.first_existing(
                    cls.object_value(opportunity, "rating_score"),
                    getattr(candidate, "primary_score_value", None),
                )
            )
        if column == 4:
            return cls.number_value(scores.get("quality_score"))
        if column == 5:
            return cls.number_value(scores.get("institutional_score"))
        if column == 6:
            return cls.number_value(scores.get("technical_score"))
        if column == 7:
            return cls.number_value(scores.get("support_score"))
        if column == 8:
            return cls.number_value(scores.get("bounce_score"))
        if column == 9:
            return cls.number_value(
                cls.first_existing(
                    metrics.get("distance_to_support"),
                    metrics.get("distance_from_support"),
                    metrics.get("support_distance"),
                    getattr(candidate, "distance_to_support", None),
                    getattr(candidate, "distance_from_support", None),
                )
            )
        if column == 10:
            return cls.number_value(
                cls.first_existing(
                    metrics.get("support_strength"),
                    metrics.get("strength_score"),
                    getattr(candidate, "support_strength", None),
                )
            )
        return None

    @classmethod
    def sorted_candidates(cls, candidates):
        return sorted(
            candidates or [],
            key=lambda candidate: cls.number_value(
                getattr(candidate, "primary_score_value", None)
            ) or 0.0,
            reverse=True,
        )

    @classmethod
    def format_score(cls, score):
        value = cls.number_value(score)

        if value is None:
            return "N/A"

        return f"{value:.1f}"

    @classmethod
    def format_risk_reward(cls, value):
        number = cls.number_value(value)

        if number is None:
            return "N/A"

        return f"{number:.2f}:1"

    @classmethod
    def format_percent(cls, value):
        number = cls.number_value(value)

        if number is None:
            return "N/A"

        return f"{number:.1f}%"

    @staticmethod
    def format_text(value):
        if value in (None, ""):
            return "N/A"
        return str(value)

    @classmethod
    def opportunity_display(cls, candidate, overall):
        opportunity = getattr(candidate, "opportunity_rating", None)
        label = cls.object_value(opportunity, "rating_label")
        score = cls.number_value(cls.object_value(opportunity, "rating_score"))

        if label and score is not None:
            return f"{label} {score:.1f}"
        if label:
            return str(label)
        if overall is not None:
            return cls.setup_badge(overall)
        return "N/A"

    @staticmethod
    def setup_badge(score):
        if score >= 85:
            return "High Conviction"
        if score >= 70:
            return "Watch"
        if score >= 55:
            return "Developing"
        return "Avoid"

    @classmethod
    def confidence_display(cls, candidate):
        thesis = getattr(candidate, "trade_thesis", None)
        confidence = cls.object_value(thesis, "confidence")

        if confidence:
            return str(confidence)

        metrics = getattr(candidate, "metrics", {}) or {}
        confidence = metrics.get("confidence")
        return str(confidence) if confidence else "N/A"

    @classmethod
    def score_role(cls, score):
        value = cls.number_value(score)

        if value is None:
            return "missing"
        if value >= 80:
            return "positive"
        if value >= 60:
            return "watch"
        return "negative"

    @classmethod
    def opportunity_role(cls, text, score):
        normalized = str(text or "").lower()

        if "avoid" in normalized or "weak" in normalized:
            return "negative"
        if "watch" in normalized or "developing" in normalized:
            return "watch"
        if "high" in normalized or "elite" in normalized or "conviction" in normalized:
            return "positive"
        return cls.score_role(score)

    @classmethod
    def risk_reward_role(cls, value):
        number = cls.number_value(value)

        if number is None:
            return "missing"
        if number >= 2.0:
            return "positive"
        if number >= 1.2:
            return "watch"
        return "negative"

    @staticmethod
    def confidence_role(confidence):
        normalized = str(confidence or "").lower()

        if normalized in {"very high", "high"}:
            return "positive"
        if normalized in {"moderate", "medium"}:
            return "watch"
        if normalized in {"--", "n/a"}:
            return "missing"
        return "negative"

    @classmethod
    def distance_role(cls, value):
        number = cls.number_value(value)

        if number is None:
            return "missing"
        if abs(number) <= 3:
            return "positive"
        if abs(number) <= 8:
            return "watch"
        return "negative"

    @staticmethod
    def first_existing(*values):
        for value in values:
            if value not in (None, ""):
                return value
        return None

    @staticmethod
    def object_value(source, name):
        if source is None:
            return None
        if isinstance(source, dict):
            return source.get(name)
        return getattr(source, name, None)

    @staticmethod
    def number_value(value):
        if hasattr(value, "value"):
            value = value.value

        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def alignment_for_column(column):
        if column in {0, 3, 12}:
            return Qt.AlignCenter
        if column in {1, 11}:
            return Qt.AlignLeft | Qt.AlignVCenter
        return Qt.AlignRight | Qt.AlignVCenter

    def apply_default_column_widths(self):
        widths = {
            0: 68,
            1: 136,
            2: 126,
            3: 148,
            4: 104,
            5: 122,
            6: 108,
            7: 104,
            8: 104,
            9: 144,
            10: 132,
            11: 116,
            12: 92,
        }

        for column, width in widths.items():
            self.setColumnWidth(column, width)

    @staticmethod
    def apply_item_style(item, role):
        colors = {
            "positive": QColor(DesignSystem.Colors.SUCCESS),
            "watch": QColor(DesignSystem.Colors.WARNING),
            "negative": QColor(DesignSystem.Colors.DANGER),
            "missing": QColor(DesignSystem.Colors.TEXT_MUTED),
            "text": QColor(DesignSystem.Colors.TEXT_PRIMARY),
            "rank": QColor(DesignSystem.Colors.TEXT_SECONDARY),
            "detail": QColor(DesignSystem.Colors.ACCENT),
        }
        item.setForeground(colors.get(role, colors["text"]))

        if role in {"positive", "watch", "negative", "detail"}:
            font = item.font()
            font.setBold(True)
            item.setFont(font)

        if role == "positive":
            item.setBackground(QColor("#13261F"))
        elif role == "watch":
            item.setBackground(QColor("#2A2314"))
        elif role == "negative":
            item.setBackground(QColor("#2A1719"))

    @staticmethod
    def grid_style():
        return """
        QTableWidget#CandidateTable {
            border: 1px solid #3A4654;
            border-radius: 8px;
            background-color: #111922;
            alternate-background-color: #16212B;
            selection-background-color: #1E4970;
            selection-color: #F3F7FA;
            gridline-color: transparent;
            outline: none;
            color: #F3F7FA;
        }
        QTableWidget#CandidateTable::item {
            padding: 8px 12px;
            border-bottom: 1px solid #243140;
        }
        QTableWidget#CandidateTable::item:hover {
            background-color: #1D2A36;
        }
        QTableWidget#CandidateTable::item:selected {
            background-color: #1E4970;
            color: #F3F7FA;
        }
        QHeaderView::section {
            background-color: #0E151D;
            color: #D7E0EA;
            border: none;
            border-right: 1px solid #243140;
            border-bottom: 1px solid #3A4654;
            padding: 9px 12px;
            font-weight: 800;
        }
        """
