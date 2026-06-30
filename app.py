import sys

from PySide6.QtWidgets import QApplication

from controllers.application_controller import ApplicationController
from ui.theme import Theme


def main():

    app = QApplication(sys.argv)
    Theme.apply(app)

    controller = ApplicationController()

    controller.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
