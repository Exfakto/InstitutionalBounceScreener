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

    COLUMNS = ["Ticker", "Company", "Status", "Notes", "Added"]

    add_selected_candidate_requested = Signal()
    remove_selected_requested = Signal()
    refresh_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.group = QGroupBox("Watchlist")
        group_layout = QVBoxLayout()
        group_layout.setContentsMargins(10, 14, 10, 10)
        group_layout.setSpacing(8)

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(30)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)

        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(6)

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
                self.value_for(item, "added_at"),
            ]

            for column, value in enumerate(values):
                table_item = QTableWidgetItem(self.format_value(value))
                if column == 0:
                    table_item.setData(Qt.UserRole, item_id)
                self.table.setItem(row_index, column, table_item)

        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)

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
