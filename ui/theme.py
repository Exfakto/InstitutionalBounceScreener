class Theme:
    """
    Central application theme.
    """

    BACKGROUND = "#15181C"
    SECONDARY = "#1E242B"
    SURFACE = "#262D35"
    ELEVATED = "#2F3842"
    BORDER = "#3D4652"
    SOFT_BORDER = "#2B333D"
    PRIMARY = "#4F8FDB"
    PRIMARY_SOFT = "#203B58"
    SUCCESS = "#41B883"
    WARNING = "#D6A23A"
    ERROR = "#E05A5A"
    TEXT = "#F4F7FA"
    MUTED_TEXT = "#A8B3C1"
    SUBTLE_TEXT = "#778391"

    @classmethod
    def load_stylesheet(cls):
        """
        Return the application stylesheet.
        """

        return f"""
        QMainWindow {{
            background-color: {cls.BACKGROUND};
            color: {cls.TEXT};
        }}

        QWidget {{
            background-color: {cls.BACKGROUND};
            color: {cls.TEXT};
            font-family: "Segoe UI", Arial, sans-serif;
            font-size: 10pt;
        }}

        QWidget#ActivityPanel {{
            background-color: {cls.BACKGROUND};
        }}

        QLabel {{
            color: {cls.TEXT};
            background-color: transparent;
        }}

        QLabel:disabled {{
            color: {cls.SUBTLE_TEXT};
        }}

        QPushButton {{
            background-color: {cls.SURFACE};
            color: {cls.TEXT};
            border: 1px solid {cls.BORDER};
            border-radius: 5px;
            padding: 8px 12px;
            min-height: 26px;
            font-weight: 600;
        }}

        QPushButton:hover {{
            border-color: {cls.PRIMARY};
            background-color: {cls.ELEVATED};
        }}

        QPushButton:pressed {{
            background-color: {cls.PRIMARY_SOFT};
            color: {cls.TEXT};
        }}

        QPushButton:disabled {{
            background-color: {cls.SECONDARY};
            color: {cls.SUBTLE_TEXT};
            border-color: {cls.SOFT_BORDER};
        }}

        QTableWidget {{
            background-color: {cls.SECONDARY};
            alternate-background-color: {cls.SURFACE};
            color: {cls.TEXT};
            gridline-color: {cls.SOFT_BORDER};
            border: 1px solid {cls.BORDER};
            border-radius: 6px;
            selection-background-color: {cls.PRIMARY_SOFT};
            selection-color: {cls.TEXT};
            outline: none;
        }}

        QTableWidget::item {{
            padding: 7px 8px;
            border: none;
        }}

        QTableWidget::item:selected {{
            background-color: {cls.PRIMARY_SOFT};
            color: {cls.TEXT};
        }}

        QHeaderView {{
            background-color: {cls.ELEVATED};
            color: {cls.TEXT};
        }}

        QHeaderView::section {{
            background-color: {cls.ELEVATED};
            color: {cls.TEXT};
            border: none;
            border-right: 1px solid {cls.SOFT_BORDER};
            border-bottom: 1px solid {cls.BORDER};
            padding: 8px;
            font-weight: 700;
        }}

        QProgressBar {{
            background-color: {cls.SECONDARY};
            color: {cls.TEXT};
            border: 1px solid {cls.BORDER};
            border-radius: 5px;
            text-align: center;
            min-height: 18px;
        }}

        QProgressBar::chunk {{
            background-color: {cls.PRIMARY};
            border-radius: 4px;
        }}

        QTextEdit {{
            background-color: {cls.SECONDARY};
            color: {cls.TEXT};
            border: 1px solid {cls.BORDER};
            border-radius: 6px;
            padding: 8px;
            selection-background-color: {cls.PRIMARY};
            font-family: "Consolas", "Segoe UI", monospace;
            font-size: 9pt;
        }}

        QLineEdit {{
            background-color: {cls.SECONDARY};
            color: {cls.TEXT};
            border: 1px solid {cls.BORDER};
            border-radius: 5px;
            padding: 7px;
            selection-background-color: {cls.PRIMARY};
        }}

        QLineEdit:focus {{
            border-color: {cls.PRIMARY};
        }}

        QGroupBox {{
            background-color: {cls.SECONDARY};
            color: {cls.TEXT};
            border: 1px solid {cls.BORDER};
            border-radius: 6px;
            margin-top: 14px;
            padding-top: 14px;
            font-weight: 700;
        }}

        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 10px;
            padding: 0 6px;
            color: {cls.MUTED_TEXT};
            background-color: {cls.SECONDARY};
        }}

        QFrame {{
            background-color: {cls.SURFACE};
            border: 1px solid {cls.BORDER};
            border-radius: 6px;
        }}

        QFrame#HeaderBar {{
            background-color: {cls.SURFACE};
            border: 1px solid {cls.BORDER};
            border-radius: 7px;
        }}

        QLabel#HeaderTitle {{
            color: {cls.TEXT};
            font-size: 16pt;
            font-weight: 700;
        }}

        QLabel#HeaderSubtitle,
        QLabel#HeaderStatus,
        QLabel#HeaderVersion,
        QLabel#ToolbarGroupLabel,
        QLabel#ResearchPreviewTimestamp,
        QLabel#ResearchPreviewSectionTitle {{
            color: {cls.MUTED_TEXT};
        }}

        QLabel#ToolbarGroupLabel {{
            font-size: 8pt;
            font-weight: 700;
            text-transform: uppercase;
            padding-left: 4px;
            padding-right: 4px;
        }}

        QFrame#ToolbarSeparator {{
            background-color: {cls.BORDER};
            border: none;
            min-width: 1px;
            max-width: 1px;
            margin-left: 6px;
            margin-right: 6px;
        }}

        QFrame#ResearchPreviewSeparator {{
            background-color: {cls.BORDER};
            border: none;
            max-height: 1px;
            margin-top: 2px;
            margin-bottom: 2px;
        }}

        QFrame#ResearchPreviewDashboard {{
            background-color: transparent;
            border: none;
        }}

        QFrame#ResearchPreviewSection {{
            background-color: {cls.SECONDARY};
            border: 1px solid {cls.BORDER};
            border-radius: 6px;
        }}

        QFrame#KpiCard {{
            background-color: {cls.SURFACE};
            border: 1px solid {cls.BORDER};
            border-radius: 7px;
        }}

        QLabel#ResearchPreviewTicker {{
            color: {cls.TEXT};
            font-size: 17pt;
            font-weight: 700;
        }}

        QLabel#ResearchPreviewCompany,
        QLabel#ResearchPreviewFieldLabel {{
            color: {cls.MUTED_TEXT};
        }}

        QLabel#ResearchPreviewFieldValue {{
            color: {cls.TEXT};
            font-weight: 700;
        }}

        QLabel#ResearchPreviewSignal {{
            color: {cls.TEXT};
            background-color: {cls.PRIMARY_SOFT};
            border: 1px solid {cls.BORDER};
            border-radius: 5px;
            padding: 5px 9px;
            font-weight: 700;
        }}

        QLabel#ResearchPreviewChecklistStatus {{
            color: {cls.TEXT};
            background-color: {cls.SURFACE};
            border: 1px solid {cls.BORDER};
            border-radius: 4px;
            padding: 3px 6px;
            font-size: 8pt;
            font-weight: 700;
        }}

        QLabel#ResearchPreviewChecklistStatus[status="pass"] {{
            color: {cls.SUCCESS};
            border-color: {cls.SUCCESS};
        }}

        QLabel#ResearchPreviewChecklistStatus[status="warning"] {{
            color: {cls.WARNING};
            border-color: {cls.WARNING};
        }}

        QLabel#ResearchPreviewChecklistStatus[status="fail"] {{
            color: {cls.ERROR};
            border-color: {cls.ERROR};
        }}

        QLabel#ResearchPreviewThesis {{
            color: {cls.MUTED_TEXT};
            background-color: {cls.BACKGROUND};
            border: 1px solid {cls.BORDER};
            border-radius: 6px;
            padding: 9px;
        }}

        QLabel#ResearchPreviewOverall {{
            color: {cls.PRIMARY};
            font-size: 27pt;
            font-weight: 700;
        }}

        QLabel#ResearchPreviewWarnings {{
            color: {cls.MUTED_TEXT};
            line-height: 125%;
        }}

        QGroupBox#ResearchPreviewCard,
        QGroupBox#ActivityLogGroup {{
            background-color: {cls.SECONDARY};
            border-color: {cls.BORDER};
        }}

        QTabWidget::pane {{
            background-color: {cls.SECONDARY};
            border: 1px solid {cls.BORDER};
            border-radius: 6px;
            top: -1px;
        }}

        QTabBar::tab {{
            background-color: {cls.BACKGROUND};
            color: {cls.MUTED_TEXT};
            border: 1px solid {cls.SOFT_BORDER};
            border-bottom: none;
            padding: 8px 13px;
            margin-right: 3px;
            border-top-left-radius: 5px;
            border-top-right-radius: 5px;
            font-weight: 600;
        }}

        QTabBar::tab:selected {{
            background-color: {cls.SECONDARY};
            color: {cls.TEXT};
            border-color: {cls.BORDER};
        }}

        QTabBar::tab:hover {{
            color: {cls.TEXT};
            background-color: {cls.SURFACE};
        }}

        QSplitter::handle {{
            background-color: {cls.BACKGROUND};
        }}

        QSplitter::handle:horizontal {{
            width: 8px;
        }}

        QSplitter::handle:vertical {{
            height: 8px;
        }}

        QLabel#PriceChartSummary {{
            color: {cls.MUTED_TEXT};
            background-color: {cls.SECONDARY};
            border: 1px solid {cls.BORDER};
            border-radius: 6px;
            padding: 12px;
            font-weight: 600;
        }}

        QLabel#PriceChartReadout {{
            color: {cls.MUTED_TEXT};
            background-color: {cls.SECONDARY};
            border: 1px solid {cls.SOFT_BORDER};
            border-radius: 5px;
            padding: 7px 9px;
            font-family: "Consolas", "Segoe UI", monospace;
            font-size: 9pt;
        }}

        QScrollBar:vertical {{
            background-color: {cls.BACKGROUND};
            width: 12px;
            margin: 0;
        }}

        QScrollBar::handle:vertical {{
            background-color: {cls.BORDER};
            border-radius: 4px;
            min-height: 20px;
        }}

        QScrollBar::handle:vertical:hover {{
            background-color: {cls.MUTED_TEXT};
        }}

        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        """

    @classmethod
    def apply(cls, app):
        """
        Apply the application theme to a QApplication.
        """

        app.setStyleSheet(cls.load_stylesheet())
