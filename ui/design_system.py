class DashboardDesignSystem:
    """
    Shared visual tokens for the professional dashboard experience.

    The constants in this module are intentionally framework-light so PySide
    widgets can reuse them without creating dependency cycles.
    """

    class Colors:
        BACKGROUND = "#070D13"
        PANEL = "#0F171F"
        SURFACE = "#141E28"
        ELEVATED = "#1B2A37"
        HEADER = "#0A1118"
        CARD = "#101923"
        BORDER = "#334252"
        BORDER_MUTED = "#22303D"
        BORDER_STRONG = "#3C4D5E"
        TEXT_PRIMARY = "#F3F7FA"
        TEXT_SECONDARY = "#B9C5D1"
        TEXT_MUTED = "#82909F"
        ACCENT = "#5B9DF2"
        ACCENT_SOFT = "#10263A"
        SUCCESS = "#35B779"
        WARNING = "#D6A23A"
        DANGER = "#E05A5A"
        INFO = "#67B7DC"

    class Typography:
        FONT_FAMILY = '"Segoe UI", Arial, sans-serif'
        BASE_PT = 10
        CAPTION_PT = 8
        SMALL_PT = 9
        SECTION_PT = 10
        TITLE_PT = 22
        SUBTITLE_PT = 10
        KPI_PT = 18

    class Spacing:
        XXS = 2
        XS = 4
        SM = 8
        MD = 12
        LG = 16
        XL = 20
        XXL = 24

    class Radius:
        SM = 5
        MD = 7
        LG = 9
        XL = 12

    class Card:
        BACKGROUND = "#101923"
        BORDER = "#2F3E4D"
        RADIUS = 8
        PADDING = 12

    class Table:
        BACKGROUND = "#0F171F"
        ALTERNATE_BACKGROUND = "#141E28"
        HEADER_BACKGROUND = "#0A1118"
        BORDER = "#334252"
        RADIUS = 8
        CELL_PADDING_VERTICAL = 8
        CELL_PADDING_HORIZONTAL = 10
        HEADER_PADDING_VERTICAL = 10
        HEADER_PADDING_HORIZONTAL = 12

    class Status:
        ACTIVE = "#35B779"
        WARNING = "#D6A23A"
        ERROR = "#E05A5A"
        NEUTRAL = "#B9C5D1"
        INFO = "#67B7DC"

    @classmethod
    def card_style(cls):
        return (
            f"background-color: {cls.Card.BACKGROUND};"
            f"border: 1px solid {cls.Card.BORDER};"
            f"border-radius: {cls.Card.RADIUS}px;"
            f"padding: {cls.Card.PADDING}px;"
        )

    @classmethod
    def table_style(cls):
        return f"""
        QTableWidget {{
            background-color: #0F171F;
            alternate-background-color: #141E28;
            border: 1px solid #334252;
            border-radius: {cls.Table.RADIUS}px;
            color: {cls.Colors.TEXT_PRIMARY};
            gridline-color: transparent;
            outline: none;
            selection-background-color: #24537B;
            selection-color: {cls.Colors.TEXT_PRIMARY};
        }}
        QTableWidget::item {{
            padding: 9px 12px;
            border-bottom: 1px solid #22303D;
        }}
        QTableWidget::item:hover {{
            background-color: #1B2A37;
        }}
        QTableWidget::item:selected {{
            background-color: #24537B;
            color: {cls.Colors.TEXT_PRIMARY};
        }}
        QHeaderView::section {{
            background-color: #0A1118;
            color: #AEBCCC;
            border: none;
            border-right: 1px solid #22303D;
            border-bottom: 1px solid #3C4D5E;
            padding: 10px 12px;
            font-weight: 800;
        }}
        QTableCornerButton::section {{
            background-color: #0A1118;
            border: none;
            border-bottom: 1px solid #3C4D5E;
        }}
        """

    @classmethod
    def section_title_style(cls):
        return (
            f"color: {cls.Colors.TEXT_SECONDARY};"
            f"font-size: {cls.Typography.SMALL_PT}pt;"
            "font-weight: 800;"
            "letter-spacing: 0px;"
        )
