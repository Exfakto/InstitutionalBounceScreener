from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class WatchlistPanel(QWidget):
    """
    Passive watchlist table with simple user actions.
    """

    COLUMNS = [
        "Ticker",
        "Company",
        "Status",
        "Notes",
        "Last",
        "Change",
        "% Change",
        "Last Updated",
        "Added",
    ]

    add_selected_candidate_requested = Signal()
    remove_selected_requested = Signal()
    refresh_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.group = QGroupBox("Watchlist")
        group_layout = QVBoxLayout()
        group_layout.setContentsMargins(12, 16, 12, 12)
        group_layout.setSpacing(10)

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(32)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)

        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(8)

        self.add_button = QPushButton("Add Selected Candidate")
        self.remove_button = QPushButton("Remove Selected")
        self.refresh_button = QPushButton("Refresh")

        self.add_button.clicked.connect(self.add_selected_candidate_requested.emit)
        self.remove_button.clicked.connect(self.remove_selected_requested.emit)
        self.refresh_button.clicked.connect(self.refresh_requested.emit)

        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.remove_button)
        button_layout.addWidget(self.refresh_button)

        group_layout.addWidget(self.table)
        group_layout.addLayout(button_layout)

        self.group.setLayout(group_layout)
        layout.addWidget(self.group)

    def refresh_items(self, items):
        """
        Replace table rows with provided watchlist item dictionaries or rows.
        """

        self.table.setRowCount(0)

        for row_index, item in enumerate(items or []):
            self.table.insertRow(row_index)
            item_id = self.value_for(item, "id")
            values = [
                self.value_for(item, "ticker"),
                self.value_for(item, "company_name"),
                self.value_for(item, "status"),
                self.value_for(item, "notes"),
                self.value_for(item, "last_price"),
                self.value_for(item, "daily_change"),
                self.value_for(item, "percent_change"),
                self.value_for(item, "last_updated"),
                self.value_for(item, "added_at"),
            ]

            for column, value in enumerate(values):
                table_item = QTableWidgetItem(self.format_value(value))
                if column == 0:
                    table_item.setData(Qt.UserRole, item_id)
                self.table.setItem(row_index, column, table_item)

        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)

    def visible_tickers(self):
        tickers = []

        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)

            if item is None:
                continue

            ticker = item.text().strip().upper()

            if ticker:
                tickers.append(ticker)

        return tickers

    def update_quote(self, ticker, quote):
        row = self.row_for_ticker(ticker)

        if row is None:
            return False

        if not quote or not quote.get("success"):
            return False

        values = {
            4: self.format_price(quote.get("last_price")),
            5: self.format_price(quote.get("daily_change"), signed=True),
            6: self.format_percent(quote.get("percent_change")),
            7: self.format_value(quote.get("timestamp")),
        }

        for column, value in values.items():
            table_item = self.table.item(row, column)

            if table_item is None:
                table_item = QTableWidgetItem()
                self.table.setItem(row, column, table_item)

            table_item.setText(value)

        return True

    def update_quotes(self, quotes):
        for ticker, quote in (quotes or {}).items():
            self.update_quote(ticker, quote)

    def row_for_ticker(self, ticker):
        normalized_ticker = str(ticker or "").strip().upper()

        if not normalized_ticker:
            return None

        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)

            if item is not None and item.text().strip().upper() == normalized_ticker:
                return row

        return None

    def selected_item_id(self):
        """
        Return the database id for the selected watchlist row.
        """

        selected_rows = self.table.selectionModel().selectedRows()

        if not selected_rows:
            return None

        ticker_item = self.table.item(selected_rows[0].row(), 0)

        if ticker_item is None:
            return None

        return ticker_item.data(Qt.UserRole)

    def clear(self):
        self.table.setRowCount(0)

    @staticmethod
    def value_for(item, key):
        if item is None:
            return None

        if isinstance(item, dict):
            return item.get(key)

        try:
            return item[key]
        except (KeyError, IndexError, TypeError):
            return getattr(item, key, None)

    @staticmethod
    def format_value(value):
        if value is None:
            return ""

        return str(value)

    @staticmethod
    def format_price(value, signed=False):
        if value is None:
            return ""

        try:
            number = float(value)
        except (TypeError, ValueError):
            return str(value)

        prefix = "+" if signed and number > 0 else ""
        return f"{prefix}{number:.2f}"

    @staticmethod
    def format_percent(value):
        if value is None:
            return ""

        try:
            number = float(value)
        except (TypeError, ValueError):
            return str(value)

        prefix = "+" if number > 0 else ""
        return f"{prefix}{number:.2f}%"
