from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)
from PySide6.QtCore import Qt

from ui.design_system import DashboardDesignSystem as DesignSystem


class StatisticsCard(QFrame):
    """
    Reusable professional KPI card for dashboard statistics.
    """

    def __init__(
        self,
        title,
        value="0",
        subtitle="",
        icon_text="",
        accent_color=None,
        parent=None,
    ):
        super().__init__(parent)

        self.accent_color = accent_color or DesignSystem.Colors.ACCENT
        self.setFrameShape(QFrame.StyledPanel)
        self.setProperty("accent", self.accent_color)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            DesignSystem.Spacing.LG,
            DesignSystem.Spacing.MD,
            DesignSystem.Spacing.LG,
            DesignSystem.Spacing.MD,
        )
        layout.setSpacing(DesignSystem.Spacing.SM)

        self.accent_bar = QFrame()
        self.accent_bar.setObjectName("KpiAccentBar")
        self.accent_bar.setFixedHeight(3)
        self.accent_bar.setStyleSheet(
            f"background-color: {self.accent_color}; border: none; border-radius: 1px;"
        )

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(DesignSystem.Spacing.SM)

        self.icon = QLabel(icon_text)
        self.icon.setObjectName("KpiIcon")
        self.icon.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.icon.setVisible(bool(icon_text))
        self.icon.setStyleSheet(f"color: {self.accent_color};")

        self.title = QLabel(title)
        self.title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        header_layout.addWidget(self.icon)
        header_layout.addWidget(self.title, stretch=1)

        self.value = QLabel(str(value))
        self.value.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        font = self.value.font()
        font.setPointSize(DesignSystem.Typography.KPI_PT)
        font.setBold(True)
        self.value.setFont(font)

        self.subtitle = QLabel(subtitle)
        self.subtitle.setObjectName("KpiSubtitle")
        self.subtitle.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.subtitle.setVisible(bool(subtitle))

        layout.addWidget(self.accent_bar)
        layout.addLayout(header_layout)
        layout.addWidget(self.value)
        layout.addWidget(self.subtitle)

    def set_value(self, value):
        self.value.setText(str(value))

    def set_subtitle(self, subtitle):
        self.subtitle.setText(str(subtitle))
        self.subtitle.setVisible(bool(subtitle))

    def set_accent_color(self, color):
        self.accent_color = color or DesignSystem.Colors.ACCENT
        self.setProperty("accent", self.accent_color)
        self.accent_bar.setStyleSheet(
            f"background-color: {self.accent_color}; border: none; border-radius: 1px;"
        )
        self.icon.setStyleSheet(f"color: {self.accent_color};")
        self.style().unpolish(self)
        self.style().polish(self)
