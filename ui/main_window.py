import sys
from datetime import datetime, timedelta

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDockWidget,
    QFormLayout,
    QGroupBox,
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
from services.market_status_service import MarketStatusService
from services.refresh_scheduler import RefreshScheduler
from services.settings_service import SettingsService
from services.workspace_state_service import WorkspaceStateService

from ui.widgets.activity_panel import ActivityPanel
from ui.widgets.candidate_table import CandidateTable
from ui.widgets.dashboard import InstitutionalDashboard
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

    DEFAULT_WORKSPACE_LAYOUT = "Default"

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
        self.candidates_by_ticker = {}
        self.active_workspace_layout = self.DEFAULT_WORKSPACE_LAYOUT

        self.setWindowTitle("Institutional Bounce Screener")
        self.resize(1600, 900)

        self.build_ui()
        self.restore_workspace_state()
        self.register_shortcuts()

        self.refresh_statistics()
        self.configure_live_refresh()

    # ----------------------------------------------------------

    def build_ui(self):

        central = QWidget()
        central.setObjectName("MainWorkspace")
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
        # Statistics
        ##########################################################

        self.kpi_strip = KpiStrip()

        main_layout.addWidget(self.kpi_strip)

        ##########################################################
        # Institutional Dashboard
        ##########################################################

        self.dashboard = InstitutionalDashboard()
        self.dashboard.setMinimumHeight(280)
        main_layout.addWidget(self.dashboard)

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

        self.screener_filters_panel = self.build_screener_filters_panel()

        self.screener_workspace_splitter = QSplitter(Qt.Horizontal)
        self.screener_workspace_splitter.setObjectName("ScreenerWorkspaceSplitter")
        self.screener_workspace_splitter.setChildrenCollapsible(False)
        self.workspace_splitter = self.screener_workspace_splitter
        self.center_splitter = self.screener_workspace_splitter

        self.price_chart.setMinimumSize(720, 360)
        self.candidates_table.setMinimumSize(640, 360)
        self.screener_filters_panel.setMinimumWidth(240)
        self.screener_filters_panel.setMaximumWidth(360)
        self.research_preview.setMinimumWidth(360)
        self.trade_card.setMinimumWidth(360)

        self.screener_workspace_splitter.addWidget(self.screener_filters_panel)
        self.screener_workspace_splitter.addWidget(self.candidates_table)
        self.screener_workspace_splitter.setStretchFactor(0, 25)
        self.screener_workspace_splitter.setStretchFactor(1, 75)
        self.screener_workspace_splitter.setSizes([300, 1100])

        main_layout.addWidget(self.screener_workspace_splitter, stretch=1)
        self.create_workspace_docks()
        self.apply_default_dock_layout()
        self.build_screener_status_bar()
        self.refresh_dashboard()
        self.refresh_watchlist()
        self.refresh_trade_journal()

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
        }

        self.chart_dock = self.workspace_docks["chart"]
        self.research_dock = self.workspace_docks["research"]
        self.trade_card_dock = self.workspace_docks["trade_card"]
        self.watchlist_dock = self.workspace_docks["watchlist"]
        self.activity_dock = self.workspace_docks["activity"]
        self.portfolio_dock = self.workspace_docks["portfolio"]

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
            }
        )
        self.addDockWidget(Qt.RightDockWidgetArea, self.chart_dock)
        self.splitDockWidget(self.chart_dock, self.research_dock, Qt.Vertical)
        self.splitDockWidget(self.research_dock, self.trade_card_dock, Qt.Vertical)

        self.addDockWidget(Qt.BottomDockWidgetArea, self.watchlist_dock)
        self.splitDockWidget(self.watchlist_dock, self.activity_dock, Qt.Horizontal)
        self.tabifyDockWidget(self.activity_dock, self.portfolio_dock)
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
            }
        )
        self.addDockWidget(Qt.RightDockWidgetArea, self.chart_dock)
        self.splitDockWidget(self.chart_dock, self.research_dock, Qt.Horizontal)
        self.splitDockWidget(self.research_dock, self.trade_card_dock, Qt.Vertical)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.watchlist_dock)
        self.tabifyDockWidget(self.watchlist_dock, self.portfolio_dock)
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
            result = self.run_screener()
            self.refresh_statistics()
            return result or {"success": True}
        except Exception as exc:
            self.clear_screener_results()
            self.activity_panel.set_progress(0)
            self.activity_panel.set_status("Refresh failed")
            self.update_screener_status(candidate_count=0)
            self.log(f"Dashboard refresh failed: {exc}")
            return {"success": False, "error": str(exc)}

    # ----------------------------------------------------------

    def apply_screener_filters(self, filters):

        for name, section in getattr(self, "filter_sections", {}).items():
            section.setChecked((filters or {}).get(name, {}).get("enabled", True))

    # ----------------------------------------------------------

    def clear_screener_results(self):

        if hasattr(self, "candidates_table"):
            self.candidates_table.populate([])
        self.candidates_by_ticker = {}
        if hasattr(self, "research_preview"):
            self.research_preview.clear()
        if hasattr(self, "trade_card"):
            self.trade_card.clear()
        if hasattr(self, "price_chart"):
            self.price_chart.clear()
        self.refresh_dashboard()

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

        self.kpi_strip.update_statistics(stats)
        self.refresh_dashboard()

    # ----------------------------------------------------------

    def refresh_dashboard(self):

        if not hasattr(self, "dashboard"):
            return

        data = self.dashboard_controller.get_dashboard_data(
            candidates=list(self.candidates_by_ticker.values()),
            last_refresh=self.last_refresh_at,
        )
        self.dashboard.set_dashboard_data(data)

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
        self.last_screen_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.update_screener_status(
            candidate_count=len(results["candidates"]),
            last_screen_time=self.last_screen_time,
        )
        self.refresh_dashboard()

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

        self.controller.close()
        self.indicator_controller.close()
        self.support_controller.close()
        self.bounce_controller.close()
        self.scoring_controller.close()
        self.chart_controller.close()

        super().closeEvent(event)
