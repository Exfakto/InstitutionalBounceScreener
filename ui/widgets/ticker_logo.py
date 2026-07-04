from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPixmap


class TickerLogoProvider:
    """
    Local-first ticker logo provider with deterministic badge fallback.
    """

    KNOWN_TICKERS = {
        "AAPL": ("A", "#8B5CF6"),
        "TSLA": ("T", "#EF4444"),
        "AMZN": ("A", "#F59E0B"),
        "NVDA": ("N", "#22C55E"),
        "GOOGL": ("G", "#38BDF8"),
        "META": ("M", "#60A5FA"),
        "MSFT": ("M", "#10B981"),
    }

    LOGO_DIR = Path(__file__).resolve().parent.parent / "assets" / "logos"
    EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")
    _cache = {}

    @classmethod
    def icon_for(cls, ticker, size=24):
        normalized = cls.normalized_ticker(ticker)
        cache_key = (normalized, size)
        if cache_key in cls._cache:
            return cls._cache[cache_key]

        icon = cls.file_icon(normalized)
        if icon is None:
            icon = QIcon(cls.badge_pixmap(normalized, size))

        cls._cache[cache_key] = icon
        return icon

    @classmethod
    def file_icon(cls, ticker):
        if not ticker:
            return None

        for extension in cls.EXTENSIONS:
            path = cls.LOGO_DIR / f"{ticker.lower()}{extension}"
            if path.exists():
                icon = QIcon(str(path))
                if not icon.isNull():
                    return icon
        return None

    @classmethod
    def badge_pixmap(cls, ticker, size):
        ticker = ticker or "--"
        initials, color = cls.badge_identity(ticker)
        pixmap = QPixmap(QSize(size, size))
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = pixmap.rect().adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(rect, 7, 7)
        painter.fillPath(path, QColor(color))

        border = QColor("#DCE8F2")
        border.setAlpha(70)
        painter.setPen(border)
        painter.drawPath(path)

        font = QFont()
        font.setBold(True)
        font.setPointSize(max(7, int(size * 0.34)))
        painter.setFont(font)
        painter.setPen(QColor("#F8FAFC"))
        painter.drawText(rect, Qt.AlignCenter, initials)
        painter.end()
        return pixmap

    @classmethod
    def badge_identity(cls, ticker):
        if ticker in cls.KNOWN_TICKERS:
            return cls.KNOWN_TICKERS[ticker]

        seed = sum(ord(char) for char in ticker)
        palette = (
            "#5B9DF2",
            "#35B779",
            "#67B7DC",
            "#D6A23A",
            "#E05A5A",
            "#A78BFA",
            "#14B8A6",
        )
        return ticker[:2], palette[seed % len(palette)]

    @staticmethod
    def normalized_ticker(ticker):
        return str(ticker or "").strip().upper()
