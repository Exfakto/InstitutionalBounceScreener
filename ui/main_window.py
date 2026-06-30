import sys

from PySide6.QtWidgets import (
    QApplication,
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
from controllers.bounce_controller import BounceController
from controllers.scoring_controller import ScoringController

from ui.widgets.activity_log import ActivityLog
from ui.widgets.progress_panel import ProgressPanel
from ui.widgets.candidate_table import CandidateTable
from ui.widgets.kpi_strip import KpiStrip
from ui.stock_detail_window import StockDetailWindow


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.controller = MarketController()
        self.indicator_controller = IndicatorController()
        self.support_controller = SupportController()
        self.bounce_controller = BounceController()
        self.scoring_controller = ScoringController()

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

        self.kpi_strip = KpiStrip()

        main_layout.addWidget(self.kpi_strip)

        ##########################################################
        # Ranked Candidates
        ##########################################################

        self.candidates_table = CandidateTable()
        self.candidates_table.ticker_double_clicked.connect(self.open_stock_detail)

        main_layout.addWidget(self.candidates_table)

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

        self.validation_button = QPushButton("Validate Bounces")
        self.validation_button.clicked.connect(self.validate_bounces)

        self.screen_button = QPushButton("▶ Run Screener")
        self.screen_button.clicked.connect(self.run_screener)

        operations_layout.addWidget(self.update_button)
        operations_layout.addWidget(self.download_button)
        operations_layout.addWidget(self.indicators_button)
        operations_layout.addWidget(self.support_button)
        operations_layout.addWidget(self.validation_button)
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

        self.kpi_strip.update_statistics(stats)

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

    def validate_bounces(self):

        self.progress.set_status("Validating bounces...")
        self.progress.set_progress(20)

        self.log_widget.clear_log()

        results = self.bounce_controller.validate_bounces()

        self.progress.set_progress(100)

        self.progress.set_status("Ready")

        self.refresh_statistics()

        self.log("Validated support-zone bounces")
        self.log(f'Support zones: {results["support_levels"]:,}')
        self.log(f'Processed: {results["processed"]:,}')
        self.log(
            f'Processed tickers: {self.format_ticker_list(results["processed_tickers"])}'
        )
        self.log(f'Skipped: {results["skipped"]:,}')
        self.log(
            f'Skipped tickers: {self.format_ticker_list(results["skipped_tickers"])}'
        )
        self.log(f'Validated zones: {results["validated"]:,}')
        self.log(f'Elapsed time: {results["elapsed_seconds"]:.2f}s')

    # ----------------------------------------------------------

    def run_screener(self):

        self.progress.set_status("Running screener...")
        self.progress.set_progress(10)

        self.log_widget.clear_log()

        self.progress.set_status("Processing candidates...")
        self.progress.set_progress(50)

        results = self.scoring_controller.run_screener()

        self.candidates_table.populate(results["candidates"])

        self.progress.set_progress(100)

        self.progress.set_status("Screener Complete")

        highest = self.highest_candidate(results["candidates"])
        average_score = self.average_candidate_score(results["candidates"])

        self.log("Candidate screening complete")
        self.log(f'Tickers analyzed: {results["processed"]:,}')
        self.log(f'Skipped: {results["skipped"]:,}')
        self.log(f'Candidates generated: {len(results["candidates"]):,}')

        if highest is None:
            self.log("Highest score: None")
        else:
            self.log(
                f"Highest score: {highest.ticker} "
                f"{highest.composite_score.value:.1f}"
            )

        self.log(f"Average score: {average_score:.1f}")
        self.log(f'Elapsed time: {results["elapsed_seconds"]:.2f}s')

    # ----------------------------------------------------------

    def open_stock_detail(self, ticker):

        detail = self.scoring_controller.get_candidate_detail(ticker)
        window = StockDetailWindow(detail, self)
        window.show()

        if not hasattr(self, "detail_windows"):
            self.detail_windows = []

        self.detail_windows.append(window)

    # ----------------------------------------------------------

    def highest_candidate(self, candidates):

        if not candidates:
            return None

        return max(
            candidates,
            key=lambda candidate: candidate.composite_score.value,
        )

    # ----------------------------------------------------------

    def average_candidate_score(self, candidates):

        if not candidates:
            return 0.0

        total = sum(
            candidate.composite_score.value
            for candidate in candidates
        )

        return total / len(candidates)

    # ----------------------------------------------------------

    def closeEvent(self, event):

        self.controller.close()
        self.indicator_controller.close()
        self.support_controller.close()
        self.bounce_controller.close()
        self.scoring_controller.close()

        super().closeEvent(event)
