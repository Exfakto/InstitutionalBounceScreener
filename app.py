import sys

from PySide6.QtWidgets import QApplication

from controllers.application_controller import ApplicationController
from config.logging_config import configure_logging
from services.exception_handler import GlobalExceptionHandler
from ui.theme import Theme


def main():

    configure_logging()
    GlobalExceptionHandler().register()
    app = QApplication(sys.argv)
    Theme.apply(app)

    controller = ApplicationController()

    controller.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
