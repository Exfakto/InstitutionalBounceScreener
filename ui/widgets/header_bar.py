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
        self.setMaximumHeight(76)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        title_layout = QVBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(2)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("HeaderTitle")

        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("HeaderSubtitle")

        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.subtitle_label)

        self.version_label = QLabel(version)
        self.version_label.setObjectName("HeaderVersion")
        self.version_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.status_label = QLabel(status)
        self.status_label.setObjectName("HeaderStatus")
        self.status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        status_layout = QVBoxLayout()
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(2)
        status_layout.addWidget(self.version_label)
        status_layout.addWidget(self.status_label)

        layout.addLayout(title_layout, stretch=1)
        layout.addLayout(status_layout)

    def set_status(self, text):
        """
        Set the displayed connection/status text.
        """

        self.status_label.setText(text)

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
