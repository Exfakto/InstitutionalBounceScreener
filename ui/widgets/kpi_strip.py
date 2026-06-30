from PySide6.QtWidgets import QHBoxLayout, QWidget

from ui.widgets.statistics_card import StatisticsCard


class KpiStrip(QWidget):
    """
    Compact strip of dashboard KPI cards.
    """

    CARD_DEFINITIONS = [
        ("stocks", "Universe Stocks"),
        ("rows", "Price Records"),
        ("indicator_rows", "Indicator Rows"),
        ("support_levels", "Support Zones"),
        ("validated_zones", "Validated Zones"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)

        self.cards = {}

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        for key, title in self.CARD_DEFINITIONS:
            card = StatisticsCard(title)
            card.setMaximumHeight(76)
            card.setMinimumWidth(140)

            self.cards[key] = card
            layout.addWidget(card)

        layout.addStretch()

    def update_statistics(self, stats):
        """
        Update KPI card values from dashboard statistics.
        """

        self.cards["stocks"].set_value(stats["stocks"])
        self.cards["rows"].set_value(f'{stats["rows"]:,}')
        self.cards["indicator_rows"].set_value(f'{stats["indicator_rows"]:,}')
        self.cards["support_levels"].set_value(f'{stats["support_levels"]:,}')
        self.cards["validated_zones"].set_value(f'{stats["validated_zones"]:,}')

    def value_for(self, key):
        """
        Return the displayed value for tests and simple callers.
        """

        return self.cards[key].value.text()
