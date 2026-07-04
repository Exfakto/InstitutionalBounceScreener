from pathlib import Path

from PySide6.QtCore import QSize, Qt, QRectF
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

    LOGO_DIR = Path(__file__).resolve().parents[2] / "assets" / "logos"
    EXTENSIONS = (".svg", ".png", ".jpg", ".jpeg", ".webp")
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

        names = {ticker, ticker.lower(), ticker.upper()}
        for name in names:
            for extension in cls.EXTENSIONS:
                path = cls.LOGO_DIR / f"{name}{extension}"
                if path.exists():
                    logo = QIcon(str(path))
                    if logo.isNull():
                        continue

                    canvas = QPixmap(QSize(32, 32))
                    canvas.fill(Qt.transparent)

                    painter = QPainter(canvas)
                    painter.setRenderHint(QPainter.Antialiasing, True)
                    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

                    tile_rect = QRectF(1.0, 1.0, 30.0, 30.0)
                    painter.setBrush(QColor("#FFFFFF"))
                    painter.setPen(QColor("#D8DEE6"))
                    painter.drawRoundedRect(tile_rect, 8.0, 8.0)

                    logo_pixmap = logo.pixmap(QSize(44, 44)).scaled(
                        QSize(22, 22),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
                    x = int((32 - logo_pixmap.width()) / 2)
                    y = int((32 - logo_pixmap.height()) / 2)
                    painter.drawPixmap(x, y, logo_pixmap)
                    painter.end()
                    return QIcon(canvas)
        return None

    @classmethod
    def badge_pixmap(cls, ticker, size):
        ticker = ticker or "--"
        initials, color = cls.badge_identity(ticker)
        scale = 2
        device_size = size * scale
        pixmap = QPixmap(QSize(device_size, device_size))
        pixmap.setDevicePixelRatio(scale)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = pixmap.rect().adjusted(scale, scale, -scale, -scale)
        path = QPainterPath()
        radius = max(7, int(size * 0.34)) * scale
        path.addRoundedRect(rect, radius, radius)

        base = QColor(color)
        painter.fillPath(path, base)

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
