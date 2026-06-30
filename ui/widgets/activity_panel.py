from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QWidget

from ui.widgets.activity_log import ActivityLog
from ui.widgets.progress_panel import ProgressPanel


class ActivityPanel(QWidget):
    """
    Reusable activity panel with status, progress, and log output.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("ActivityPanel")
        self.setMaximumHeight(260)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.progress_panel = ProgressPanel()

        self.log_group = QGroupBox("Activity Log")
        self.log_group.setObjectName("ActivityLogGroup")
        log_layout = QVBoxLayout()
        log_layout.setContentsMargins(8, 10, 8, 8)
        self.activity_log = ActivityLog()
        self.activity_log.setMinimumHeight(96)
        log_layout.addWidget(self.activity_log)
        self.log_group.setLayout(log_layout)

        layout.addWidget(self.progress_panel)
        layout.addWidget(self.log_group)

    def append_log(self, message):
        """
        Append a message to the activity log.
        """

        self.activity_log.log(message)

    def clear_log(self):
        """
        Clear the activity log.
        """

        self.activity_log.clear_log()

    def set_progress(self, percent):
        """
        Set the progress bar value.
        """

        self.progress_panel.set_progress(percent)

    def set_status(self, text):
        """
        Set the status text.
        """

        self.progress_panel.set_status(text)

    def reset(self):
        """
        Reset status and progress.
        """

        self.progress_panel.reset()

    def status_text(self):
        """
        Return current status text for tests and simple callers.
        """

        return self.progress_panel.status.text()

    def progress_value(self):
        """
        Return current progress value for tests and simple callers.
        """

        return self.progress_panel.progress.value()

    def log_text(self):
        """
        Return current log text for tests and simple callers.
        """

        return self.activity_log.toPlainText()
