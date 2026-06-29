from PySide6.QtWidgets import QTextEdit


class ActivityLog(QTextEdit):

    def __init__(self):
        super().__init__()

        self.setReadOnly(True)

    def log(self, message):
        self.append(message)

    def clear_log(self):
        self.clear()