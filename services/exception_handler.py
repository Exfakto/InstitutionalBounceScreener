from __future__ import annotations

import logging
import sys
import traceback

from PySide6.QtWidgets import QApplication, QMessageBox


class GlobalExceptionHandler:
    """
    Register a sys.excepthook that logs tracebacks and shows a safe UI message.
    """

    def __init__(self, logger=None, dialog_factory=None):
        self.logger = logger or logging.getLogger("IBS")
        self.dialog_factory = dialog_factory or QMessageBox.critical
        self.previous_hook = None

    def register(self):
        self.previous_hook = sys.excepthook
        sys.excepthook = self.handle_exception
        return self

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            if self.previous_hook:
                return self.previous_hook(exc_type, exc_value, exc_traceback)
            return None

        formatted = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        self.logger.error("Unhandled exception\n%s", formatted)

        if QApplication.instance() is not None:
            try:
                self.dialog_factory(
                    None,
                    "Unexpected Error",
                    (
                        "An unexpected error occurred. The application will try to "
                        "remain open. Check the logs for technical details."
                    ),
                )
            except Exception:
                self.logger.exception("Unable to display exception dialog")
        return None
