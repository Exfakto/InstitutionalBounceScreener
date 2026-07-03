from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.design_system import DashboardDesignSystem as DesignSystem


class BacktestAnalyticsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("BacktestAnalyticsPanel")
        self.current_model = None
        self.build_ui()
        self.clear()

    def build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(DesignSystem.Spacing.SM)

        section = QFrame()
        section.setObjectName("ResearchPreviewSection")
        section.setStyleSheet(DesignSystem.card_style())
        section_layout = QVBoxLayout(section)
        section_layout.setContentsMargins(
            DesignSystem.Spacing.MD,
            DesignSystem.Spacing.MD,
            DesignSystem.Spacing.MD,
            DesignSystem.Spacing.MD,
        )
        section_layout.setSpacing(DesignSystem.Spacing.SM)

        title = QLabel("Backtest Analytics")
        title.setObjectName("ResearchPreviewSectionTitle")
        section_layout.addWidget(title)

        self.empty_label = QLabel("No backtest analytics available.")
        self.empty_label.setObjectName("EmptyStateLabel")
        self.empty_label.setAlignment(Qt.AlignCenter)
        section_layout.addWidget(self.empty_label)

        self.content = QWidget()
        grid = QGridLayout(self.content)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(DesignSystem.Spacing.LG)
        grid.setVerticalSpacing(DesignSystem.Spacing.XS)
        self.summary_labels = {}
        for index, (key, title_text) in enumerate(
            [
                ("equity", "Equity Curve"),
                ("drawdown", "Drawdown"),
                ("distribution", "Trade Distribution"),
                ("expectancy", "Expectancy"),
                ("profit_factor", "Profit Factor"),
                ("warnings", "Warnings"),
            ]
        ):
            label = QLabel(title_text)
            label.setObjectName("ResearchPreviewFieldLabel")
            value = QLabel("N/A")
            value.setObjectName("ResearchPreviewFieldValue")
            value.setWordWrap(True)
            value.setTextInteractionFlags(Qt.TextSelectableByMouse)
            grid.addWidget(label, index, 0)
            grid.addWidget(value, index, 1)
            self.summary_labels[key] = value
        section_layout.addWidget(self.content)

        self.winners_table = self.build_table("Top Winners")
        self.losers_table = self.build_table("Top Losers")
        section_layout.addWidget(self.winners_table)
        section_layout.addWidget(self.losers_table)
        layout.addWidget(section)

    def build_table(self, title):
        table = QTableWidget(0, 3)
        table.setObjectName(title.replace(" ", "") + "Table")
        table.setHorizontalHeaderLabels([title, "Return %", "Exit"])
        table.setAlternatingRowColors(True)
        table.setSortingEnabled(True)
        table.verticalHeader().setVisible(False)
        table.setMinimumHeight(96)
        table.setStyleSheet(DesignSystem.table_style())
        return table

    def set_analytics_model(self, model):
        if model is None:
            self.clear()
            return
        self.current_model = model
        summary = model.summary or {}
        self.summary_labels["equity"].setText(
            f"{len(model.equity_curve)} point(s), final {self.display(summary.get('final_equity'))}"
        )
        self.summary_labels["drawdown"].setText(
            f"{len(model.drawdown_curve)} point(s), max {self.display(summary.get('max_drawdown'))}%"
        )
        self.summary_labels["distribution"].setText(
            f"{summary.get('total_trades', 0)} trade(s)"
        )
        self.summary_labels["expectancy"].setText(self.display(summary.get("expectancy")))
        self.summary_labels["profit_factor"].setText(self.display(summary.get("profit_factor")))
        self.summary_labels["warnings"].setText(self.list_text(model.warnings))
        self.populate_trade_table(self.winners_table, model.top_winners)
        self.populate_trade_table(self.losers_table, model.top_losers)
        self.empty_label.hide()
        self.content.show()
        self.winners_table.show()
        self.losers_table.show()

    def clear(self):
        self.current_model = None
        self.empty_label.show()
        self.content.hide()
        self.winners_table.hide()
        self.losers_table.hide()

    @classmethod
    def populate_trade_table(cls, table, trades):
        table.setSortingEnabled(False)
        table.setRowCount(0)
        for row_index, trade in enumerate(trades or []):
            table.insertRow(row_index)
            values = [
                cls.value(trade, "ticker"),
                cls.value(trade, "return_pct"),
                cls.value(trade, "exit_reason"),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(cls.display(value))
                if column == 1:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    item.setData(Qt.UserRole, float(value or 0))
                table.setItem(row_index, column, item)
        table.setSortingEnabled(True)

    @staticmethod
    def value(source, key):
        if isinstance(source, dict):
            return source.get(key)
        return getattr(source, key, None)

    @staticmethod
    def display(value):
        if value in (None, ""):
            return "N/A"
        if isinstance(value, float):
            return f"{value:.2f}"
        return str(value)

    @staticmethod
    def list_text(values):
        if not values:
            return "N/A"
        if isinstance(values, (list, tuple)):
            return "\n".join(str(value) for value in values)
        return str(values)
