import sys
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDockWidget,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSplitter,
    QStatusBar,
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
from controllers.screener_preset_controller import ScreenerPresetController
from controllers.dashboard_controller import DashboardController
from controllers.results_export_controller import ResultsExportController
from backtesting.signal_validation import BacktestConfig
from backtesting.signal_validation import BacktestEngine as SignalBacktestEngine
from services.market_status_service import MarketStatusService
from services.refresh_scheduler import RefreshScheduler
from services.settings_service import SettingsService
from services.app_settings_service import AppSettingsService
from services.chart_analytics_service import ChartAnalyticsService
from services.data_quality_service import DataQualityService
from services.market_data_cache_service import MarketDataCacheService
from services.market_data_refresh_service import MarketDataRefreshService
from services.provider_diagnostics_service import ProviderDiagnosticsService
from services.scan_preset_service import ScanPresetService
from services.universe_scan_adapter import UniverseScanAdapter
from services.workspace_state_service import WorkspaceStateService

from ui.widgets.activity_panel import ActivityPanel
from ui.widgets.candidate_table import CandidateTable
from ui.widgets.dashboard import InstitutionalDashboard
from ui.widgets.kpi_strip import KpiStrip
from ui.widgets.operations_toolbar import OperationsToolbar
from ui.widgets.header_bar import HeaderBar
from ui.widgets.pipeline_progress_panel import PipelineProgressPanel
from ui.widgets.price_chart import PriceChart
from ui.widgets.research_preview import ResearchPreview
from ui.widgets.screening_results_panel import ScreeningResultsPanel
from ui.widgets.trade_card import TradeCard
from ui.widgets.watchlist_panel import WatchlistPanel
from ui.widgets.trade_journal_panel import TradeJournalPanel
from ui.widgets.performance_dashboard import PerformanceDashboard
from ui.candidate_detail_window import CandidateDetailWindow
from ui.stock_detail_window import StockDetailWindow
from ui.export_dialog import ExportDialog
from ui.screening_worker import ScreeningWorker
from ui.settings_dialog import SettingsDialog
from ui.about_dialog import AboutDialog
from ui.design_system import DashboardDesignSystem as DesignSystem


class MainWindow(QMainWindow):

    DEFAULT_WORKSPACE_LAYOUT = "Default"
    MAX_UNIVERSE_SCAN_TICKERS = 250
    RESULTS_PAGE_SIZE = 100
    RUN_HISTORY_PAGE_SIZE = 50

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
        self.screener_preset_controller = ScreenerPresetController()
        self.market_status_service = MarketStatusService()
        self.settings_service = SettingsService()
        self.app_settings_service = AppSettingsService()
        self.app_preferences = self.load_app_preferences()
        self.scan_preset_service = ScanPresetService()
        self.workspace_state_service = WorkspaceStateService()
        self.refresh_scheduler = RefreshScheduler()
        self.refresh_scheduler.register_callback(self.handle_live_refresh_result)
        self.dashboard_controller = DashboardController(
            market_controller=self.controller,
            watchlist_controller=self.watchlist_controller,
            market_status_service=self.market_status_service,
            settings_service=self.settings_service,
        )
        self.last_refresh_at = None
        self.next_refresh_at = None
        self.latest_statistics = {}
        self.candidates_by_ticker = {}
        self.active_workspace_layout = self.DEFAULT_WORKSPACE_LAYOUT
        self.selected_results_run_id = None
        self.ranked_candidates_offset = 0
        self.ranked_candidates_total_count = 0
        self.run_history_offset = 0
        self.run_history_total_count = 0
        self.data_refresh_cancel_requested = False

        self.setWindowTitle("Institutional Bounce Screener")
        self.resize(1600, 900)

        self.build_ui()
        self.restore_workspace_state()
        self.register_shortcuts()

        self.refresh_statistics()
        self.configure_live_refresh()
        self.add_activity("Dashboard ready", status="success")

    # ----------------------------------------------------------

    def build_ui(self):

        central = QWidget()
        central.setObjectName("MainWorkspace")
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(
            DesignSystem.Spacing.XL,
            DesignSystem.Spacing.LG,
            DesignSystem.Spacing.XL,
            DesignSystem.Spacing.LG,
        )
        main_layout.setSpacing(DesignSystem.Spacing.LG)

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

        self.dashboard_summary_panel = self.build_dashboard_summary_panel()
        main_layout.addWidget(self.dashboard_summary_panel)

        ##########################################################
        # Pipeline Actions
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
        self.operations_toolbar.save_preset_requested.connect(self.save_screener_preset)
        self.operations_toolbar.load_preset_requested.connect(self.load_screener_preset)
        self.operations_toolbar.reset_filters_requested.connect(self.reset_screener_filters)
        self.operations_toolbar.refresh_results_requested.connect(
            self.refresh_dashboard_results
        )
        self.operations_toolbar.open_detail_requested.connect(
            self.open_selected_stock_detail
        )

        main_layout.addWidget(self.operations_toolbar)

        ##########################################################
        # Pipeline Progress
        ##########################################################

        self.pipeline_progress_panel = PipelineProgressPanel()

        ##########################################################
        # Activity Feed
        ##########################################################

        self.dashboard = InstitutionalDashboard()
        self.dashboard.setMinimumHeight(180)
        self.dashboard.setMaximumHeight(280)

        ##########################################################
        # Main Workspace
        ##########################################################

        self.candidates_table = CandidateTable()
        self.candidates_table.ticker_double_clicked.connect(self.open_stock_detail)
        self.candidates_table.detail_requested.connect(self.open_stock_detail)
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
        self.screening_results_panel = ScreeningResultsPanel()
        self.screening_results_panel.refresh_ranked_candidates_requested.connect(
            self.refresh_ranked_candidates_view
        )
        self.screening_results_panel.refresh_run_history_requested.connect(
            self.refresh_screening_run_history_view
        )
        self.screening_results_panel.load_more_ranked_candidates_requested.connect(
            self.load_more_ranked_candidates_view
        )
        self.screening_results_panel.load_more_run_history_requested.connect(
            self.load_more_screening_run_history_view
        )
        self.screening_results_panel.run_selected.connect(
            self.load_ranked_candidates_for_run
        )
        self.screening_results_panel.candidate_selected.connect(
            self.update_results_candidate_chart
        )
        self.screening_results_panel.export_candidates_csv_requested.connect(
            self.export_ranked_candidates_csv
        )
        self.screening_results_panel.export_candidates_json_requested.connect(
            self.export_ranked_candidates_json
        )
        self.screening_results_panel.export_full_run_package_requested.connect(
            self.export_full_run_package_json
        )
        self.screening_results_panel.run_screening_requested.connect(
            self.start_screening_from_input
        )
        self.screening_results_panel.cancel_screening_requested.connect(
            self.cancel_screening
        )
        self.screening_results_panel.screening_mode_changed.connect(
            self.handle_screening_mode_changed
        )
        self.screening_results_panel.scan_preset_changed.connect(
            self.handle_scan_preset_changed
        )
        self.screening_results_panel.refresh_selected_ticker_requested.connect(
            self.refresh_selected_market_data_ticker
        )
        self.screening_results_panel.refresh_ticker_list_requested.connect(
            self.refresh_market_data_ticker_list
        )
        self.screening_results_panel.refresh_universe_symbols_requested.connect(
            self.refresh_market_data_universe_symbols
        )
        self.screening_results_panel.cancel_data_refresh_requested.connect(
            self.cancel_market_data_refresh
        )
        self.screening_results_panel.clear_cache_ticker_requested.connect(
            self.clear_market_data_cache_ticker
        )
        self.screening_results_panel.clear_all_cache_requested.connect(
            self.clear_all_market_data_cache
        )
        self.screening_results_panel.provider_diagnostics_requested.connect(
            self.run_provider_diagnostics
        )
        self.screening_results_panel.data_quality_report_requested.connect(
            self.show_data_quality_report
        )
        self.screening_results_panel.run_backtest_requested.connect(
            self.run_backtest_from_results
        )
        self.screening_results_panel.cancel_backtest_requested.connect(
            self.cancel_backtest
        )
        self.screening_results_panel.set_scan_presets(
            self.scan_preset_service.list_presets()
        )
        self.apply_app_preferences_to_ui()
        self.update_scan_preset_summary()
        self.activity_panel = ActivityPanel()

        self.screener_filters_panel = self.build_screener_filters_panel()

        self.screener_workspace_splitter = QSplitter(Qt.Horizontal)
        self.screener_workspace_splitter.setObjectName("ScreenerWorkspaceSplitter")
        self.screener_workspace_splitter.setChildrenCollapsible(False)
        self.workspace_splitter = self.screener_workspace_splitter
        self.center_splitter = self.screener_workspace_splitter

        self.price_chart.setMinimumSize(520, 280)
        self.candidates_table.setMinimumSize(620, 320)
        self.screener_filters_panel.setMinimumWidth(190)
        self.screener_filters_panel.setMaximumWidth(260)
        self.research_preview.setMinimumWidth(300)
        self.trade_card.setMinimumWidth(300)

        self.screener_workspace_splitter.addWidget(self.screener_filters_panel)
        self.screener_workspace_splitter.addWidget(self.candidates_table)
        self.screener_workspace_splitter.setStretchFactor(0, 14)
        self.screener_workspace_splitter.setStretchFactor(1, 86)
        self.screener_workspace_splitter.setSizes([220, 1280])

        main_layout.addWidget(self.screener_workspace_splitter, stretch=4)
        main_layout.addWidget(self.pipeline_progress_panel)
        main_layout.addWidget(self.dashboard, stretch=1)
        self.create_workspace_docks()
        self.apply_default_dock_layout()
        self.build_screener_status_bar()
        self.refresh_dashboard()
        self.refresh_watchlist()
        self.refresh_trade_journal()
        self.refresh_ranked_candidates_view()
        self.refresh_screening_run_history_view()
        self.refresh_cache_coverage_summary()

    # ----------------------------------------------------------

    def build_dashboard_summary_panel(self):

        panel = QFrame()
        panel.setObjectName("ResearchPreviewSection")
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(
            DesignSystem.Spacing.LG,
            DesignSystem.Spacing.MD,
            DesignSystem.Spacing.LG,
            DesignSystem.Spacing.MD,
        )
        layout.setSpacing(DesignSystem.Spacing.XL)

        self.dashboard_summary_labels = {}

        for key, title in [
            ("total_stocks_loaded", "Total Stocks Loaded"),
            ("stocks_passing_filters", "Stocks Passing Current Filters"),
            ("last_refresh_time", "Last Refresh Time"),
            ("database_name", "Current Database Name"),
        ]:
            container = QWidget()
            item_layout = QVBoxLayout(container)
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(DesignSystem.Spacing.XS)

            label = QLabel(title)
            label.setObjectName("ResearchPreviewFieldLabel")
            value = QLabel("N/A")
            value.setObjectName("ResearchPreviewFieldValue")
            value.setTextInteractionFlags(Qt.TextSelectableByMouse)

            item_layout.addWidget(label)
            item_layout.addWidget(value)
            layout.addWidget(container)
            self.dashboard_summary_labels[key] = value

        layout.addStretch()

        self.dashboard_status_label = QLabel("No results available")
        self.dashboard_status_label.setObjectName("EmptyStateLabel")
        self.dashboard_status_label.setAlignment(Qt.AlignCenter)
        self.dashboard_status_label.setMinimumWidth(220)
        layout.addWidget(self.dashboard_status_label)
        return panel

    # ----------------------------------------------------------

    def build_screener_filters_panel(self):

        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.filter_sections = {}
        for title, fields in [
            ("Universe", ["Universe"]),
            ("Fundamentals", ["Revenue Growth", "EPS Growth"]),
            ("Institutional", ["Institutional Score", "Ownership"]),
            ("Technical", ["Technical Score", "Support"]),
            ("Risk", ["Risk/Reward", "Warnings"]),
        ]:
            section = QGroupBox(title)
            section.setCheckable(True)
            section.setChecked(True)
            section.setObjectName("ScreenerFilterSection")
            form = QFormLayout(section)
            form.setContentsMargins(12, 18, 12, 12)
            form.setVerticalSpacing(9)
            for field in fields:
                control = QComboBox()
                control.addItems(["Any", "Low", "Moderate", "High"])
                form.addRow(field, control)
            self.filter_sections[title] = section
            layout.addWidget(section)

        layout.addStretch()
        return panel

    # ----------------------------------------------------------

    def build_screener_status_bar(self):

        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        self.market_status_status = QLabel("Market: --")
        self.active_provider_status = QLabel("Provider: --")
        self.database_status = QLabel("Database: --")
        self.last_refresh_status = QLabel("Last refresh: --")
        self.last_sync_status = QLabel("Last sync: --")
        self.candidate_count_status = QLabel("Candidate count: 0")
        self.selected_ticker_status = QLabel("Selected ticker: --")
        self.active_preset_status = QLabel("Active preset: --")
        self.workspace_state_status = QLabel("Workspace: --")
        self.last_screen_time_status = self.last_refresh_status

        for label in [
            self.market_status_status,
            self.active_provider_status,
            self.database_status,
            self.last_refresh_status,
            self.last_sync_status,
            self.candidate_count_status,
            self.selected_ticker_status,
            self.active_preset_status,
            self.workspace_state_status,
        ]:
            label.setObjectName("StatusBarLabel")
            status_bar.addPermanentWidget(label)

        self.update_screener_status()

    # ----------------------------------------------------------

    def create_workspace_docks(self):

        self.workspace_docks = {
            "chart": self.create_dock("Chart", self.price_chart),
            "research": self.create_dock("Research", self.research_preview),
            "trade_card": self.create_dock("Trade Card", self.trade_card),
            "watchlist": self.create_dock("Watchlist", self.watchlist_panel),
            "activity": self.create_dock("Activity", self.activity_panel),
            "portfolio": self.create_dock("Portfolio", self.performance_dashboard),
            "results": self.create_dock("Results", self.screening_results_panel),
        }

        self.chart_dock = self.workspace_docks["chart"]
        self.research_dock = self.workspace_docks["research"]
        self.trade_card_dock = self.workspace_docks["trade_card"]
        self.watchlist_dock = self.workspace_docks["watchlist"]
        self.activity_dock = self.workspace_docks["activity"]
        self.portfolio_dock = self.workspace_docks["portfolio"]
        self.results_dock = self.workspace_docks["results"]

    # ----------------------------------------------------------

    def create_dock(self, title, widget):

        dock = QDockWidget(title, self)
        dock.setObjectName(f"{title.replace(' ', '')}Dock")
        dock.setWidget(widget)
        dock.setAllowedAreas(Qt.AllDockWidgetAreas)
        dock.setFeatures(
            QDockWidget.DockWidgetMovable
            | QDockWidget.DockWidgetFloatable
            | QDockWidget.DockWidgetClosable
        )
        self.addDockWidget(Qt.RightDockWidgetArea, dock)
        return dock

    # ----------------------------------------------------------

    def apply_default_dock_layout(self):

        self.active_workspace_layout = "Default"
        self.set_docks_floating(False)
        self.show_workspace_docks(
            {
                "chart": True,
                "research": True,
                "trade_card": True,
                "watchlist": True,
                "activity": True,
                "portfolio": True,
                "results": True,
            }
        )
        self.addDockWidget(Qt.RightDockWidgetArea, self.chart_dock)
        self.splitDockWidget(self.chart_dock, self.research_dock, Qt.Vertical)
        self.splitDockWidget(self.research_dock, self.trade_card_dock, Qt.Vertical)

        self.addDockWidget(Qt.BottomDockWidgetArea, self.watchlist_dock)
        self.splitDockWidget(self.watchlist_dock, self.activity_dock, Qt.Horizontal)
        self.tabifyDockWidget(self.activity_dock, self.portfolio_dock)
        self.tabifyDockWidget(self.portfolio_dock, self.results_dock)
        self.activity_dock.raise_()

        self.resizeDocks(
            [self.chart_dock, self.research_dock, self.trade_card_dock],
            [360, 280, 220],
            Qt.Vertical,
        )
        self.resizeDocks(
            [self.watchlist_dock, self.activity_dock],
            [980, 460],
            Qt.Horizontal,
        )

    # ----------------------------------------------------------

    def apply_default_layout(self):

        self.apply_default_dock_layout()
        self.screener_workspace_splitter.setSizes([300, 1100])
        self.update_screener_status(workspace_state="Default layout")

    # ----------------------------------------------------------

    def apply_research_layout(self):

        self.active_workspace_layout = "Research"
        self.set_docks_floating(False)
        self.show_workspace_docks(
            {
                "chart": True,
                "research": True,
                "trade_card": False,
                "watchlist": True,
                "activity": True,
                "portfolio": False,
                "results": True,
            }
        )
        self.addDockWidget(Qt.RightDockWidgetArea, self.research_dock)
        self.splitDockWidget(self.research_dock, self.chart_dock, Qt.Vertical)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.watchlist_dock)
        self.splitDockWidget(self.watchlist_dock, self.activity_dock, Qt.Horizontal)
        self.research_dock.raise_()
        self.screener_workspace_splitter.setSizes([240, 1160])
        self.resizeDocks(
            [self.research_dock, self.chart_dock],
            [520, 300],
            Qt.Vertical,
        )
        self.resizeDocks(
            [self.watchlist_dock, self.activity_dock],
            [340, 900],
            Qt.Horizontal,
        )
        self.update_screener_status(workspace_state="Research layout")

    # ----------------------------------------------------------

    def apply_trading_layout(self):

        self.active_workspace_layout = "Trading"
        self.set_docks_floating(False)
        self.show_workspace_docks(
            {
                "chart": True,
                "research": True,
                "trade_card": True,
                "watchlist": True,
                "activity": False,
                "portfolio": True,
                "results": True,
            }
        )
        self.addDockWidget(Qt.RightDockWidgetArea, self.chart_dock)
        self.splitDockWidget(self.chart_dock, self.research_dock, Qt.Horizontal)
        self.splitDockWidget(self.research_dock, self.trade_card_dock, Qt.Vertical)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.watchlist_dock)
        self.tabifyDockWidget(self.watchlist_dock, self.portfolio_dock)
        self.tabifyDockWidget(self.portfolio_dock, self.results_dock)
        self.chart_dock.raise_()
        self.screener_workspace_splitter.setSizes([260, 1140])
        self.resizeDocks(
            [self.chart_dock, self.research_dock],
            [760, 420],
            Qt.Horizontal,
        )
        self.resizeDocks(
            [self.research_dock, self.trade_card_dock],
            [360, 260],
            Qt.Vertical,
        )
        self.update_screener_status(workspace_state="Trading layout")

    # ----------------------------------------------------------

    def apply_compact_layout(self):

        self.active_workspace_layout = "Compact"
        self.set_docks_floating(False)
        self.show_workspace_docks(
            {
                "chart": True,
                "research": True,
                "trade_card": False,
                "watchlist": False,
                "activity": False,
                "portfolio": False,
                "results": False,
            }
        )
        self.addDockWidget(Qt.RightDockWidgetArea, self.chart_dock)
        self.tabifyDockWidget(self.chart_dock, self.research_dock)
        self.chart_dock.raise_()
        self.screener_workspace_splitter.setSizes([210, 990])
        self.resizeDocks([self.chart_dock], [360], Qt.Horizontal)
        self.update_screener_status(workspace_state="Compact layout")

    # ----------------------------------------------------------

    def reset_workspace(self):

        self.apply_default_layout()
        state = self.capture_workspace_state()
        state["dock_state"] = None
        return self.workspace_state_service.save_state(state)

    # ----------------------------------------------------------

    def show_workspace_docks(self, visibility):

        for name, dock in getattr(self, "workspace_docks", {}).items():
            if visibility.get(name, True):
                dock.show()
            else:
                dock.hide()

    # ----------------------------------------------------------

    def set_docks_floating(self, floating):

        for dock in getattr(self, "workspace_docks", {}).values():
            dock.setFloating(floating)

    # ----------------------------------------------------------

    def restore_workspace_state(self):

        if not hasattr(self, "workspace_state_service"):
            return

        state = self.workspace_state_service.load_state()
        self.apply_workspace_state(state)
        self.update_screener_status(workspace_state="Loaded")

    # ----------------------------------------------------------

    def apply_workspace_state(self, state):

        if not isinstance(state, dict):
            return

        window_state = state.get("window") or {}
        self.restore_window_geometry(window_state)
        active_layout = state.get("active_layout")
        if active_layout in {"Default", "Research", "Trading", "Compact"}:
            self.apply_named_layout(active_layout)
        self.restore_splitter_state(state.get("splitters") or {})
        self.restore_dock_state(state.get("dock_state"))
        self.restore_dock_metadata(state)
        self.restore_tab_state(state)

        active_preset = state.get("active_screener_preset")
        if active_preset:
            self.screener_preset_controller.active_preset = active_preset
            self.update_screener_status(active_preset=active_preset)

    # ----------------------------------------------------------

    def apply_named_layout(self, layout_name):

        handlers = {
            "Default": self.apply_default_layout,
            "Research": self.apply_research_layout,
            "Trading": self.apply_trading_layout,
            "Compact": self.apply_compact_layout,
        }
        handler = handlers.get(layout_name)
        if handler is not None:
            handler()

    # ----------------------------------------------------------

    def restore_window_geometry(self, window_state):

        if not isinstance(window_state, dict):
            return

        size = window_state.get("size")
        position = window_state.get("position")

        try:
            if (
                isinstance(size, list)
                and len(size) == 2
                and int(size[0]) > 0
                and int(size[1]) > 0
            ):
                self.resize(int(size[0]), int(size[1]))
        except (TypeError, ValueError):
            pass

        try:
            if isinstance(position, list) and len(position) == 2:
                self.move(int(position[0]), int(position[1]))
        except (TypeError, ValueError):
            pass

        try:
            if window_state.get("maximized"):
                self.showMaximized()
        except RuntimeError:
            pass

    # ----------------------------------------------------------

    def restore_splitter_state(self, splitters):

        if not isinstance(splitters, dict):
            return

        for name in [
            "workspace_splitter",
            "screener_workspace_splitter",
            "center_splitter",
            "bottom_splitter",
        ]:
            splitter = getattr(self, name, None)
            sizes = splitters.get(name)
            if splitter is None or not isinstance(sizes, list):
                continue

            try:
                splitter.setSizes([int(size) for size in sizes])
            except (TypeError, ValueError):
                continue

    # ----------------------------------------------------------

    def restore_dock_state(self, dock_state):

        if not dock_state:
            return

        try:
            from PySide6.QtCore import QByteArray

            data = bytes.fromhex(str(dock_state))
            self.restoreState(QByteArray(data))
        except (TypeError, ValueError, RuntimeError):
            return

    # ----------------------------------------------------------

    def restore_dock_metadata(self, state):

        visibility = state.get("dock_visibility") or {}
        floating = state.get("dock_floating") or {}

        for name, dock in getattr(self, "workspace_docks", {}).items():
            if name in visibility:
                dock.setVisible(bool(visibility[name]))

            if name in floating:
                dock.setFloating(bool(floating[name]))

    # ----------------------------------------------------------

    def restore_tab_state(self, state):

        active_dock = state.get("active_workspace")
        if active_dock and hasattr(self, "workspace_docks"):
            for dock in self.workspace_docks.values():
                if dock.windowTitle() == active_dock:
                    dock.raise_()
                    return

        active_tab = state.get("active_tab")
        if active_tab is None or not hasattr(self, "bottom_left_tabs"):
            return

        try:
            index = int(active_tab)
        except (TypeError, ValueError):
            return

        if 0 <= index < self.bottom_left_tabs.count():
            self.bottom_left_tabs.setCurrentIndex(index)

    # ----------------------------------------------------------

    def capture_workspace_state(self):

        geometry = self.normalGeometry() if self.isMaximized() else self.geometry()
        selected_ticker = (
            self.candidates_table.selected_ticker()
            if hasattr(self, "candidates_table")
            else None
        )
        active_tab = (
            self.active_workspace_index()
            if hasattr(self, "workspace_docks")
            else None
        )
        active_workspace = (
            self.active_workspace_title()
        )

        return {
            "window": {
                "size": [geometry.width(), geometry.height()],
                "position": [geometry.x(), geometry.y()],
                "maximized": self.isMaximized(),
            },
            "splitters": self.capture_splitter_state(),
            "active_layout": getattr(
                self,
                "active_workspace_layout",
                self.DEFAULT_WORKSPACE_LAYOUT,
            ),
            "dock_state": bytes(self.saveState()).hex(),
            "dock_visibility": self.capture_dock_visibility(),
            "dock_floating": self.capture_dock_floating(),
            "selected_ticker": selected_ticker,
            "active_tab": active_tab,
            "active_workspace": active_workspace,
            "active_screener_preset": getattr(
                self.screener_preset_controller,
                "active_preset",
                None,
            ),
        }

    # ----------------------------------------------------------

    def capture_dock_visibility(self):

        return {
            name: dock.isVisible()
            for name, dock in getattr(self, "workspace_docks", {}).items()
        }

    # ----------------------------------------------------------

    def capture_dock_floating(self):

        return {
            name: dock.isFloating()
            for name, dock in getattr(self, "workspace_docks", {}).items()
        }

    # ----------------------------------------------------------

    def capture_splitter_state(self):

        splitters = {}
        for name in [
            "workspace_splitter",
            "screener_workspace_splitter",
            "center_splitter",
            "bottom_splitter",
        ]:
            splitter = getattr(self, name, None)
            if splitter is not None:
                splitters[name] = list(splitter.sizes())

        return splitters

    # ----------------------------------------------------------

    def active_workspace_title(self):

        for dock in getattr(self, "workspace_docks", {}).values():
            if dock.isVisible() and dock.widget() is not None:
                return dock.windowTitle()

        return "Results"

    # ----------------------------------------------------------

    def active_workspace_index(self):

        titles = [
            dock.windowTitle()
            for dock in getattr(self, "workspace_docks", {}).values()
        ]
        active_title = self.active_workspace_title()

        try:
            return titles.index(active_title)
        except ValueError:
            return None

    # ----------------------------------------------------------

    def save_workspace_state(self):

        if not hasattr(self, "workspace_state_service"):
            return None

        saved = self.workspace_state_service.save_state(
            self.capture_workspace_state()
        )
        self.update_screener_status(workspace_state="Saved")
        return saved

    # ----------------------------------------------------------

    def log(self, text):

        self.activity_panel.append_log(text)

        QApplication.processEvents()

    # ----------------------------------------------------------

    def add_activity(self, message, status="info"):

        if hasattr(self, "dashboard"):
            return self.dashboard.add_activity(message, status=status)
        return None

    # ----------------------------------------------------------

    def mark_pipeline_running(self, step_key):

        if hasattr(self, "pipeline_progress_panel"):
            self.pipeline_progress_panel.mark_running(step_key)

    # ----------------------------------------------------------

    def mark_pipeline_complete(self, step_key):

        if hasattr(self, "pipeline_progress_panel"):
            self.pipeline_progress_panel.mark_complete(step_key, datetime.now())

    # ----------------------------------------------------------

    def mark_pipeline_error(self, step_key):

        if hasattr(self, "pipeline_progress_panel"):
            self.pipeline_progress_panel.mark_error(step_key, datetime.now())

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
        result = self.settings_dialog.exec()
        self.app_preferences = self.load_app_preferences()
        self.apply_app_preferences_to_ui()
        return result

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

    def current_screener_filters(self):

        filters = {}
        for name, section in getattr(self, "filter_sections", {}).items():
            filters[name] = {
                "enabled": section.isChecked(),
            }
        return filters

    # ----------------------------------------------------------

    def save_screener_preset(self):

        result = self.screener_preset_controller.save_preset(
            "Default",
            self.current_screener_filters(),
        )
        self.update_screener_status(active_preset=result.get("name"))
        self.log(result.get("message", "Preset saved."))
        return result

    # ----------------------------------------------------------

    def load_screener_preset(self):

        result = self.screener_preset_controller.load_preset()
        self.apply_screener_filters(result.get("filters") or {})
        self.update_screener_status(active_preset=result.get("name"))
        self.log(result.get("message", "Preset load complete."))
        return result

    # ----------------------------------------------------------

    def reset_screener_filters(self):

        result = self.screener_preset_controller.reset_filters()
        self.apply_screener_filters({})
        self.clear_screener_results()
        self.update_screener_status(active_preset=None, candidate_count=0)
        self.log(result.get("message", "Screener filters reset."))
        return result

    # ----------------------------------------------------------

    def refresh_screener_results(self):

        return self.refresh_dashboard_results()

    # ----------------------------------------------------------

    def refresh_dashboard_results(self):

        try:
            self.clear_screener_results()
            records = self.load_market_universe_records()
            candidates = [
                self.market_universe_record_to_candidate(record)
                for record in records
            ]
            self.candidates_by_ticker = {
                candidate.ticker: candidate
                for candidate in candidates
            }
            self.candidates_table.populate(candidates)
            self.update_open_detail_state()
            self.last_screen_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.update_screener_status(
                candidate_count=len(candidates),
                last_screen_time=self.last_screen_time,
            )
            self.update_market_universe_statistics(len(candidates))
            self.refresh_dashboard()
            self.update_dashboard_result_state(candidates)
            self.add_activity(
                f"Dashboard results refreshed: {len(candidates):,} records",
                status="success",
            )
            return {
                "success": True,
                "records": len(candidates),
            }
        except Exception as exc:
            self.clear_screener_results(message="Unable to load dashboard data")
            self.activity_panel.set_progress(0)
            self.activity_panel.set_status("Refresh failed")
            self.update_screener_status(candidate_count=0)
            self.log(f"Dashboard refresh failed: {exc}")
            self.mark_pipeline_error("screener")
            self.add_activity("Unable to load dashboard data", status="error")
            return {"success": False, "error": str(exc)}

    # ----------------------------------------------------------

    def load_market_universe_records(self):

        loader = getattr(self.controller, "get_active_market_universe_records", None)

        if not callable(loader):
            return []

        return loader() or []

    # ----------------------------------------------------------

    def market_universe_record_to_candidate(self, record):

        value = self.record_value
        ticker = str(value(record, "ticker") or "").strip().upper()
        metrics = {
            "market_cap": value(record, "market_cap"),
            "price": value(record, "price"),
            "average_volume": value(record, "average_volume"),
            "average_dollar_volume": value(record, "average_dollar_volume"),
            "exchange": value(record, "exchange"),
            "security_type": value(record, "security_type"),
            "sector": value(record, "sector"),
            "industry": value(record, "industry"),
        }

        return SimpleNamespace(
            ticker=ticker,
            company_name=value(record, "company_name") or value(record, "company"),
            primary_score_value=None,
            opportunity_rating=None,
            risk_rating=None,
            composite_score=None,
            bounce_score=None,
            setup_quality=None,
            institutional_checklist=None,
            trade_thesis=None,
            research_report=None,
            trade_card=None,
            institutional_bounce_score=None,
            composite_intelligence_component_scores={},
            metrics=metrics,
            score_map={
                "quality_score": None,
                "institutional_score": None,
                "technical_score": None,
                "support_score": None,
                "bounce_score": None,
            },
            scores=[],
            warnings=[],
            notes=None,
            summary=None,
            timestamp=datetime.now(),
        )

    # ----------------------------------------------------------

    def update_market_universe_statistics(self, stock_count):

        try:
            stats = self.controller.get_statistics()
        except Exception:
            stats = {}

        stats = dict(stats or {})
        stats.setdefault("rows", 0)
        stats.setdefault("indicator_rows", 0)
        stats.setdefault("support_levels", 0)
        stats.setdefault("validated_zones", 0)
        stats["candidates"] = len(getattr(self, "candidates_by_ticker", {}) or {})
        stats["stocks"] = stock_count
        self.latest_statistics = stats
        self.kpi_strip.update_statistics(stats)

    # ----------------------------------------------------------

    @staticmethod
    def record_value(record, key):

        if isinstance(record, dict):
            return record.get(key)

        return getattr(record, key, None)

    # ----------------------------------------------------------

    def apply_screener_filters(self, filters):

        for name, section in getattr(self, "filter_sections", {}).items():
            section.setChecked((filters or {}).get(name, {}).get("enabled", True))
        self.update_summary()
        if not getattr(self, "candidates_by_ticker", {}):
            self.set_dashboard_status_message("No stocks match the current filters")

    # ----------------------------------------------------------

    def clear_screener_results(self, message="No results available"):

        if hasattr(self, "candidates_table"):
            self.candidates_table.populate([])
        self.candidates_by_ticker = {}
        self.refresh_candidate_kpi()
        if hasattr(self, "research_preview"):
            self.research_preview.clear()
        if hasattr(self, "trade_card"):
            self.trade_card.clear()
        if hasattr(self, "price_chart"):
            self.price_chart.clear()
        self.refresh_dashboard()
        self.set_dashboard_status_message(message)

    # ----------------------------------------------------------

    def update_screener_status(
        self,
        selected_ticker=None,
        candidate_count=None,
        last_screen_time=None,
        active_preset=None,
        market_status=None,
        active_provider=None,
        database_status=None,
        last_sync_time=None,
        workspace_state=None,
    ):

        if not hasattr(self, "selected_ticker_status"):
            return

        if selected_ticker is None and hasattr(self, "candidates_table"):
            selected_ticker = self.candidates_table.selected_ticker()

        if candidate_count is None:
            candidate_count = len(getattr(self, "candidates_by_ticker", {}) or {})

        if last_screen_time is None:
            last_screen_time = getattr(self, "last_screen_time", None)

        if active_preset is None:
            active_preset = getattr(self.screener_preset_controller, "active_preset", None)

        if market_status is None:
            market_status = self.current_market_status_text()

        if active_provider is None:
            active_provider = self.current_provider_text()

        if database_status is None:
            database_status = getattr(self, "current_database_status", None)

        if last_sync_time is None:
            last_sync_time = getattr(self, "last_sync_at", None)

        if workspace_state is None:
            workspace_state = getattr(self, "workspace_state_indicator", None)

        self.market_status_status.setText(f"Market: {market_status or '--'}")
        self.active_provider_status.setText(f"Provider: {active_provider or '--'}")
        self.database_status.setText(f"Database: {database_status or '--'}")
        self.last_refresh_status.setText(
            f"Last refresh: {last_screen_time or '--'}"
        )
        self.last_sync_status.setText(f"Last sync: {last_sync_time or '--'}")
        self.selected_ticker_status.setText(
            f"Selected ticker: {selected_ticker or '--'}"
        )
        self.candidate_count_status.setText(f"Candidate count: {candidate_count}")
        self.active_preset_status.setText(f"Active preset: {active_preset or '--'}")
        self.workspace_state_status.setText(f"Workspace: {workspace_state or '--'}")

    # ----------------------------------------------------------

    def current_market_status_text(self):

        try:
            return self.market_status_service.get_status().status
        except Exception:
            return None

    # ----------------------------------------------------------

    def current_provider_text(self):

        try:
            provider_status = self.settings_service.provider_status()
        except Exception:
            return None

        if not isinstance(provider_status, dict):
            return None

        return provider_status.get("current_provider")

    # ----------------------------------------------------------

    def refresh_statistics(self):

        stats = self.controller.get_statistics()
        stats["candidates"] = len(getattr(self, "candidates_by_ticker", {}) or {})
        self.latest_statistics = stats

        self.kpi_strip.update_statistics(stats)
        self.refresh_dashboard()

    # ----------------------------------------------------------

    def refresh_candidate_kpi(self):

        if not hasattr(self, "kpi_strip"):
            return

        stats = dict(getattr(self, "latest_statistics", {}) or {})
        for key in [
            "stocks",
            "rows",
            "indicator_rows",
            "support_levels",
            "validated_zones",
        ]:
            stats.setdefault(key, 0)
        stats["candidates"] = len(getattr(self, "candidates_by_ticker", {}) or {})
        self.latest_statistics = stats
        self.kpi_strip.update_statistics(stats)

    # ----------------------------------------------------------

    def refresh_dashboard(self):

        if not hasattr(self, "dashboard"):
            return

        data = self.dashboard_controller.get_dashboard_data(
            candidates=list(self.candidates_by_ticker.values()),
            last_refresh=self.last_refresh_at,
        )
        self.dashboard.set_dashboard_data(data)
        self.update_summary()

    # ----------------------------------------------------------

    def update_dashboard_result_state(self, candidates):

        if candidates:
            self.clear_dashboard_status_message()
            return

        if self.has_active_filter_selection():
            self.set_dashboard_status_message("No stocks match the current filters")
        else:
            self.set_dashboard_status_message("No results available")

    # ----------------------------------------------------------

    def set_dashboard_status_message(self, message):

        if not hasattr(self, "dashboard_status_label"):
            return

        self.dashboard_status_label.setText(message or "")
        self.dashboard_status_label.setVisible(bool(message))

    # ----------------------------------------------------------

    def clear_dashboard_status_message(self):

        self.set_dashboard_status_message("")

    # ----------------------------------------------------------

    def has_active_filter_selection(self):

        for section in getattr(self, "filter_sections", {}).values():
            if hasattr(section, "isChecked") and not section.isChecked():
                return True
        return False

    # ----------------------------------------------------------

    def update_summary(self, stats=None):

        if not hasattr(self, "dashboard_summary_labels"):
            return

        summary = self.dashboard_summary_values(stats)

        for key, label in self.dashboard_summary_labels.items():
            label.setText(summary.get(key, "N/A"))

    # ----------------------------------------------------------

    def dashboard_summary_values(self, stats=None):

        stats = stats if isinstance(stats, dict) else getattr(self, "latest_statistics", {})

        if not stats:
            try:
                stats = self.controller.get_statistics()
                self.latest_statistics = stats
            except Exception:
                stats = {}

        return {
            "total_stocks_loaded": self.summary_int(stats.get("stocks")),
            "stocks_passing_filters": self.summary_int(
                len(getattr(self, "candidates_by_ticker", {}) or {})
            ),
            "last_refresh_time": self.summary_text(
                self.last_refresh_at or getattr(self, "last_screen_time", None)
            ),
            "database_name": self.current_database_name(),
        }

    # ----------------------------------------------------------

    def current_database_name(self):

        try:
            settings = self.settings_service.load()
        except Exception:
            return "N/A"

        path = ((settings or {}).get("paths") or {}).get("database_path")
        if not path:
            return "N/A"

        name = Path(str(path)).name
        return name or "N/A"

    # ----------------------------------------------------------

    @staticmethod
    def summary_int(value):

        if value in (None, ""):
            return "N/A"
        try:
            return f"{int(value):,}"
        except (TypeError, ValueError):
            return "N/A"

    # ----------------------------------------------------------

    @staticmethod
    def summary_text(value):

        if value in (None, ""):
            return "N/A"
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        return str(value)

    # ----------------------------------------------------------

    def update_universe(self):

        self.mark_pipeline_running("universe")
        self.activity_panel.set_status("Importing universe...")
        self.activity_panel.set_progress(20)

        self.activity_panel.clear_log()

        imported, total = self.controller.update_universe()

        self.log(f"✅ Imported {imported} stocks")

        self.activity_panel.set_progress(100)

        self.activity_panel.set_status("Ready")

        self.refresh_statistics()
        self.mark_pipeline_complete("universe")
        self.add_activity(
            f"Universe update complete: {imported:,} of {total:,} stocks imported",
            status="success",
        )

    # ----------------------------------------------------------

    def download_prices(self):

        self.mark_pipeline_running("prices")
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
        self.mark_pipeline_complete("prices")
        self.add_activity(
            f"Price download complete: {total:,} database rows",
            status="success",
        )

        self.log("")
        self.log(f"Database Rows: {total:,}")

    # ----------------------------------------------------------

    def calculate_indicators(self):

        self.mark_pipeline_running("indicators")
        self.activity_panel.set_status("Calculating indicators...")
        self.activity_panel.set_progress(20)

        self.activity_panel.clear_log()

        results = self.indicator_controller.calculate_indicators()

        self.activity_panel.set_progress(100)

        self.activity_panel.set_status("Ready")

        self.refresh_statistics()
        self.mark_pipeline_complete("indicators")
        self.add_activity(
            f"Indicator calculation complete: {results['rows']:,} rows written",
            status="success",
        )

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

        self.mark_pipeline_running("support")
        self.activity_panel.set_status("Detecting support...")
        self.activity_panel.set_progress(20)

        self.activity_panel.clear_log()

        results = self.support_controller.detect_support()

        self.activity_panel.set_progress(100)

        self.activity_panel.set_status("Ready")

        self.refresh_statistics()
        self.mark_pipeline_complete("support")
        self.add_activity(
            f"Support detection complete: {results['zones']:,} zones found",
            status="success",
        )

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

        self.mark_pipeline_running("bounce_validation")
        self.activity_panel.set_status("Validating bounces...")
        self.activity_panel.set_progress(20)

        self.activity_panel.clear_log()

        results = self.bounce_controller.validate_bounces()

        self.activity_panel.set_progress(100)

        self.activity_panel.set_status("Ready")

        self.refresh_statistics()
        self.mark_pipeline_complete("bounce_validation")
        self.add_activity(
            f"Bounce validation complete: {results['validated']:,} zones validated",
            status="success",
        )

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

        self.mark_pipeline_running("screener")
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
        self.refresh_candidate_kpi()
        self.update_open_detail_state()
        self.last_screen_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.update_screener_status(
            candidate_count=len(results["candidates"]),
            last_screen_time=self.last_screen_time,
        )
        self.refresh_dashboard()
        self.update_dashboard_result_state(results["candidates"])

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
        self.mark_pipeline_complete("screener")
        self.add_activity(
            f"Screener run complete: {len(results['candidates']):,} candidates",
            status="success",
        )

    # ----------------------------------------------------------

    def open_stock_detail(self, ticker):

        candidate = getattr(self, "candidates_by_ticker", {}).get(ticker)
        detail = self.candidate_detail_for_ticker(ticker)

        if candidate is None and detail:
            window = StockDetailWindow(detail, self)
        else:
            window = CandidateDetailWindow(candidate=candidate, detail=detail, parent=self)
        window.show()

        if not hasattr(self, "detail_windows"):
            self.detail_windows = []

        self.detail_windows.append(window)

    # ----------------------------------------------------------

    def candidate_detail_for_ticker(self, ticker):

        try:
            return self.scoring_controller.get_candidate_detail(ticker) or {}
        except Exception:
            return {}

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
        self.update_screener_status(selected_ticker=ticker)

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
            if hasattr(self.watchlist_controller, "get_watchlist_intelligence"):
                intelligence = self.watchlist_controller.get_watchlist_intelligence()
                self.watchlist_panel.refresh_intelligence(intelligence)
        else:
            self.watchlist_panel.clear()
        self.refresh_dashboard()

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

    def screening_repository(self):

        explicit = getattr(self, "_screening_repository", None)
        if explicit is not None:
            return explicit

        market_service = getattr(self.controller, "market", None)
        return getattr(market_service, "db", None)

    # ----------------------------------------------------------

    def parse_screening_tickers(self, ticker_text):

        tickers = []
        for raw_ticker in str(ticker_text or "").split(","):
            ticker = raw_ticker.strip().upper()
            if ticker and ticker not in tickers:
                tickers.append(ticker)
        return tickers

    # ----------------------------------------------------------

    def parse_ticker_input(self, ticker_text):

        return self.parse_screening_tickers(ticker_text)

    # ----------------------------------------------------------

    def universe_scan_adapter(self):

        explicit = getattr(self, "_universe_scan_adapter", None)
        if explicit is not None:
            return explicit
        return UniverseScanAdapter(self.controller)

    # ----------------------------------------------------------

    def market_data_refresh_service(self):

        explicit = getattr(self, "_market_data_refresh_service", None)
        if explicit is not None:
            return explicit
        return MarketDataRefreshService(repository=self.screening_repository())

    # ----------------------------------------------------------

    def market_data_cache_service(self):

        explicit = getattr(self, "_market_data_cache_service", None)
        if explicit is not None:
            return explicit
        return MarketDataCacheService(repository=self.screening_repository())

    # ----------------------------------------------------------

    def data_quality_service(self):

        explicit = getattr(self, "_data_quality_service", None)
        if explicit is not None:
            return explicit
        return DataQualityService(repository=self.screening_repository())

    # ----------------------------------------------------------

    def provider_diagnostics_service(self):

        explicit = getattr(self, "_provider_diagnostics_service", None)
        if explicit is not None:
            return explicit
        return ProviderDiagnosticsService(settings_service=self.app_settings_service)

    # ----------------------------------------------------------

    def refresh_selected_market_data_ticker(self, ticker, force_refresh=False):

        tickers = self.parse_ticker_input(ticker)
        if not tickers:
            self.screening_results_panel.set_market_data_status("No ticker selected")
            return None
        return self.refresh_market_data_tickers(tickers[:1], force_refresh=force_refresh)

    # ----------------------------------------------------------

    def refresh_market_data_ticker_list(self, ticker_text, force_refresh=False):

        tickers = self.parse_ticker_input(ticker_text)
        if not tickers:
            self.screening_results_panel.set_market_data_status("No tickers provided")
            return None
        return self.refresh_market_data_tickers(tickers, force_refresh=force_refresh)

    # ----------------------------------------------------------

    def refresh_market_data_tickers(self, tickers, force_refresh=False):

        panel = self.screening_results_panel
        service = self.market_data_refresh_service()
        self.data_refresh_cancel_requested = False
        panel.set_data_refresh_active(True, "Refreshing market data")

        def progress(progress_event):
            if getattr(self, "data_refresh_cancel_requested", False):
                return
            current = progress_event.get("current_ticker") or "--"
            processed = progress_event.get("processed_tickers", 0)
            total = progress_event.get("total_tickers", 0)
            panel.set_market_data_status(f"Refreshing {current}: {processed}/{total}")

        try:
            result = service.refresh_tickers(
                tickers,
                force_refresh=force_refresh,
                progress_callback=progress,
                cancellation_callback=lambda: self.data_refresh_cancel_requested,
            )
            if self.data_refresh_cancel_requested:
                panel.set_market_data_status("Refresh cancelled")
            else:
                errors = len(getattr(result, "errors", []) or [])
                warnings = len(getattr(result, "warnings", []) or [])
                count = len(getattr(result, "results", {}) or {})
                panel.set_market_data_status(
                    f"Refresh complete: {count} ticker(s), {warnings} warning(s), {errors} error(s)"
                )
            self.refresh_cache_coverage_summary()
            return result
        except Exception as exc:
            panel.set_market_data_status(f"Refresh failed: {exc}")
            return None
        finally:
            panel.set_data_refresh_active(False)

    # ----------------------------------------------------------

    def refresh_market_data_universe_symbols(self, force_refresh=False):

        tickers = self.universe_scan_tickers()
        if not tickers:
            self.screening_results_panel.set_market_data_status(
                "No eligible universe symbols"
            )
            return None
        return self.refresh_market_data_tickers(tickers, force_refresh=force_refresh)

    # ----------------------------------------------------------

    def cancel_market_data_refresh(self):

        self.data_refresh_cancel_requested = True
        self.screening_results_panel.set_data_refresh_active(False, "Refresh cancelled")
        return True

    # ----------------------------------------------------------

    def refresh_cache_coverage_summary(self):

        if not hasattr(self, "screening_results_panel"):
            return []
        try:
            coverage = self.market_data_cache_service().coverage()
        except Exception:
            coverage = []
        self.screening_results_panel.set_cache_coverage_summary(coverage)
        return coverage

    # ----------------------------------------------------------

    def clear_market_data_cache_ticker(self, ticker):

        tickers = self.parse_ticker_input(ticker)
        if not tickers:
            self.screening_results_panel.set_market_data_status("No ticker selected")
            return 0
        deleted = self.market_data_cache_service().clear_ticker(tickers[0])
        self.screening_results_panel.set_market_data_status(
            f"Cleared {deleted} cached row(s) for {tickers[0]}"
        )
        self.refresh_cache_coverage_summary()
        return deleted

    # ----------------------------------------------------------

    def clear_all_market_data_cache(self):

        deleted = self.market_data_cache_service().clear_all()
        self.screening_results_panel.set_market_data_status(
            f"Cleared {deleted} cached OHLCV row(s)"
        )
        self.refresh_cache_coverage_summary()
        return deleted

    # ----------------------------------------------------------

    def run_provider_diagnostics(self):

        try:
            result = self.provider_diagnostics_service().run(connectivity_test=True)
            status = (
                f"Provider {result.selected_provider}: {result.credential_status}; "
                f"connectivity {result.connectivity_status}; retries {result.max_retries}"
            )
        except Exception as exc:
            result = None
            status = f"Provider diagnostics failed: {exc}"
        self.screening_results_panel.set_market_data_status(status)
        return result

    # ----------------------------------------------------------

    def backtest_engine(self):

        explicit = getattr(self, "_backtest_engine", None)
        if explicit is not None:
            return explicit
        return SignalBacktestEngine(repository=self.screening_repository())

    # ----------------------------------------------------------

    def chart_analytics_service(self):

        explicit = getattr(self, "_chart_analytics_service", None)
        if explicit is not None:
            return explicit
        chart_data_service = getattr(self.chart_controller, "chart_data_service", None)
        return ChartAnalyticsService(
            chart_data_service=chart_data_service,
            repository=self.screening_repository(),
        )

    # ----------------------------------------------------------

    def run_backtest_from_results(self, config_values=None):

        if not hasattr(self, "screening_results_panel"):
            return None
        candidates = getattr(self.screening_results_panel, "current_candidates", [])
        if not candidates:
            self.screening_results_panel.set_backtest_status(
                "No ranked candidates available for backtest"
            )
            return None
        config_values = config_values or {}
        config = BacktestConfig(
            min_score=float(config_values.get("min_score", 60)),
            max_holding_days=int(config_values.get("max_holding_days", 30)),
            profit_target_pct=float(config_values.get("profit_target_pct", 20)),
            stop_loss_pct=float(config_values.get("stop_loss_pct", 8)),
        )
        self.screening_results_panel.set_backtest_active(True, "Running backtest")
        try:
            result = self.backtest_engine().run_backtest(candidates, config=config)
            repository = self.screening_repository()
            if repository is not None and hasattr(repository, "save_backtest_run"):
                repository.save_backtest_run(
                    result,
                    source_run_id=getattr(self, "selected_results_run_id", None),
                )
            self.screening_results_panel.populate_backtest_results(result)
            analytics = self.chart_analytics_service().build_backtest_analytics(result)
            self.screening_results_panel.set_backtest_analytics_model(analytics)
            self.screening_results_panel.set_backtest_status(
                f"Backtest complete: {len(result.trades)} trade(s)"
            )
            return result
        except Exception as exc:
            self.screening_results_panel.set_backtest_status(
                f"Backtest failed: {exc}"
            )
            return None
        finally:
            self.screening_results_panel.set_backtest_active(False)

    # ----------------------------------------------------------

    def cancel_backtest(self):

        self.screening_results_panel.set_backtest_active(False, "Backtest cancelled")
        return True

    # ----------------------------------------------------------

    def show_data_quality_report(self, ticker_text=None):

        tickers = self.parse_ticker_input(ticker_text)
        if not tickers:
            tickers = [
                self.ticker_for_candidate(candidate)
                for candidate in getattr(self.screening_results_panel, "current_candidates", [])
            ]
        tickers = [ticker for ticker in tickers if ticker]
        if not tickers:
            self.screening_results_panel.set_market_data_status(
                "No tickers available for data quality report"
            )
            return None
        report = self.data_quality_service().generate_report(tickers)
        warning_count = len(getattr(report, "warnings", []) or [])
        self.screening_results_panel.set_market_data_status(
            f"Data quality report: {len(report.ticker_reports)} ticker(s), {warning_count} warning(s)"
        )
        return report

    # ----------------------------------------------------------

    def universe_scan_tickers(self):

        return self.universe_scan_adapter().load_tickers(
            self.current_universe_scan_filters()
        )

    # ----------------------------------------------------------

    def selected_scan_preset(self):

        if not hasattr(self, "screening_results_panel"):
            return None
        return self.scan_preset_service.apply_preset(
            self.screening_results_panel.selected_scan_preset_name()
        )

    # ----------------------------------------------------------

    def current_universe_scan_filters(self):

        filters = self.current_screener_filters()
        filters["scan_preset"] = self.selected_scan_preset()
        return filters

    # ----------------------------------------------------------

    def scan_filter_summary_text(self, preset=None):

        preset = preset if preset is not None else self.selected_scan_preset()
        if preset is None:
            return "Filters: No preset selected"

        parts = []
        if preset.min_market_cap is not None:
            parts.append(f"Market cap >= {self.compact_number(preset.min_market_cap)}")
        if preset.min_price is not None:
            parts.append(f"Price >= ${preset.min_price:g}")
        if preset.min_avg_volume is not None:
            parts.append(f"Avg volume >= {self.compact_number(preset.min_avg_volume)}")
        if preset.min_avg_dollar_volume is not None:
            parts.append(
                f"Avg dollar volume >= {self.compact_number(preset.min_avg_dollar_volume)}"
            )
        if preset.exchanges:
            parts.append(f"Exchanges: {', '.join(preset.exchanges)}")
        if preset.security_types:
            parts.append(f"Types: {', '.join(preset.security_types)}")
        return "Filters: " + "; ".join(parts)

    # ----------------------------------------------------------

    def update_scan_preset_summary(self):

        if not hasattr(self, "screening_results_panel"):
            return
        preset = self.selected_scan_preset()
        if preset is None:
            self.screening_results_panel.set_preset_description("Preset: --")
            self.screening_results_panel.set_active_filter_summary("Filters: --")
            return
        self.screening_results_panel.set_preset_description(
            f"{preset.name}: {preset.description}"
        )
        self.screening_results_panel.set_active_filter_summary(
            self.scan_filter_summary_text(preset)
        )

    # ----------------------------------------------------------

    def handle_scan_preset_changed(self, name=None):

        self.update_scan_preset_summary()
        if (
            hasattr(self, "screening_results_panel")
            and self.screening_results_panel.is_universe_scan_mode()
        ):
            return self.handle_screening_mode_changed()
        return []

    # ----------------------------------------------------------

    def handle_screening_mode_changed(self, mode=None):

        if not hasattr(self, "screening_results_panel"):
            return []

        self.update_scan_preset_summary()
        if self.screening_results_panel.is_universe_scan_mode():
            tickers = self.universe_scan_tickers()
            self.screening_results_panel.set_universe_count(len(tickers))
            if not tickers:
                self.screening_results_panel.set_screening_status(
                    "No eligible universe tickers"
                )
            else:
                self.screening_results_panel.set_screening_status(
                    f"Universe scan ready: {len(tickers)} ticker(s)"
                )
            return tickers

        self.screening_results_panel.set_universe_count("--")
        self.screening_results_panel.set_screening_status("Ready")
        return []

    # ----------------------------------------------------------

    def load_app_preferences(self):

        try:
            return self.app_settings_service.get_preferences()
        except Exception:
            return None

    # ----------------------------------------------------------

    def app_preference(self, key, default=None):

        return getattr(getattr(self, "app_preferences", None), key, default)

    # ----------------------------------------------------------

    def apply_app_preferences_to_ui(self):

        if not hasattr(self, "screening_results_panel"):
            return

        max_scan_size = self.app_preference(
            "max_scan_size",
            self.MAX_UNIVERSE_SCAN_TICKERS,
        )
        self.MAX_UNIVERSE_SCAN_TICKERS = int(max_scan_size or self.MAX_UNIVERSE_SCAN_TICKERS)
        self._results_export_output_dir = self.app_preference(
            "default_export_directory",
            "exports/results",
        )

        mode = self.app_preference("default_scan_mode", None)
        if mode:
            index = self.screening_results_panel.screening_mode_combo.findText(mode)
            if index >= 0:
                self.screening_results_panel.screening_mode_combo.setCurrentIndex(index)

        preset = self.app_preference("default_scan_preset", None)
        if preset:
            index = self.screening_results_panel.scan_preset_combo.findText(preset)
            if index >= 0:
                self.screening_results_panel.scan_preset_combo.setCurrentIndex(index)

    # ----------------------------------------------------------

    @staticmethod
    def compact_number(value):

        number = float(value)
        for suffix, divisor in [
            ("T", 1_000_000_000_000),
            ("B", 1_000_000_000),
            ("M", 1_000_000),
            ("K", 1_000),
        ]:
            if abs(number) >= divisor:
                return f"{number / divisor:g}{suffix}"
        return f"{number:g}"

    # ----------------------------------------------------------

    def selected_screening_tickers(self, ticker_text=None):

        if (
            hasattr(self, "screening_results_panel")
            and self.screening_results_panel.is_universe_scan_mode()
        ):
            tickers = self.universe_scan_tickers()
            self.screening_results_panel.set_universe_count(len(tickers))
            return tickers

        text = (
            ticker_text
            if ticker_text is not None
            else self.screening_results_panel.ticker_input.text()
        )
        return self.parse_screening_tickers(text)

    # ----------------------------------------------------------

    def apply_screening_ticker_guardrails(self, tickers):

        self.last_screening_guardrail_message = None
        if not tickers:
            self.last_screening_guardrail_message = "No eligible tickers"
            self.screening_results_panel.set_screening_status(
                self.last_screening_guardrail_message
            )
            return []

        max_scan_size = int(
            self.app_preference("max_scan_size", self.MAX_UNIVERSE_SCAN_TICKERS)
            or self.MAX_UNIVERSE_SCAN_TICKERS
        )
        warning_threshold = int(
            self.app_preference("large_scan_warning_threshold", max_scan_size)
            or max_scan_size
        )

        if len(tickers) > max_scan_size:
            limited = tickers[:max_scan_size]
            self.last_screening_guardrail_message = (
                f"Large scan limited to {max_scan_size} ticker(s)"
            )
            self.screening_results_panel.set_screening_status(
                self.last_screening_guardrail_message
            )
            return limited

        if len(tickers) >= warning_threshold:
            self.last_screening_guardrail_message = (
                f"Large scan warning: {len(tickers)} ticker(s)"
            )
            self.screening_results_panel.set_screening_status(
                self.last_screening_guardrail_message
            )

        return tickers

    # ----------------------------------------------------------

    def start_screening_from_input(self, ticker_text=None):

        if not hasattr(self, "screening_results_panel"):
            return None

        tickers = self.selected_screening_tickers(ticker_text)
        tickers = self.apply_screening_ticker_guardrails(tickers)
        if not tickers:
            return None

        if getattr(self, "screening_worker", None) is not None:
            self.screening_results_panel.set_screening_status("Screening already running")
            return self.screening_worker

        worker = self.create_screening_worker(tickers)
        self.screening_worker = worker
        start_message = (
            self.last_screening_guardrail_message
            or f"Starting screening for {len(tickers)} ticker(s)..."
        )
        self.screening_results_panel.set_screening_active(
            True,
            start_message,
        )
        worker.started_signal.connect(self.handle_screening_started)
        worker.progress_signal.connect(self.handle_screening_progress)
        worker.completed_signal.connect(self.handle_screening_completed)
        worker.failed_signal.connect(self.handle_screening_failed)
        worker.cancelled_signal.connect(self.handle_screening_cancelled)
        worker.start()
        return worker

    # ----------------------------------------------------------

    def create_screening_worker(self, tickers):

        repository = self.screening_repository()
        pipeline_adapter = None
        if repository is not None:
            from services.candidate_pipeline_adapter import CandidatePipelineAdapter
            pipeline_adapter = CandidatePipelineAdapter(repository)
        from services.screening_orchestrator import ScreeningOrchestrator
        orchestrator = ScreeningOrchestrator(
            market_data_refresh_service=self.market_data_refresh_service(),
            pipeline_adapter=pipeline_adapter,
            repository=repository,
        )
        return ScreeningWorker(
            tickers=tickers,
            repository=repository,
            orchestrator=orchestrator,
            parent=self,
        )

    # ----------------------------------------------------------

    def handle_screening_started(self, message):

        self.screening_results_panel.set_screening_active(True, message)

    # ----------------------------------------------------------

    def handle_screening_progress(self, message):

        if isinstance(message, dict):
            current = message.get("current_ticker") or "--"
            processed = message.get("processed_tickers", 0)
            total = message.get("total_tickers", 0)
            pct = message.get("progress_percentage", 0)
            status = message.get("status_message") or "Screening"
            text = f"{status} ({processed}/{total}, {pct:.0f}%, current: {current})"
        else:
            text = str(message)
        self.screening_results_panel.set_screening_status(text)

    # ----------------------------------------------------------

    def handle_screening_completed(self, result):

        count = len(getattr(result, "ranked_candidates", []) or [])
        self.screening_results_panel.set_screening_active(
            False,
            f"Screening complete: {count} ranked candidate(s)",
        )
        self.screening_worker = None
        if self.app_preference("auto_refresh_results", True):
            self.refresh_screening_run_history_view()
            self.refresh_ranked_candidates_view()

    # ----------------------------------------------------------

    def handle_screening_cancelled(self, result):

        count = len(getattr(result, "ranked_candidates", []) or [])
        self.screening_results_panel.set_screening_active(
            False,
            f"Screening cancelled: {count} ranked candidate(s)",
        )
        self.screening_worker = None
        if self.app_preference("auto_refresh_results", True):
            self.refresh_screening_run_history_view()
            self.refresh_ranked_candidates_view()

    # ----------------------------------------------------------

    def handle_screening_failed(self, message):

        self.screening_results_panel.set_screening_active(
            False,
            f"Screening failed: {message}",
        )
        self.screening_worker = None

    # ----------------------------------------------------------

    def cancel_screening(self):

        worker = getattr(self, "screening_worker", None)
        if worker is None:
            self.screening_results_panel.set_screening_status("No active screening run")
            return False

        if hasattr(worker, "request_cancel"):
            worker.request_cancel()
        self.screening_results_panel.set_screening_status("Cancellation requested")
        self.screening_results_panel.cancel_screening_button.setEnabled(False)
        return True

    # ----------------------------------------------------------

    def refresh_ranked_candidates_view(self):

        if not hasattr(self, "screening_results_panel"):
            return []

        self.selected_results_run_id = None
        self.ranked_candidates_offset = 0
        repository = self.screening_repository()
        candidates = []
        total_count = 0

        try:
            if repository is not None and hasattr(
                repository,
                "fetch_latest_ranked_candidates",
            ):
                candidates = self.displayable_ranked_candidates(
                    self.fetch_latest_ranked_page(repository, 0)
                )
                total_count = self.count_latest_ranked_candidates(repository, candidates)
        except Exception:
            candidates = []

        self.ranked_candidates_offset = len(candidates)
        self.ranked_candidates_total_count = total_count
        self.screening_results_panel.populate_ranked_candidates(
            candidates,
            total_count=total_count,
        )
        self.update_results_export_state(candidates)
        return candidates

    # ----------------------------------------------------------

    def load_ranked_candidates_for_run(self, run_id):

        if not hasattr(self, "screening_results_panel"):
            return []

        self.selected_results_run_id = run_id
        self.ranked_candidates_offset = 0
        repository = self.screening_repository()
        candidates = []
        total_count = 0

        try:
            if repository is not None and hasattr(repository, "fetch_ranked_candidates"):
                candidates = self.displayable_ranked_candidates(
                    self.fetch_ranked_candidates_page(repository, run_id, 0)
                )
                total_count = self.count_ranked_candidates(
                    repository,
                    run_id,
                    candidates,
                )
        except Exception:
            candidates = []

        self.ranked_candidates_offset = len(candidates)
        self.ranked_candidates_total_count = total_count
        self.screening_results_panel.populate_ranked_candidates(
            candidates,
            total_count=total_count,
        )
        if not candidates:
            self.screening_results_panel.show_ranked_empty_message(
                "Run has no candidates"
            )
        self.update_results_export_state(candidates)
        return candidates

    # ----------------------------------------------------------

    def load_more_ranked_candidates_view(self):

        if not hasattr(self, "screening_results_panel"):
            return []

        repository = self.screening_repository()
        candidates = []
        offset = getattr(self, "ranked_candidates_offset", 0)
        run_id = getattr(self, "selected_results_run_id", None)

        try:
            if repository is None:
                candidates = []
            elif run_id:
                candidates = self.displayable_ranked_candidates(
                    self.fetch_ranked_candidates_page(repository, run_id, offset)
                )
            else:
                candidates = self.displayable_ranked_candidates(
                    self.fetch_latest_ranked_page(repository, offset)
                )
        except Exception:
            candidates = []

        self.ranked_candidates_offset = offset + len(candidates)
        self.screening_results_panel.populate_ranked_candidates(
            candidates,
            total_count=getattr(self, "ranked_candidates_total_count", None),
            append=True,
        )
        self.update_results_export_state()
        return candidates

    # ----------------------------------------------------------

    def refresh_screening_run_history_view(self):

        if not hasattr(self, "screening_results_panel"):
            return []

        repository = self.screening_repository()
        runs = []
        self.run_history_offset = 0
        total_count = 0

        try:
            if repository is not None and hasattr(
                repository,
                "fetch_screening_run_history",
            ):
                runs = self.fetch_screening_run_history_page(repository, 0)
                total_count = self.count_screening_runs(repository, runs)
        except Exception:
            runs = []

        self.run_history_offset = len(runs)
        self.run_history_total_count = total_count
        self.screening_results_panel.populate_run_history(
            runs,
            total_count=total_count,
        )
        return runs

    # ----------------------------------------------------------

    def load_more_screening_run_history_view(self):

        if not hasattr(self, "screening_results_panel"):
            return []

        repository = self.screening_repository()
        offset = getattr(self, "run_history_offset", 0)
        runs = []

        try:
            if repository is not None and hasattr(
                repository,
                "fetch_screening_run_history",
            ):
                runs = self.fetch_screening_run_history_page(repository, offset)
        except Exception:
            runs = []

        self.run_history_offset = offset + len(runs)
        self.screening_results_panel.populate_run_history(
            runs,
            total_count=getattr(self, "run_history_total_count", None),
            append=True,
        )
        return runs

    # ----------------------------------------------------------

    def fetch_ranked_candidates_page(self, repository, run_id, offset):

        try:
            return repository.fetch_ranked_candidates(
                run_id,
                limit=self.RESULTS_PAGE_SIZE,
                offset=offset,
            ) or []
        except TypeError:
            return repository.fetch_ranked_candidates(run_id) or []

    # ----------------------------------------------------------

    def fetch_latest_ranked_page(self, repository, offset):

        try:
            return repository.fetch_latest_ranked_candidates(
                limit=self.RESULTS_PAGE_SIZE,
                offset=offset,
            ) or []
        except TypeError:
            return repository.fetch_latest_ranked_candidates() or []

    # ----------------------------------------------------------

    def fetch_screening_run_history_page(self, repository, offset):

        try:
            return repository.fetch_screening_run_history(
                limit=self.RUN_HISTORY_PAGE_SIZE,
                offset=offset,
            ) or []
        except TypeError:
            return repository.fetch_screening_run_history(
                limit=self.RUN_HISTORY_PAGE_SIZE,
            ) or []

    # ----------------------------------------------------------

    def count_ranked_candidates(self, repository, run_id, fallback):

        if repository is not None and hasattr(repository, "count_ranked_candidates"):
            return repository.count_ranked_candidates(run_id)
        return len(fallback or [])

    # ----------------------------------------------------------

    def count_latest_ranked_candidates(self, repository, fallback):

        if repository is not None and hasattr(repository, "count_latest_ranked_candidates"):
            return repository.count_latest_ranked_candidates()
        return len(fallback or [])

    # ----------------------------------------------------------

    def count_screening_runs(self, repository, fallback):

        if repository is not None and hasattr(repository, "count_screening_runs"):
            return repository.count_screening_runs()
        return len(fallback or [])

    # ----------------------------------------------------------

    def displayable_ranked_candidates(self, candidates):

        rows = list(candidates or [])
        if self.app_preference("show_rejected_candidates", True):
            return rows
        return [
            candidate
            for candidate in rows
            if (
                candidate.get("grade")
                if isinstance(candidate, dict)
                else getattr(candidate, "grade", None)
            ) != "REJECT"
        ]

    # ----------------------------------------------------------

    def update_results_export_state(self, candidates=None):

        if not hasattr(self, "screening_results_panel"):
            return False

        exportable = bool(candidates if candidates is not None else getattr(
            self.screening_results_panel,
            "current_candidates",
            [],
        ))
        self.screening_results_panel.set_export_enabled(exportable)
        self.screening_results_panel.set_export_status(
            "Ready to export" if exportable else "No exportable results"
        )
        return exportable

    # ----------------------------------------------------------

    def results_export_controller(self):

        return ResultsExportController(
            self.screening_repository(),
            export_service=getattr(self, "_results_export_service", None),
            output_dir=getattr(self, "_results_export_output_dir", None),
        )

    # ----------------------------------------------------------

    def export_ranked_candidates_csv(self):

        return self.export_results("csv")

    # ----------------------------------------------------------

    def export_ranked_candidates_json(self):

        return self.export_results("json")

    # ----------------------------------------------------------

    def export_full_run_package_json(self):

        return self.export_results("full_package")

    # ----------------------------------------------------------

    def export_results(self, export_kind):

        controller = self.results_export_controller()
        run_id = getattr(self, "selected_results_run_id", None)

        try:
            if export_kind == "csv":
                result = controller.export_candidates_csv(run_id)
            elif export_kind == "json":
                result = controller.export_candidates_json(run_id)
            else:
                result = controller.export_full_run_package_json(run_id)
        except Exception as exc:
            result = {
                "success": False,
                "message": f"Export failed: {exc}",
                "path": None,
                "count": None,
            }

        message = result.get("message") or "Export failed."
        if result.get("success"):
            path = result.get("path")
            status_text = f"Export saved: {path}" if path else message
        else:
            status_text = message

        if hasattr(self, "screening_results_panel"):
            self.screening_results_panel.set_export_status(status_text)
            self.screening_results_panel.set_screening_status(status_text)
        return result

    # ----------------------------------------------------------

    def update_results_candidate_chart(self, candidate):

        if not hasattr(self, "screening_results_panel"):
            return None

        ticker = (
            candidate.get("ticker")
            if isinstance(candidate, dict)
            else getattr(candidate, "ticker", None)
        )
        try:
            if (
                not hasattr(self.chart_controller, "chart_data_service")
                and hasattr(self.chart_controller, "get_chart_data")
            ):
                chart_data = self.chart_controller.get_chart_data(ticker)
                chart_model = self.chart_analytics_service().build_candidate_view(
                    ticker=ticker,
                    candidate=candidate,
                    price_rows=chart_data.get("prices", []),
                    support_zones=chart_data.get("support_zones", []),
                    technical_indicators=chart_data.get("indicators", []),
                )
                if chart_data.get("warnings"):
                    from dataclasses import replace

                    chart_model = replace(
                        chart_model,
                        warnings=self.unique([*chart_model.warnings, *chart_data.get("warnings", [])]),
                    )
            else:
                chart_model = self.chart_analytics_service().build_candidate_view(
                    ticker=ticker,
                    candidate=candidate,
                )
            self.screening_results_panel.set_candidate_chart_model(chart_model)
            return chart_model
        except Exception:
            return None

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
        self.refresh_dashboard()

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

        self.save_workspace_state()

        if hasattr(self, "refresh_scheduler"):
            self.refresh_scheduler.stop()

        worker = getattr(self, "screening_worker", None)
        if worker is not None and hasattr(worker, "isRunning") and worker.isRunning():
            if hasattr(worker, "request_cancel"):
                worker.request_cancel()
            worker.quit()
            worker.wait(1000)

        self.controller.close()
        self.indicator_controller.close()
        self.support_controller.close()
        self.bounce_controller.close()
        self.scoring_controller.close()
        self.chart_controller.close()

        super().closeEvent(event)
