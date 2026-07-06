from PySide6.QtCore import QSize, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStyle,
    QWidget,
)

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
                (
                    "update_universe",
                    "Update Universe",
                    "update_universe_requested",
                    QStyle.SP_DirIcon,
                ),
                (
                    "download_prices",
                    "Download Prices",
                    "download_prices_requested",
                    QStyle.SP_ArrowDown,
                ),
            ],
        ),
        (
            "Analysis",
            [
                (
                    "calculate_indicators",
                    "Calculate Indicators",
                    "calculate_indicators_requested",
                    QStyle.SP_FileDialogDetailedView,
                ),
                (
                    "detect_support",
                    "Detect Support",
                    "detect_support_requested",
                    QStyle.SP_FileDialogContentsView,
                ),
                (
                    "validate_bounces",
                    "Validate Bounces",
                    "validate_bounces_requested",
                    QStyle.SP_DialogApplyButton,
                ),
            ],
        ),
        (
            "Research",
            [
                (
                    "run_screener",
                    "Run Screener",
                    "run_screener_requested",
                    QStyle.SP_MediaPlay,
                ),
                (
                    "save_preset",
                    "Save Preset",
                    "save_preset_requested",
                    QStyle.SP_DialogSaveButton,
                ),
                (
                    "load_preset",
                    "Load Preset",
                    "load_preset_requested",
                    QStyle.SP_DialogOpenButton,
                ),
                (
                    "reset_filters",
                    "Reset Filters",
                    "reset_filters_requested",
                    QStyle.SP_BrowserStop,
                ),
                (
                    "refresh_results",
                    "Refresh Results",
                    "refresh_results_requested",
                    QStyle.SP_BrowserReload,
                ),
                (
                    "open_detail",
                    "Open Detail",
                    "open_detail_requested",
                    QStyle.SP_FileDialogInfoView,
                ),
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

            for key, text, signal_name, icon in actions:
                button = QPushButton(text)
                button.setObjectName("ToolbarActionButton")
                button.setProperty(
                    "variant",
                    "primary" if key in {"run_screener", "refresh_results"} else "secondary",
                )
                button.setIcon(self.style().standardIcon(icon))
                button.setIconSize(QSize(15, 15))
                button.setToolTip(text)
                button.setMinimumHeight(36)
                button.setMinimumWidth(112)
                button.setMaximumWidth(156)
                button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
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

    def set_run_screener_enabled(self, enabled):
        """
        Enable or disable the Run Screener action.
        """

        self.buttons["run_screener"].setEnabled(enabled)

    def is_open_detail_enabled(self):
        """
        Return whether Open Detail is currently enabled.
        """

        return self.buttons["open_detail"].isEnabled()
