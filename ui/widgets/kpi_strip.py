from PySide6.QtWidgets import QHBoxLayout, QWidget

from ui.design_system import DashboardDesignSystem as DesignSystem
from ui.widgets.statistics_card import StatisticsCard


class KpiStrip(QWidget):
    """
    Compact strip of dashboard KPI cards.
    """

    CARD_DEFINITIONS = [
        {
            "key": "stocks",
            "title": "Universe Stocks",
            "subtitle": "Active market universe",
            "icon": "UNV",
            "accent": DesignSystem.Colors.INFO,
        },
        {
            "key": "rows",
            "title": "Price Records",
            "subtitle": "Historical OHLCV rows",
            "icon": "PX",
            "accent": DesignSystem.Colors.ACCENT,
        },
        {
            "key": "indicator_rows",
            "title": "Indicator Rows",
            "subtitle": "Calculated technical data",
            "icon": "SMA",
            "accent": DesignSystem.Colors.WARNING,
        },
        {
            "key": "support_levels",
            "title": "Support Zones",
            "subtitle": "Detected institutional zones",
            "icon": "SUP",
            "accent": DesignSystem.Colors.SUCCESS,
        },
        {
            "key": "validated_zones",
            "title": "Validated Zones",
            "subtitle": "Bounce-tested support",
            "icon": "VAL",
            "accent": DesignSystem.Colors.SUCCESS,
        },
        {
            "key": "candidates",
            "title": "Candidates",
            "subtitle": "Current screen results",
            "icon": "IB",
            "accent": DesignSystem.Colors.ACCENT,
        },
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("KpiStrip")

        self.cards = {}

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(DesignSystem.Spacing.MD)

        for definition in self.CARD_DEFINITIONS:
            key = definition["key"]
            card = StatisticsCard(
                definition["title"],
                subtitle=definition["subtitle"],
                icon_text=definition["icon"],
                accent_color=definition["accent"],
            )
            card.setObjectName("KpiCard")
            card.setMaximumHeight(126)
            card.setMinimumHeight(106)
            card.setMinimumWidth(180)
            card.title.setObjectName("KpiTitle")
            card.value.setObjectName("KpiValue")

            title_font = card.title.font()
            title_font.setPointSize(DesignSystem.Typography.SMALL_PT)
            title_font.setBold(True)
            card.title.setFont(title_font)

            value_font = card.value.font()
            value_font.setPointSize(DesignSystem.Typography.KPI_PT)
            value_font.setBold(True)
            card.value.setFont(value_font)

            self.cards[key] = card
            layout.addWidget(card)

        layout.addStretch()

    def update_statistics(self, stats):
        """
        Update KPI card values from dashboard statistics.
        """

        self.cards["stocks"].set_value(self.format_count(stats.get("stocks", 0)))
        self.cards["rows"].set_value(self.format_count(stats.get("rows", 0)))
        self.cards["indicator_rows"].set_value(
            self.format_count(stats.get("indicator_rows", 0))
        )
        self.cards["support_levels"].set_value(
            self.format_count(stats.get("support_levels", 0))
        )
        self.cards["validated_zones"].set_value(
            self.format_count(stats.get("validated_zones", 0))
        )
        self.cards["candidates"].set_value(self.format_count(stats.get("candidates", 0)))

    def value_for(self, key):
        """
        Return the displayed value for tests and simple callers.
        """

        return self.cards[key].value.text()

    @staticmethod
    def format_count(value):
        if value in (None, ""):
            return "0"

        try:
            return f"{int(value):,}"
        except (TypeError, ValueError):
            return str(value)
