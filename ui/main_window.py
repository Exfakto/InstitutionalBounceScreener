import sys

from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from controllers.market_controller import MarketController
from controllers.indicator_controller import IndicatorController
from controllers.support_controller import SupportController
from controllers.bounce_controller import BounceController
from controllers.scoring_controller import ScoringController
from controllers.chart_controller import ChartController

from ui.widgets.activity_panel import ActivityPanel
from ui.widgets.candidate_table import CandidateTable
from ui.widgets.kpi_strip import KpiStrip
from ui.widgets.operations_toolbar import OperationsToolbar
from ui.widgets.header_bar import HeaderBar
from ui.widgets.price_chart import PriceChart
from ui.widgets.research_preview import ResearchPreview
from ui.stock_detail_window import StockDetailWindow


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.controller = MarketController()
        self.indicator_controller = IndicatorController()
        self.support_controller = SupportController()
        self.bounce_controller = BounceController()
        self.scoring_controller = ScoringController()
        self.chart_controller = ChartController()
        self.candidates_by_ticker = {}

        self.setWindowTitle("Institutional Bounce Screener")
        self.resize(1600, 900)

        self.build_ui()

        self.refresh_statistics()

    # ----------------------------------------------------------

    def build_ui(self):

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)

        ##########################################################
        # Header
        ##########################################################

        self.header_bar = HeaderBar()
        main_layout.addWidget(self.header_bar)

        ##########################################################
        # Statistics
        ##########################################################

        self.kpi_strip = KpiStrip()

        main_layout.addWidget(self.kpi_strip)

        ##########################################################
        # Operations
        ##########################################################

        self.operations_toolbar = OperationsToolbar()
        self.operations_toolbar.update_universe_requested.connect(self.update_universe)
        self.operations_toolbar.download_prices_requested.connect(self.download_prices)
        self.operations_toolbar.calculate_indicators_requested.connect(
            self.calculate_indicators
        )
        self.operations_toolbar.detect_support_requested.connect(self.detect_support)
        self.operations_toolbar.validate_bounces_requested.connect(self.validate_bounces)
        self.operations_toolbar.run_screener_requested.connect(self.run_screener)
        self.operations_toolbar.open_detail_requested.connect(
            self.open_selected_stock_detail
        )

        main_layout.addWidget(self.operations_toolbar)

        ##########################################################
        # Main Workspace
        ##########################################################

        workspace_layout = QHBoxLayout()
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(12)

        self.candidates_table = CandidateTable()
        self.candidates_table.ticker_double_clicked.connect(self.open_stock_detail)
        self.candidates_table.selectionModel().selectionChanged.connect(
            self.update_open_detail_state
        )

        left_workspace = QVBoxLayout()
        left_workspace.setContentsMargins(0, 0, 0, 0)
        left_workspace.setSpacing(12)

        self.price_chart = PriceChart()
        self.research_preview = ResearchPreview()

        left_workspace.addWidget(self.candidates_table, stretch=3)
        left_workspace.addWidget(self.price_chart, stretch=2)

        workspace_layout.addLayout(left_workspace, stretch=5)
        workspace_layout.addWidget(self.research_preview, stretch=1)

        main_layout.addLayout(workspace_layout, stretch=5)

        ##########################################################
        # Activity
        ##########################################################

        self.activity_panel = ActivityPanel()

        main_layout.addWidget(self.activity_panel, stretch=1)

    # ----------------------------------------------------------

    def log(self, text):

        self.activity_panel.append_log(text)

        QApplication.processEvents()

    # ----------------------------------------------------------

    def refresh_statistics(self):

        stats = self.controller.get_statistics()

        self.kpi_strip.update_statistics(stats)

    # ----------------------------------------------------------

    def update_universe(self):

        self.activity_panel.set_status("Importing universe...")
        self.activity_panel.set_progress(20)

        self.activity_panel.clear_log()

        imported, total = self.controller.update_universe()

        self.log(f"✅ Imported {imported} stocks")

        self.activity_panel.set_progress(100)

        self.activity_panel.set_status("Ready")

        self.refresh_statistics()

    # ----------------------------------------------------------

    def download_prices(self):

        self.activity_panel.set_status("Downloading prices...")
        self.activity_panel.set_progress(10)

        self.activity_panel.clear_log()

        results, total = self.controller.download_prices()

        for ticker, rows in results.items():

            self.log(f"✓ {ticker}: {rows} rows")

        self.activity_panel.set_progress(100)

        self.activity_panel.set_status("Ready")

        self.refresh_statistics()

        self.log("")
        self.log(f"Database Rows: {total:,}")

    # ----------------------------------------------------------

    def calculate_indicators(self):

        self.activity_panel.set_status("Calculating indicators...")
        self.activity_panel.set_progress(20)

        self.activity_panel.clear_log()

        results = self.indicator_controller.calculate_indicators()

        self.activity_panel.set_progress(100)

        self.activity_panel.set_status("Ready")

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

        self.activity_panel.set_status("Detecting support...")
        self.activity_panel.set_progress(20)

        self.activity_panel.clear_log()

        results = self.support_controller.detect_support()

        self.activity_panel.set_progress(100)

        self.activity_panel.set_status("Ready")

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

        self.activity_panel.set_status("Validating bounces...")
        self.activity_panel.set_progress(20)

        self.activity_panel.clear_log()

        results = self.bounce_controller.validate_bounces()

        self.activity_panel.set_progress(100)

        self.activity_panel.set_status("Ready")

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

        self.activity_panel.set_status("Running screener...")
        self.activity_panel.set_progress(10)

        self.activity_panel.clear_log()

        self.activity_panel.set_status("Processing candidates...")
        self.activity_panel.set_progress(50)

        results = self.scoring_controller.run_screener()

        self.candidates_by_ticker = {
            candidate.ticker: candidate
            for candidate in results["candidates"]
        }
        self.candidates_table.populate(results["candidates"])
        self.update_open_detail_state()

        self.activity_panel.set_progress(100)

        self.activity_panel.set_status("Screener Complete")

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
                f"{highest.primary_score_value:.1f}"
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

    def open_selected_stock_detail(self):

        ticker = self.candidates_table.selected_ticker()

        if ticker is None:
            return

        self.open_stock_detail(ticker)

    # ----------------------------------------------------------

    def update_open_detail_state(self, *args):

        ticker = self.candidates_table.selected_ticker()

        self.operations_toolbar.set_open_detail_enabled(ticker is not None)
        self.update_research_preview(ticker)
        self.update_price_chart(ticker)

    # ----------------------------------------------------------

    def update_research_preview(self, ticker):

        if ticker is None:
            self.research_preview.clear()
            return

        self.research_preview.set_candidate(self.candidates_by_ticker.get(ticker))

    # ----------------------------------------------------------

    def update_price_chart(self, ticker):

        if ticker is None:
            self.price_chart.clear()
            return

        try:
            chart_data = self.chart_controller.get_chart_data(ticker)
        except Exception:
            self.price_chart.set_chart_data(
                {
                    "ticker": ticker,
                    "prices": [],
                    "indicators": [],
                    "support_zones": [],
                    "bounce_validations": [],
                    "warnings": ["Chart data unavailable"],
                }
            )
            return

        self.price_chart.set_chart_data(chart_data)

    # ----------------------------------------------------------

    def highest_candidate(self, candidates):

        if not candidates:
            return None

        return max(
            candidates,
            key=lambda candidate: candidate.primary_score_value,
        )

    # ----------------------------------------------------------

    def average_candidate_score(self, candidates):

        if not candidates:
            return 0.0

        total = sum(
            candidate.primary_score_value
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
        self.chart_controller.close()

        super().closeEvent(event)
