import sys

from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from controllers.market_controller import MarketController
from controllers.indicator_controller import IndicatorController
from controllers.support_controller import SupportController

from ui.widgets.statistics_card import StatisticsCard
from ui.widgets.activity_log import ActivityLog
from ui.widgets.progress_panel import ProgressPanel


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.controller = MarketController()
        self.indicator_controller = IndicatorController()
        self.support_controller = SupportController()

        self.setWindowTitle("Institutional Bounce Screener")
        self.resize(1200, 800)

        self.build_ui()

        self.refresh_statistics()

    # ----------------------------------------------------------

    def build_ui(self):

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)

        ##########################################################
        # Title
        ##########################################################

        title = QLabel("<h1>Institutional Bounce Screener</h1>")
        main_layout.addWidget(title)

        ##########################################################
        # Statistics
        ##########################################################

        stats_layout = QGridLayout()

        self.universe_card = StatisticsCard("Universe Stocks")
        self.database_card = StatisticsCard("Price Records")
        self.indicator_card = StatisticsCard("Indicator Rows")
        self.support_card = StatisticsCard("Support Zones")

        stats_layout.addWidget(self.universe_card, 0, 0)
        stats_layout.addWidget(self.database_card, 0, 1)
        stats_layout.addWidget(self.indicator_card, 0, 2)
        stats_layout.addWidget(self.support_card, 0, 3)

        main_layout.addLayout(stats_layout)

        ##########################################################
        # Operations
        ##########################################################

        operations = QGroupBox("Operations")

        operations_layout = QHBoxLayout()

        self.update_button = QPushButton("🌎 Update Universe")
        self.update_button.clicked.connect(self.update_universe)

        self.download_button = QPushButton("📥 Download Prices")
        self.download_button.clicked.connect(self.download_prices)

        self.indicators_button = QPushButton("Calculate Indicators")
        self.indicators_button.clicked.connect(self.calculate_indicators)

        self.support_button = QPushButton("Detect Support")
        self.support_button.clicked.connect(self.detect_support)

        self.screen_button = QPushButton("▶ Run Screener")
        self.screen_button.setEnabled(False)

        operations_layout.addWidget(self.update_button)
        operations_layout.addWidget(self.download_button)
        operations_layout.addWidget(self.indicators_button)
        operations_layout.addWidget(self.support_button)
        operations_layout.addWidget(self.screen_button)

        operations.setLayout(operations_layout)

        main_layout.addWidget(operations)

        ##########################################################
        # Progress
        ##########################################################

        self.progress = ProgressPanel()

        main_layout.addWidget(self.progress)

        ##########################################################
        # Activity Log
        ##########################################################

        log_group = QGroupBox("Activity Log")

        log_layout = QVBoxLayout()

        self.log_widget = ActivityLog()

        log_layout.addWidget(self.log_widget)

        log_group.setLayout(log_layout)

        main_layout.addWidget(log_group)

    # ----------------------------------------------------------

    def log(self, text):

        self.log_widget.log(text)

        QApplication.processEvents()

    # ----------------------------------------------------------

    def refresh_statistics(self):

        stats = self.controller.get_statistics()

        self.universe_card.set_value(stats["stocks"])

        self.database_card.set_value(f'{stats["rows"]:,}')

        self.indicator_card.set_value(f'{stats["indicator_rows"]:,}')

        self.support_card.set_value(f'{stats["support_levels"]:,}')

    # ----------------------------------------------------------

    def update_universe(self):

        self.progress.set_status("Importing universe...")
        self.progress.set_progress(20)

        self.log_widget.clear_log()

        imported, total = self.controller.update_universe()

        self.log(f"✅ Imported {imported} stocks")

        self.progress.set_progress(100)

        self.progress.set_status("Ready")

        self.refresh_statistics()

    # ----------------------------------------------------------

    def download_prices(self):

        self.progress.set_status("Downloading prices...")
        self.progress.set_progress(10)

        self.log_widget.clear_log()

        results, total = self.controller.download_prices()

        for ticker, rows in results.items():

            self.log(f"✓ {ticker}: {rows} rows")

        self.progress.set_progress(100)

        self.progress.set_status("Ready")

        self.refresh_statistics()

        self.log("")
        self.log(f"Database Rows: {total:,}")

    # ----------------------------------------------------------

    def calculate_indicators(self):

        self.progress.set_status("Calculating indicators...")
        self.progress.set_progress(20)

        self.log_widget.clear_log()

        results = self.indicator_controller.calculate_indicators()

        self.progress.set_progress(100)

        self.progress.set_status("Ready")

        self.refresh_statistics()

        self.log("Calculated indicators")
        self.log(f'Tickers: {results["tickers"]:,}')
        self.log(f'Processed: {results["processed"]:,}')
        self.log(
            f'Processed tickers: {self.format_ticker_list(results["processed_tickers"])}'
        )
        self.log(f'Skipped: {results["skipped"]:,}')
        self.log(
            f'Skipped tickers: {self.format_ticker_list(results["skipped_tickers"])}'
        )
        self.log(f'Indicator rows written: {results["rows"]:,}')
        self.log(f'Elapsed time: {results["elapsed_seconds"]:.2f}s')

    # ----------------------------------------------------------

    def format_ticker_list(self, tickers):

        if not tickers:
            return "None"

        return ", ".join(tickers)

    # ----------------------------------------------------------

    def detect_support(self):

        self.progress.set_status("Detecting support...")
        self.progress.set_progress(20)

        self.log_widget.clear_log()

        results = self.support_controller.detect_support()

        self.progress.set_progress(100)

        self.progress.set_status("Ready")

        self.refresh_statistics()

        self.log("Detected support zones")
        self.log(f'Tickers: {results["tickers"]:,}')
        self.log(f'Processed: {results["processed"]:,}')
        self.log(
            f'Processed tickers: {self.format_ticker_list(results["processed_tickers"])}'
        )
        self.log(f'Skipped: {results["skipped"]:,}')
        self.log(
            f'Skipped tickers: {self.format_ticker_list(results["skipped_tickers"])}'
        )
        self.log(f'Zones found: {results["zones"]:,}')
        self.log(f'Elapsed time: {results["elapsed_seconds"]:.2f}s')

    # ----------------------------------------------------------

    def closeEvent(self, event):

        self.controller.close()
        self.indicator_controller.close()
        self.support_controller.close()

        super().closeEvent(event)
