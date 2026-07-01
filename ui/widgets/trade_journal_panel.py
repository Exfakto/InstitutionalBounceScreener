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


class TradeJournalPanel(QWidget):
    """
    Passive paper trade journal table with simple action signals.
    """

    COLUMNS = [
        "Ticker",
        "Status",
        "Entry",
        "Stop",
        "Target",
        "Exit",
        "Risk/Reward",
        "Opportunity Rating",
        "Confidence",
    ]

    new_trade_requested = Signal()
    close_trade_requested = Signal()
    delete_trade_requested = Signal()
    refresh_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.group = QGroupBox("Paper Trade Journal")
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

        self.new_button = QPushButton("New Trade")
        self.close_button = QPushButton("Close Trade")
        self.delete_button = QPushButton("Delete Trade")
        self.refresh_button = QPushButton("Refresh")

        self.new_button.clicked.connect(self.new_trade_requested.emit)
        self.close_button.clicked.connect(self.close_trade_requested.emit)
        self.delete_button.clicked.connect(self.delete_trade_requested.emit)
        self.refresh_button.clicked.connect(self.refresh_requested.emit)

        button_layout.addWidget(self.new_button)
        button_layout.addWidget(self.close_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.refresh_button)

        group_layout.addWidget(self.table)
        group_layout.addLayout(button_layout)

        self.group.setLayout(group_layout)
        layout.addWidget(self.group)

    def refresh_trades(self, trades):
        """
        Replace table rows with provided paper trade dictionaries or rows.
        """

        self.table.setRowCount(0)

        for row_index, trade in enumerate(trades or []):
            self.table.insertRow(row_index)
            trade_id = self.value_for(trade, "id")
            values = [
                self.value_for(trade, "ticker"),
                self.value_for(trade, "status"),
                self.value_for(trade, "entry_price"),
                self.value_for(trade, "stop_price"),
                self.value_for(trade, "target_price"),
                self.value_for(trade, "exit_price"),
                self.value_for(trade, "risk_reward"),
                self.value_for(trade, "opportunity_rating"),
                self.value_for(trade, "confidence"),
            ]

            for column, value in enumerate(values):
                table_item = QTableWidgetItem(self.format_value(value))
                if column == 0:
                    table_item.setData(Qt.UserRole, trade_id)
                self.table.setItem(row_index, column, table_item)

        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)

    def selected_trade(self):
        """
        Return the selected trade id, if a row is selected.
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

        if isinstance(value, float):
            return f"{value:.2f}"

        return str(value)
