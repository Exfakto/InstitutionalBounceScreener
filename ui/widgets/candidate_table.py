from PySide6.QtCore import Signal
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
        "Quality",
        "Institutional",
        "Technical",
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
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(36)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setMinimumSectionSize(104)
        self.cellDoubleClicked.connect(self.emit_double_clicked_ticker)

    def populate(self, candidates):
        """
        Populate table rows from CandidateScore objects.
        """

        self.setRowCount(0)

        for row, candidate in enumerate(self.sorted_candidates(candidates)):
            self.insertRow(row)

            for column, value in enumerate(self.row_values(candidate)):
                self.setItem(row, column, QTableWidgetItem(value))

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
        scores = candidate.score_map

        return [
            candidate.ticker,
            self.format_score(candidate.primary_score_value),
            self.format_score(scores.get("quality_score")),
            self.format_score(scores.get("institutional_score")),
            self.format_score(scores.get("technical_score")),
            self.format_score(scores.get("support_score")),
            self.format_score(scores.get("bounce_score")),
        ]

    @classmethod
    def sorted_candidates(cls, candidates):
        return sorted(
            candidates,
            key=lambda candidate: candidate.primary_score_value,
            reverse=True,
        )

    @staticmethod
    def format_score(score):
        if score is None:
            return "0.0"

        if hasattr(score, "value"):
            return f"{score.value:.1f}"

        return f"{float(score):.1f}"
