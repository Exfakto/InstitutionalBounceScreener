from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget

from ui.design_system import DashboardDesignSystem as DesignSystem
from ui.widgets.provider_health_panel import ProviderHealthPanel


class SettingsPanel(QWidget):
    def __init__(self, market_data_controller=None, parent=None):
        super().__init__(parent)
        self.market_data_controller = market_data_controller
        self.setObjectName("SettingsPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            DesignSystem.Spacing.MD,
            DesignSystem.Spacing.MD,
            DesignSystem.Spacing.MD,
            DesignSystem.Spacing.MD,
        )
        layout.setSpacing(DesignSystem.Spacing.SM)
        self.provider_health_panel = ProviderHealthPanel(controller=market_data_controller)
        layout.addWidget(self.provider_health_panel)
        layout.addStretch(1)
