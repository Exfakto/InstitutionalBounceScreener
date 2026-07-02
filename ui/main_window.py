import sys
from datetime import datetime, timedelta

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from controllers.market_controller import MarketController
from controllers.indicator_controller import IndicatorController
from controllers.support_controller import SupportController
from controllers.bounce_controller import BounceController
from controllers.scoring_controller import ScoringController
from controllers.chart_controller import ChartController
from controllers.watchlist_controller import WatchlistController
from controllers.trade_journal_controller import TradeJournalController
from services.market_status_service import MarketStatusService
from services.refresh_scheduler import RefreshScheduler

from ui.widgets.activity_panel import ActivityPanel
from ui.widgets.candidate_table import CandidateTable
from ui.widgets.kpi_strip import KpiStrip
from ui.widgets.operations_toolbar import OperationsToolbar
from ui.widgets.header_bar import HeaderBar
from ui.widgets.price_chart import PriceChart
from ui.widgets.research_preview import ResearchPreview
from ui.widgets.trade_card import TradeCard
from ui.widgets.watchlist_panel import WatchlistPanel
from ui.widgets.trade_journal_panel import TradeJournalPanel
from ui.widgets.performance_dashboard import PerformanceDashboard
from ui.stock_detail_window import StockDetailWindow
from ui.export_dialog import ExportDialog
from ui.settings_dialog import SettingsDialog
from ui.about_dialog import AboutDialog


class MainWindow(QMainWindow):

    LIVE_REFRESH_INTERVALS = {
        "Open": 300,
        "Pre-market": 600,
        "After-hours": 900,
        "Closed": 1800,
    }

    SHORTCUT_ACTIONS = (
        ("run_screener_action", "Run Screener", "Ctrl+R", "run_screener"),
        ("update_universe_action", "Update Universe", "Ctrl+U", "update_universe"),
        ("download_prices_action", "Download Prices", "Ctrl+D", "download_prices"),
        (
            "calculate_indicators_action",
            "Calculate Indicators",
            "Ctrl+I",
            "calculate_indicators",
        ),
        ("detect_support_action", "Detect Support", "Ctrl+S", "detect_support"),
        (
            "validate_bounces_action",
            "Validate Bounces",
            "Ctrl+B",
            "validate_bounces",
        ),
        (
            "open_detail_action",
            "Open Selected Stock Detail",
            "Ctrl+O",
            "open_selected_stock_detail",
        ),
        (
            "add_watchlist_action",
            "Add Selected Candidate to Watchlist",
            "Ctrl+W",
            "add_selected_candidate_to_watchlist",
        ),
        ("export_center_action", "Open Export Center", "Ctrl+E", "open_export_dialog"),
        ("settings_action", "Open Settings", "Ctrl+,", "open_settings_dialog"),
        ("about_action", "Open About & Diagnostics", "F1", "open_about_dialog"),
        ("clear_selection_action", "Clear Selection", "Escape", "clear_current_selection"),
    )

    def __init__(self):
        super().__init__()

        self.controller = MarketController()
        self.indicator_controller = IndicatorController()
        self.support_controller = SupportController()
        self.bounce_controller = BounceController()
        self.scoring_controller = ScoringController()
        self.chart_controller = ChartController()
        self.watchlist_controller = WatchlistController()
        self.trade_journal_controller = TradeJournalController()
        self.market_status_service = MarketStatusService()
        self.refresh_scheduler = RefreshScheduler()
        self.refresh_scheduler.register_callback(self.handle_live_refresh_result)
        self.last_refresh_at = None
        self.next_refresh_at = None
        self.candidates_by_ticker = {}

        self.setWindowTitle("Institutional Bounce Screener")
        self.resize(1600, 900)

        self.build_ui()
        self.register_shortcuts()

        self.refresh_statistics()
        self.configure_live_refresh()

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
        # Statistics
        ##########################################################

        self.kpi_strip = KpiStrip()

        main_layout.addWidget(self.kpi_strip)

        ##########################################################
        # Main Workspace
        ##########################################################

        self.candidates_table = CandidateTable()
        self.candidates_table.ticker_double_clicked.connect(self.open_stock_detail)
        self.candidates_table.selectionModel().selectionChanged.connect(
            self.update_open_detail_state
        )

        self.price_chart = PriceChart()
        self.research_preview = ResearchPreview()
        self.trade_card = TradeCard()
        self.watchlist_panel = WatchlistPanel()
        self.watchlist_panel.add_selected_candidate_requested.connect(
            self.add_selected_candidate_to_watchlist
        )
        self.watchlist_panel.remove_selected_requested.connect(
            self.remove_selected_watchlist_item
        )
        self.watchlist_panel.refresh_requested.connect(self.refresh_watchlist)
        self.trade_journal_panel = TradeJournalPanel()
        self.trade_journal_panel.new_trade_requested.connect(
            self.create_selected_candidate_trade
        )
        self.trade_journal_panel.close_trade_requested.connect(
            self.close_selected_trade
        )
        self.trade_journal_panel.delete_trade_requested.connect(
            self.delete_selected_trade
        )
        self.trade_journal_panel.refresh_requested.connect(self.refresh_trade_journal)
        self.performance_dashboard = PerformanceDashboard()
        self.activity_panel = ActivityPanel()

        self.workspace_splitter = QSplitter(Qt.Vertical)
        self.workspace_splitter.setObjectName("MainWorkspaceSplitter")
        self.workspace_splitter.setChildrenCollapsible(False)

        self.center_splitter = QSplitter(Qt.Horizontal)
        self.center_splitter.setObjectName("CenterWorkspaceSplitter")
        self.center_splitter.setChildrenCollapsible(False)

        self.price_chart.setMinimumSize(720, 360)
        self.research_preview.setMinimumWidth(360)
        self.trade_card.setMinimumWidth(360)

        self.decision_panel = QWidget()
        self.decision_panel.setObjectName("DecisionPanel")
        decision_layout = QVBoxLayout(self.decision_panel)
        decision_layout.setContentsMargins(0, 0, 0, 0)
        decision_layout.setSpacing(10)
        decision_layout.addWidget(self.research_preview, stretch=3)
        decision_layout.addWidget(self.trade_card, stretch=2)

        self.center_splitter.addWidget(self.price_chart)
        self.center_splitter.addWidget(self.decision_panel)
        self.center_splitter.setStretchFactor(0, 65)
        self.center_splitter.setStretchFactor(1, 35)
        self.center_splitter.setSizes([1040, 560])

        self.bottom_splitter = QSplitter(Qt.Horizontal)
        self.bottom_splitter.setObjectName("BottomWorkspaceSplitter")
        self.bottom_splitter.setChildrenCollapsible(False)

        self.bottom_left_tabs = QTabWidget()
        self.bottom_left_tabs.setObjectName("BottomLeftTabs")
        self.bottom_left_tabs.setMinimumSize(720, 220)
        self.bottom_left_tabs.addTab(self.candidates_table, "Candidates")
        self.bottom_left_tabs.addTab(self.watchlist_panel, "Watchlist")
        self.bottom_left_tabs.addTab(self.performance_dashboard, "Portfolio")
        self.bottom_left_tabs.addTab(self.trade_journal_panel, "Trade Journal")

        self.bottom_right_tabs = QTabWidget()
        self.bottom_right_tabs.setObjectName("BottomRightTabs")
        self.bottom_right_tabs.setMinimumSize(360, 220)
        self.bottom_right_tabs.addTab(self.activity_panel, "Activity")

        self.bottom_splitter.addWidget(self.bottom_left_tabs)
        self.bottom_splitter.addWidget(self.bottom_right_tabs)
        self.bottom_splitter.setStretchFactor(0, 65)
        self.bottom_splitter.setStretchFactor(1, 35)
        self.bottom_splitter.setSizes([1040, 560])

        self.workspace_splitter.addWidget(self.center_splitter)
        self.workspace_splitter.addWidget(self.bottom_splitter)
        self.workspace_splitter.setStretchFactor(0, 3)
        self.workspace_splitter.setStretchFactor(1, 1)
        self.workspace_splitter.setSizes([600, 260])

        main_layout.addWidget(self.workspace_splitter, stretch=1)
        self.refresh_watchlist()
        self.refresh_trade_journal()

    # ----------------------------------------------------------

    def log(self, text):

        self.activity_panel.append_log(text)

        QApplication.processEvents()

    # ----------------------------------------------------------

    def register_shortcuts(self):

        if hasattr(self, "shortcut_actions"):
            return

        self.shortcut_actions = {}

        for attribute_name, text, shortcut, handler_name in self.SHORTCUT_ACTIONS:
            action = QAction(text, self)
            action.setShortcut(QKeySequence(shortcut))
            action.setShortcutContext(Qt.ApplicationShortcut)
            action.triggered.connect(
                lambda checked=False, name=handler_name: self.invoke_shortcut(name)
            )
            self.addAction(action)
            self.shortcut_actions[attribute_name] = action
            setattr(self, attribute_name, action)

    # ----------------------------------------------------------

    def invoke_shortcut(self, handler_name):

        handler = getattr(self, handler_name, None)

        if callable(handler):
            handler()

    # ----------------------------------------------------------

    def open_export_dialog(self):

        self.export_dialog = ExportDialog(self)
        self.export_dialog.exec()

    # ----------------------------------------------------------

    def open_settings_dialog(self):

        self.settings_dialog = SettingsDialog(parent=self)
        self.settings_dialog.exec()

    # ----------------------------------------------------------

    def open_about_dialog(self):

        self.about_dialog = AboutDialog(parent=self)
        self.about_dialog.exec()

    # ----------------------------------------------------------

    def clear_current_selection(self):

        active_modal = QApplication.activeModalWidget()

        if active_modal is not None and active_modal is not self:
            reject = getattr(active_modal, "reject", None)

            if callable(reject):
                reject()
            else:
                active_modal.close()

            return

        if hasattr(self, "candidates_table"):
            clear_selection = getattr(self.candidates_table, "clearSelection", None)

            if callable(clear_selection):
                clear_selection()

        self.update_open_detail_state()

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

        self.mark_refresh_completed()

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
        self.register_refresh_tickers(results["candidates"])
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
            self.update_trade_card(None)
            return

        candidate = self.candidates_by_ticker.get(ticker)
        self.research_preview.set_candidate(candidate)
        self.update_trade_card(candidate)

    # ----------------------------------------------------------

    def update_trade_card(self, candidate):

        if not hasattr(self, "trade_card"):
            return

        if candidate is None:
            self.trade_card.clear()
            return

        trade_card = ResearchPreview.trade_card_for_candidate(candidate)

        if trade_card is None:
            self.trade_card.set_placeholder("No trade plan available.")
            return

        self.trade_card.set_trade_card(trade_card)

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

    def add_selected_candidate_to_watchlist(self):

        ticker = self.candidates_table.selected_ticker()

        if ticker is None:
            return

        candidate = self.candidates_by_ticker.get(ticker)
        result = self.watchlist_controller.add_candidate(
            ticker,
            company_name=self.company_name_for_candidate(candidate),
        )

        if result.get("success"):
            self.refresh_watchlist()

        self.log(result.get("message", "Watchlist update complete."))

    # ----------------------------------------------------------

    def remove_selected_watchlist_item(self):

        item_id = self.watchlist_panel.selected_item_id()

        if item_id is None:
            return

        result = self.watchlist_controller.remove_item(item_id)

        if result.get("success"):
            self.refresh_watchlist()

        self.log(result.get("message", "Watchlist update complete."))

    # ----------------------------------------------------------

    def refresh_watchlist(self):

        if not hasattr(self, "watchlist_panel"):
            return

        result = self.watchlist_controller.get_items()

        if result.get("success"):
            self.watchlist_panel.refresh_items(result.get("item") or [])
        else:
            self.watchlist_panel.clear()

    # ----------------------------------------------------------

    def create_selected_candidate_trade(self):

        ticker = self.candidates_table.selected_ticker()

        if ticker is None:
            return

        candidate = self.candidates_by_ticker.get(ticker)
        result = self.trade_journal_controller.create_trade(
            ticker=ticker,
            company_name=self.company_name_for_candidate(candidate),
        )

        if result.get("success"):
            self.refresh_trade_journal()

        self.log(result.get("message", "Trade journal update complete."))

    # ----------------------------------------------------------

    def close_selected_trade(self):

        trade_id = self.trade_journal_panel.selected_trade()

        if trade_id is None:
            return

        result = self.trade_journal_controller.close_trade(trade_id)

        if result.get("success"):
            self.refresh_trade_journal()

        self.log(result.get("message", "Trade journal update complete."))

    # ----------------------------------------------------------

    def delete_selected_trade(self):

        trade_id = self.trade_journal_panel.selected_trade()

        if trade_id is None:
            return

        result = self.trade_journal_controller.delete_trade(trade_id)

        if result.get("success"):
            self.refresh_trade_journal()

        self.log(result.get("message", "Trade journal update complete."))

    # ----------------------------------------------------------

    def refresh_trade_journal(self):

        if not hasattr(self, "trade_journal_panel"):
            return

        result = self.trade_journal_controller.get_trades()

        if result.get("success"):
            self.trade_journal_panel.refresh_trades(result.get("trades") or [])
        else:
            self.trade_journal_panel.clear()

    # ----------------------------------------------------------

    def configure_live_refresh(self, now=None):

        market_status = self.market_status_service.get_status(now)
        interval = self.refresh_interval_for_status(market_status.status)

        if interval is None:
            self.refresh_scheduler.stop()
            self.next_refresh_at = None
            self.update_refresh_status_header(market_status)
            return market_status

        self.refresh_scheduler.set_refresh_interval(interval)
        self.refresh_scheduler.start()
        self.next_refresh_at = self.next_refresh_time(interval, now=now)
        self.update_refresh_status_header(market_status)

        return market_status

    # ----------------------------------------------------------

    def register_refresh_tickers(self, candidates):

        if not hasattr(self, "refresh_scheduler"):
            return

        self.refresh_scheduler.clear_tickers()

        for candidate in candidates:
            ticker = self.ticker_for_candidate(candidate)

            if ticker is not None:
                self.refresh_scheduler.register_ticker(ticker)

    # ----------------------------------------------------------

    @classmethod
    def refresh_interval_for_status(cls, status):

        return cls.LIVE_REFRESH_INTERVALS.get(status)

    # ----------------------------------------------------------

    def update_refresh_status_header(self, market_status=None):

        if not hasattr(self, "header_bar"):
            return

        if market_status is None:
            market_status = self.market_status_service.get_status()

        interval = self.refresh_interval_for_status(market_status.status)
        is_running = (
            self.refresh_scheduler.is_running()
            if hasattr(self.refresh_scheduler, "is_running")
            else False
        )

        self.header_bar.set_refresh_status(
            market_status=market_status.status,
            auto_refresh=is_running,
            refresh_interval=interval if is_running else None,
            last_refresh=self.last_refresh_at,
            next_refresh=self.next_refresh_at if is_running else None,
        )

    # ----------------------------------------------------------

    def mark_refresh_completed(self, when=None):

        self.last_refresh_at = self.current_refresh_time(when)
        interval = getattr(self.refresh_scheduler, "refresh_interval", None)

        if self.refresh_scheduler.is_running() and interval is not None:
            self.next_refresh_at = self.next_refresh_time(interval, now=self.last_refresh_at)

        self.update_refresh_status_header()

    # ----------------------------------------------------------

    def handle_live_refresh_result(self, ticker, result):

        self.mark_refresh_completed()
        self.refresh_visible_watchlist_quotes()

    # ----------------------------------------------------------

    def refresh_visible_watchlist_quotes(self):

        if not hasattr(self, "watchlist_panel"):
            return

        market_status = self.market_status_service.get_status()

        if market_status.status not in {"Open", "Pre-market", "After-hours"}:
            return

        tickers = self.watchlist_panel.visible_tickers()

        if not tickers:
            return

        result = self.watchlist_controller.refresh_watchlist(tickers)
        self.watchlist_panel.update_quotes(result.get("quotes") or {})

    # ----------------------------------------------------------

    @classmethod
    def next_refresh_time(cls, interval, now=None):

        return cls.current_refresh_time(now) + timedelta(seconds=interval)

    # ----------------------------------------------------------

    @staticmethod
    def current_refresh_time(value=None):

        if value is None:
            return datetime.now().astimezone()

        if isinstance(value, datetime):
            return value

        return datetime.now().astimezone()

    # ----------------------------------------------------------

    @staticmethod
    def ticker_for_candidate(candidate):

        if candidate is None:
            return None

        if isinstance(candidate, dict):
            return candidate.get("ticker")

        return getattr(candidate, "ticker", None)

    # ----------------------------------------------------------

    @staticmethod
    def company_name_for_candidate(candidate):

        if candidate is None:
            return None

        if isinstance(candidate, dict):
            return (
                candidate.get("company_name")
                or candidate.get("company")
                or candidate.get("name")
            )

        return (
            getattr(candidate, "company_name", None)
            or getattr(candidate, "company", None)
            or getattr(candidate, "name", None)
        )

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

        if hasattr(self, "refresh_scheduler"):
            self.refresh_scheduler.stop()

        self.controller.close()
        self.indicator_controller.close()
        self.support_controller.close()
        self.bounce_controller.close()
        self.scoring_controller.close()
        self.chart_controller.close()

        super().closeEvent(event)
