from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget


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
    open_detail_requested = Signal()

    BUTTON_DEFINITIONS = [
        ("update_universe", "Update Universe", "update_universe_requested"),
        ("download_prices", "Download Prices", "download_prices_requested"),
        (
            "calculate_indicators",
            "Calculate Indicators",
            "calculate_indicators_requested",
        ),
        ("detect_support", "Detect Support", "detect_support_requested"),
        ("validate_bounces", "Validate Bounces", "validate_bounces_requested"),
        ("run_screener", "Run Screener", "run_screener_requested"),
        ("open_detail", "Open Detail", "open_detail_requested"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)

        self.buttons = {}

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        for key, label, signal_name in self.BUTTON_DEFINITIONS:
            button = QPushButton(label)
            button.clicked.connect(getattr(self, signal_name).emit)

            self.buttons[key] = button
            layout.addWidget(button)

        layout.addStretch()

        self.set_open_detail_enabled(False)

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
