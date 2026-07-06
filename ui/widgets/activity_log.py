from PySide6.QtGui import QTextOption
from PySide6.QtWidgets import QTextEdit


class ActivityLog(QTextEdit):

    def __init__(self):
        super().__init__()

        self.setReadOnly(True)
        self.setLineWrapMode(QTextEdit.WidgetWidth)
        self.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.setMinimumWidth(240)

    def log(self, message):
        text = str(message)
        self.append(text)
        self.setToolTip(text)

    def clear_log(self):
        self.clear()
