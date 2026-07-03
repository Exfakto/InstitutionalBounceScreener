from ui.main_window import MainWindow
from config.logging_config import logger
from services.startup_diagnostics_service import StartupDiagnosticsService


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
        self.startup_diagnostics = StartupDiagnosticsService()

    def start(self):
        report = self.startup_diagnostics.run()
        logger.info("Startup diagnostics: %s", report.status)
        self.main_window = MainWindow()
        self.main_window.show()
