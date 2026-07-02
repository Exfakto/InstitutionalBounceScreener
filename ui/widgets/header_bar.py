from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout


class HeaderBar(QFrame):
    """
    Professional application header.
    """

    def __init__(
        self,
        title="Institutional Bounce Platform",
        version="v2.0",
        status="Ready",
        subtitle="Institutional Research Workstation",
        parent=None,
    ):
        super().__init__(parent)

        self.setObjectName("HeaderBar")
        self.setMaximumHeight(112)
        self.setMinimumHeight(88)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 10, 18, 10)
        layout.setSpacing(18)

        title_layout = QVBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(3)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("HeaderTitle")
        title_font = self.title_label.font()
        title_font.setPointSize(15)
        title_font.setBold(True)
        self.title_label.setFont(title_font)

        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("HeaderSubtitle")

        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.subtitle_label)

        self.version_label = QLabel(version)
        self.version_label.setObjectName("HeaderVersion")
        self.version_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        version_font = self.version_label.font()
        version_font.setBold(True)
        self.version_label.setFont(version_font)

        self.status_label = QLabel(status)
        self.status_label.setObjectName("HeaderStatus")
        self.status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.market_status_label = QLabel("Market: --")
        self.market_status_label.setObjectName("HeaderStatus")
        self.market_status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.auto_refresh_label = QLabel("Auto-refresh: --")
        self.auto_refresh_label.setObjectName("HeaderStatus")
        self.auto_refresh_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.refresh_interval_label = QLabel("Interval: --")
        self.refresh_interval_label.setObjectName("HeaderStatus")
        self.refresh_interval_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.last_refresh_label = QLabel("Last refresh: --")
        self.last_refresh_label.setObjectName("HeaderStatus")
        self.last_refresh_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.next_refresh_label = QLabel("Next refresh: --")
        self.next_refresh_label.setObjectName("HeaderStatus")
        self.next_refresh_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        status_layout = QVBoxLayout()
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(3)
        status_layout.addWidget(self.version_label)
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.market_status_label)
        status_layout.addWidget(self.auto_refresh_label)
        status_layout.addWidget(self.refresh_interval_label)
        status_layout.addWidget(self.last_refresh_label)
        status_layout.addWidget(self.next_refresh_label)

        layout.addLayout(title_layout, stretch=1)
        layout.addLayout(status_layout)

    def set_status(self, text):
        """
        Set the displayed connection/status text.
        """

        self.status_label.setText(text)

    def set_refresh_status(
        self,
        market_status=None,
        auto_refresh=None,
        refresh_interval=None,
        last_refresh=None,
        next_refresh=None,
    ):
        """
        Display supplied market and auto-refresh state.
        """

        self.market_status_label.setText(
            f"Market: {self.safe_text(market_status)}"
        )
        self.auto_refresh_label.setText(
            f"Auto-refresh: {self.auto_refresh_text(auto_refresh)}"
        )
        self.refresh_interval_label.setText(
            f"Interval: {self.interval_text(refresh_interval)}"
        )
        self.last_refresh_label.setText(
            f"Last refresh: {self.datetime_text(last_refresh)}"
        )
        self.next_refresh_label.setText(
            f"Next refresh: {self.datetime_text(next_refresh)}"
        )

    def set_version(self, text):
        """
        Set the displayed version.
        """

        self.version_label.setText(text)

    def set_title(self, text):
        """
        Set the displayed application title.
        """

        self.title_label.setText(text)

    def status_text(self):
        """
        Return displayed status text for tests and simple callers.
        """

        return self.status_label.text()

    def market_status_text(self):
        """
        Return displayed market status text.
        """

        return self.market_status_label.text()

    def auto_refresh_text_value(self):
        """
        Return displayed auto-refresh text.
        """

        return self.auto_refresh_label.text()

    def refresh_interval_text(self):
        """
        Return displayed refresh interval text.
        """

        return self.refresh_interval_label.text()

    def last_refresh_text(self):
        """
        Return displayed last refresh text.
        """

        return self.last_refresh_label.text()

    def next_refresh_text(self):
        """
        Return displayed next refresh text.
        """

        return self.next_refresh_label.text()

    def version_text(self):
        """
        Return displayed version text for tests and simple callers.
        """

        return self.version_label.text()

    def title_text(self):
        """
        Return displayed title text for tests and simple callers.
        """

        return self.title_label.text()

    def subtitle_text(self):
        """
        Return displayed subtitle text for tests and simple callers.
        """

        return self.subtitle_label.text()

    @staticmethod
    def safe_text(value):
        if value in (None, ""):
            return "--"

        return str(value)

    @staticmethod
    def auto_refresh_text(value):
        if value is True:
            return "On"

        if value is False:
            return "Off"

        return "--"

    @classmethod
    def interval_text(cls, seconds):
        if seconds is None:
            return "--"

        try:
            total_seconds = int(seconds)
        except (TypeError, ValueError):
            return "--"

        if total_seconds <= 0:
            return "--"

        if total_seconds % 60 == 0:
            return f"{total_seconds // 60} min"

        return f"{total_seconds} sec"

    @staticmethod
    def datetime_text(value):
        if value is None:
            return "--"

        if isinstance(value, datetime):
            return value.strftime("%H:%M")

        return str(value)
