from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QWidget

from ui.design_system import DashboardDesignSystem as DesignSystem


class OperationsToolbar(QWidget):
    """
    Toolbar of dashboard operation buttons.
    """

    update_universe_requested = Signal()
    download_prices_requested = Signal()
    calculate_indicators_requested = Signal()
    detect_support_requested = Signal()
    validate_bounces_requested = Signal()
    run_screener_requested = Signal()
    save_preset_requested = Signal()
    load_preset_requested = Signal()
    reset_filters_requested = Signal()
    refresh_results_requested = Signal()
    open_detail_requested = Signal()

    ACTION_GROUPS = [
        (
            "Market Data",
            [
                ("update_universe", "Update Universe", "update_universe_requested"),
                ("download_prices", "Download Prices", "download_prices_requested"),
            ],
        ),
        (
            "Analysis",
            [
                (
                    "calculate_indicators",
                    "Calculate Indicators",
                    "calculate_indicators_requested",
                ),
                ("detect_support", "Detect Support", "detect_support_requested"),
                ("validate_bounces", "Validate Bounces", "validate_bounces_requested"),
            ],
        ),
        (
            "Research",
            [
                ("run_screener", "Run Screener", "run_screener_requested"),
                ("save_preset", "Save Preset", "save_preset_requested"),
                ("load_preset", "Load Preset", "load_preset_requested"),
                ("reset_filters", "Reset Filters", "reset_filters_requested"),
                ("refresh_results", "Refresh Results", "refresh_results_requested"),
                ("open_detail", "Open Detail", "open_detail_requested"),
            ],
        ),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("OperationsToolbar")

        self.buttons = {}

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(DesignSystem.Spacing.MD)

        for group_index, (group_label, actions) in enumerate(self.ACTION_GROUPS):
            if group_index > 0:
                layout.addWidget(self.separator())

            label = QLabel(group_label)
            label.setObjectName("ToolbarGroupLabel")
            label.setMinimumHeight(36)
            layout.addWidget(label)

            for key, text, signal_name in actions:
                button = QPushButton(text)
                button.setProperty(
                    "variant",
                    "primary" if key in {"run_screener", "refresh_results"} else "secondary",
                )
                button.setMinimumHeight(36)
                button.setMinimumWidth(118)
                button.clicked.connect(getattr(self, signal_name).emit)

                self.buttons[key] = button
                layout.addWidget(button)

        layout.addStretch()

        self.set_open_detail_enabled(False)

    @staticmethod
    def separator():
        line = QFrame()
        line.setObjectName("ToolbarSeparator")
        line.setFrameShape(QFrame.VLine)
        line.setFrameShadow(QFrame.Plain)

        return line

    def set_open_detail_enabled(self, enabled):
        """
        Enable or disable the Open Detail action.
        """

        self.buttons["open_detail"].setEnabled(enabled)

    def is_open_detail_enabled(self):
        """
        Return whether Open Detail is currently enabled.
        """

        return self.buttons["open_detail"].isEnabled()
