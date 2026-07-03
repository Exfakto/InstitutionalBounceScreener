class DashboardDesignSystem:
    """
    Shared visual tokens for the professional dashboard experience.

    The constants in this module are intentionally framework-light so PySide
    widgets can reuse them without creating dependency cycles.
    """

    class Colors:
        BACKGROUND = "#0B1117"
        PANEL = "#141B23"
        SURFACE = "#1A232D"
        ELEVATED = "#202B36"
        HEADER = "#111922"
        CARD = "#18212A"
        BORDER = "#3A4654"
        BORDER_MUTED = "#273340"
        BORDER_STRONG = "#4A5868"
        TEXT_PRIMARY = "#F3F7FA"
        TEXT_SECONDARY = "#B9C5D1"
        TEXT_MUTED = "#82909F"
        ACCENT = "#5B9DF2"
        ACCENT_SOFT = "#1D3A58"
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
        BACKGROUND = "#18212A"
        BORDER = "#3A4654"
        RADIUS = 9
        PADDING = 12

    class Table:
        BACKGROUND = "#141B23"
        ALTERNATE_BACKGROUND = "#1A232D"
        HEADER_BACKGROUND = "#111922"
        BORDER = "#3A4654"
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
        return (
            f"background-color: {cls.Table.BACKGROUND};"
            f"alternate-background-color: {cls.Table.ALTERNATE_BACKGROUND};"
            f"border: 1px solid {cls.Table.BORDER};"
            f"border-radius: {cls.Table.RADIUS}px;"
            f"color: {cls.Colors.TEXT_PRIMARY};"
            "gridline-color: transparent;"
        )

    @classmethod
    def section_title_style(cls):
        return (
            f"color: {cls.Colors.TEXT_SECONDARY};"
            f"font-size: {cls.Typography.SMALL_PT}pt;"
            "font-weight: 800;"
            "letter-spacing: 0px;"
        )
