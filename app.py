import sys

from PySide6.QtWidgets import QApplication

from controllers.application_controller import ApplicationController


def main():

    app = QApplication(sys.argv)

    controller = ApplicationController()

    controller.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()