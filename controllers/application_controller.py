from ui.main_window import MainWindow


class ApplicationController:
    """
    Responsible for bootstrapping the application.

    Future responsibilities:
    - Load configuration
    - Initialize logging
    - Initialize database
    - Create services
    - Launch the GUI
    """

    def __init__(self):
        self.main_window = None

    def start(self):
        self.main_window = MainWindow()
        self.main_window.show()