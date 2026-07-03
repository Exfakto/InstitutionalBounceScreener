from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from ui.design_system import DashboardDesignSystem as DesignSystem


class PipelineProgressPanel(QFrame):
    """
    Compact visual tracker for the screening workflow pipeline.
    """

    STEPS = [
        ("universe", "Universe"),
        ("prices", "Prices"),
        ("indicators", "Indicators"),
        ("support", "Support"),
        ("bounce_validation", "Bounce Validation"),
        ("screener", "Screener"),
    ]

    VALID_STATUSES = {"Pending", "Running", "Complete", "Error"}

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("PipelineProgressPanel")
        self.step_widgets = {}
        self.step_state = {
            key: {"status": "Pending", "timestamp": None}
            for key, _ in self.STEPS
        }

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            DesignSystem.Spacing.LG,
            DesignSystem.Spacing.MD,
            DesignSystem.Spacing.LG,
            DesignSystem.Spacing.MD,
        )
        layout.setSpacing(DesignSystem.Spacing.MD)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(DesignSystem.Spacing.MD)

        self.title_label = QLabel("Pipeline Progress")
        self.title_label.setObjectName("PipelineTitle")

        self.progress_label = QLabel("0% Complete")
        self.progress_label.setObjectName("PipelineProgressLabel")
        self.progress_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("PipelineProgressBar")
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)

        steps_grid = QGridLayout()
        steps_grid.setContentsMargins(0, 0, 0, 0)
        steps_grid.setHorizontalSpacing(DesignSystem.Spacing.MD)
        steps_grid.setVerticalSpacing(DesignSystem.Spacing.SM)

        for column, (key, name) in enumerate(self.STEPS):
            step = self.create_step_widget(name)
            self.step_widgets[key] = step
            steps_grid.addWidget(step["container"], 0, column)

        layout.addLayout(header_layout)
        layout.addWidget(self.progress_bar)
        layout.addLayout(steps_grid)

    def create_step_widget(self, name):
        container = QWidget()
        container.setObjectName("PipelineStep")

        layout = QVBoxLayout(container)
        layout.setContentsMargins(
            DesignSystem.Spacing.SM,
            DesignSystem.Spacing.SM,
            DesignSystem.Spacing.SM,
            DesignSystem.Spacing.SM,
        )
        layout.setSpacing(DesignSystem.Spacing.XS)

        name_label = QLabel(name)
        name_label.setObjectName("PipelineStepName")
        name_label.setAlignment(Qt.AlignCenter)

        status_label = QLabel("Pending")
        status_label.setObjectName("PipelineStepStatus")
        status_label.setProperty("status", "Pending")
        status_label.setAlignment(Qt.AlignCenter)

        timestamp_label = QLabel("Last: N/A")
        timestamp_label.setObjectName("PipelineStepTimestamp")
        timestamp_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(name_label)
        layout.addWidget(status_label)
        layout.addWidget(timestamp_label)

        return {
            "container": container,
            "name": name_label,
            "status": status_label,
            "timestamp": timestamp_label,
        }

    def update_step(self, step_key, status, timestamp=None):
        """
        Update one pipeline step safely.
        """

        if step_key not in self.step_state:
            return

        normalized_status = status if status in self.VALID_STATUSES else "Pending"
        self.step_state[step_key] = {
            "status": normalized_status,
            "timestamp": timestamp,
        }

        widgets = self.step_widgets[step_key]
        widgets["status"].setText(normalized_status)
        widgets["status"].setProperty("status", normalized_status)
        widgets["status"].style().unpolish(widgets["status"])
        widgets["status"].style().polish(widgets["status"])
        widgets["timestamp"].setText(f"Last: {self.format_timestamp(timestamp)}")

        self.update_overall_progress()

    def mark_running(self, step_key):
        self.update_step(step_key, "Running")

    def mark_complete(self, step_key, timestamp=None):
        self.update_step(step_key, "Complete", timestamp or datetime.now())

    def mark_error(self, step_key, timestamp=None):
        self.update_step(step_key, "Error", timestamp or datetime.now())

    def progress_percentage(self):
        complete_steps = sum(
            1
            for state in self.step_state.values()
            if state.get("status") == "Complete"
        )

        if not self.step_state:
            return 0

        return round((complete_steps / len(self.step_state)) * 100)

    def update_overall_progress(self):
        percent = self.progress_percentage()
        self.progress_bar.setValue(percent)
        self.progress_label.setText(f"{percent}% Complete")

    def status_for(self, step_key):
        return self.step_state.get(step_key, {}).get("status")

    def timestamp_text_for(self, step_key):
        widgets = self.step_widgets.get(step_key)
        if not widgets:
            return None
        return widgets["timestamp"].text()

    @staticmethod
    def format_timestamp(timestamp):
        if not timestamp:
            return "N/A"
        if isinstance(timestamp, datetime):
            return timestamp.strftime("%Y-%m-%d %H:%M:%S")
        return str(timestamp)
