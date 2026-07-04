from PySide6.QtCore import QThread, Signal


class TaskWorker(QThread):
    started_signal = Signal(str)
    completed_signal = Signal(object)
    failed_signal = Signal(str)

    def __init__(self, task_name, task_callable, parent=None):
        super().__init__(parent)
        self.task_name = task_name
        self.task_callable = task_callable

    def run(self):
        try:
            self.started_signal.emit(self.task_name)
            result = self.task_callable()
            self.completed_signal.emit(result)
        except Exception as exc:
            self.failed_signal.emit(str(exc))
