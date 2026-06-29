from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
)
from PySide6.QtCore import Qt


class StatisticsCard(QFrame):
    """
    Displays a statistic such as
    Universe Size or Database Rows.
    """

    def __init__(self, title, value="0"):
        super().__init__()

        self.setFrameShape(QFrame.StyledPanel)

        layout = QVBoxLayout(self)

        self.title = QLabel(title)
        self.title.setAlignment(Qt.AlignCenter)

        self.value = QLabel(str(value))
        self.value.setAlignment(Qt.AlignCenter)

        font = self.value.font()
        font.setPointSize(18)
        font.setBold(True)
        self.value.setFont(font)

        layout.addWidget(self.title)
        layout.addWidget(self.value)

    def set_value(self, value):
        self.value.setText(str(value))