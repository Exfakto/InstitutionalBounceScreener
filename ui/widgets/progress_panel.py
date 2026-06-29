from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QProgressBar,
)


class ProgressPanel(QWidget):

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        self.status = QLabel("Ready")

        self.progress = QProgressBar()

        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        self.progress.setValue(0)

        layout.addWidget(self.status)
        layout.addWidget(self.progress)

    def set_status(self, text):
        self.status.setText(text)

    def set_progress(self, value):
        self.progress.setValue(value)

    def reset(self):
        self.status.setText("Ready")
        self.progress.setValue(0)