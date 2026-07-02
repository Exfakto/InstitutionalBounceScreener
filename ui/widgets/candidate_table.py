from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
)


class CandidateTable(QTableWidget):
    """
    Read-only ranked candidate table.
    """

    COLUMNS = [
        "Ticker",
        "Overall (Gen 2)",
        "Opportunity",
        "Quality",
        "Technical",
        "Institutional",
        "Risk/Reward",
        "Confidence",
        "Support",
        "Bounce",
    ]

    ticker_double_clicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(0, len(self.COLUMNS), parent)

        self.setObjectName("CandidateTable")
        self.setHorizontalHeaderLabels(self.COLUMNS)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.setMouseTracking(True)
        self.setSortingEnabled(False)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(38)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setMinimumSectionSize(104)
        self.setStyleSheet(self.grid_style())
        self.cellDoubleClicked.connect(self.emit_double_clicked_ticker)

    def populate(self, candidates):
        """
        Populate table rows from CandidateScore objects.
        """

        self.setRowCount(0)

        for row, candidate in enumerate(self.sorted_candidates(candidates)):
            self.insertRow(row)

            for column, (value, role) in enumerate(self.row_values(candidate)):
                item = QTableWidgetItem(value)
                item.setTextAlignment(self.alignment_for_column(column))
                self.apply_item_style(item, role)
                self.setItem(row, column, item)

        self.resizeColumnsToContents()
        self.horizontalHeader().setStretchLastSection(True)

    def selected_ticker(self):
        """
        Return the selected ticker, if one is selected.
        """

        selected_rows = self.selectionModel().selectedRows()

        if not selected_rows:
            return None

        ticker_item = self.item(selected_rows[0].row(), 0)

        if ticker_item is None:
            return None

        return ticker_item.text()

    def ticker_at_row(self, row):
        """
        Return the ticker displayed at a row.
        """

        ticker_item = self.item(row, 0)

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

    def row_values(self, candidate):
        scores = getattr(candidate, "score_map", {}) or {}
        metrics = getattr(candidate, "metrics", {}) or {}
        overall = self.number_value(getattr(candidate, "primary_score_value", None))
        opportunity = self.opportunity_display(candidate, overall)
        risk_reward = self.first_existing(
            metrics.get("risk_reward"),
            getattr(candidate, "risk_reward", None),
        )
        confidence = self.confidence_display(candidate)

        return [
            (str(getattr(candidate, "ticker", "--") or "--"), "text"),
            (self.format_score(overall), self.score_role(overall)),
            (opportunity, self.opportunity_role(opportunity, overall)),
            (self.format_score(scores.get("quality_score")), self.score_role(scores.get("quality_score"))),
            (self.format_score(scores.get("technical_score")), self.score_role(scores.get("technical_score"))),
            (self.format_score(scores.get("institutional_score")), self.score_role(scores.get("institutional_score"))),
            (self.format_risk_reward(risk_reward), self.risk_reward_role(risk_reward)),
            (confidence, self.confidence_role(confidence)),
            (self.format_score(scores.get("support_score")), self.score_role(scores.get("support_score"))),
            (self.format_score(scores.get("bounce_score")), self.score_role(scores.get("bounce_score"))),
        ]

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
            return "--"

        return f"{value:.1f}"

    @classmethod
    def format_risk_reward(cls, value):
        number = cls.number_value(value)

        if number is None:
            return "--"

        return f"{number:.2f}:1"

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
        return "--"

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
        return str(confidence) if confidence else "--"

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
        if normalized == "--":
            return "missing"
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
        if column == 0:
            return Qt.AlignLeft | Qt.AlignVCenter
        if column == 2:
            return Qt.AlignCenter
        return Qt.AlignRight | Qt.AlignVCenter

    @staticmethod
    def apply_item_style(item, role):
        colors = {
            "positive": QColor("#35B779"),
            "watch": QColor("#D6A23A"),
            "negative": QColor("#E05A5A"),
            "missing": QColor("#7F8C99"),
            "text": QColor("#F4F7FA"),
        }
        item.setForeground(colors.get(role, colors["text"]))

        if role in {"positive", "watch", "negative"}:
            font = item.font()
            font.setBold(True)
            item.setFont(font)

    @staticmethod
    def grid_style():
        return """
        QTableWidget#CandidateTable {
            border: 1px solid #34404D;
            border-radius: 8px;
            background-color: #171D24;
            alternate-background-color: #1B232C;
            selection-background-color: #1E3A56;
            selection-color: #F4F7FA;
            gridline-color: transparent;
        }
        QTableWidget#CandidateTable::item {
            padding: 8px 10px;
            border-bottom: 1px solid #26313B;
        }
        QTableWidget#CandidateTable::item:hover {
            background-color: #202833;
        }
        QTableWidget#CandidateTable::item:selected {
            background-color: #1E3A56;
            color: #F4F7FA;
        }
        QHeaderView::section {
            background-color: #151C24;
            color: #B9C4D0;
            border: none;
            border-right: 1px solid #26313B;
            border-bottom: 1px solid #34404D;
            padding: 9px 10px;
            font-weight: 700;
        }
        """
