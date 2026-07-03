from ui.design_system import DashboardDesignSystem as DesignSystem


class Theme:
    """
    Central application theme.
    """

    BACKGROUND = DesignSystem.Colors.BACKGROUND
    PANEL_BACKGROUND = DesignSystem.Colors.PANEL
    ELEVATED_PANEL = DesignSystem.Colors.ELEVATED
    BORDER = DesignSystem.Colors.BORDER
    MUTED_BORDER = DesignSystem.Colors.BORDER_MUTED
    PRIMARY_TEXT = DesignSystem.Colors.TEXT_PRIMARY
    SECONDARY_TEXT = DesignSystem.Colors.TEXT_SECONDARY
    MUTED_TEXT = DesignSystem.Colors.TEXT_MUTED
    POSITIVE = DesignSystem.Colors.SUCCESS
    NEGATIVE = DesignSystem.Colors.DANGER
    WARNING = DesignSystem.Colors.WARNING
    ACCENT = DesignSystem.Colors.ACCENT
    ACCENT_MUTED = DesignSystem.Colors.ACCENT_SOFT
    CARD_BACKGROUND = DesignSystem.Colors.CARD
    HEADER_BACKGROUND = DesignSystem.Colors.HEADER

    SECONDARY = PANEL_BACKGROUND
    SURFACE = CARD_BACKGROUND
    ELEVATED = ELEVATED_PANEL
    SOFT_BORDER = MUTED_BORDER
    PRIMARY = ACCENT
    PRIMARY_SOFT = ACCENT_MUTED
    SUCCESS = POSITIVE
    ERROR = NEGATIVE
    TEXT = PRIMARY_TEXT
    SUBTLE_TEXT = MUTED_TEXT

    @classmethod
    def card_style(cls):
        return DesignSystem.card_style()

    @classmethod
    def section_title_style(cls):
        return DesignSystem.section_title_style()

    @classmethod
    def muted_label_style(cls):
        return f"color: {cls.MUTED_TEXT}; font-weight: 500;"

    @classmethod
    def value_label_style(cls):
        return f"color: {cls.PRIMARY_TEXT}; font-weight: 700;"

    @classmethod
    def badge_style(cls, kind="neutral"):
        colors = {
            "positive": (cls.POSITIVE, "#11281F"),
            "negative": (cls.NEGATIVE, "#2B1719"),
            "warning": (cls.WARNING, "#2A2314"),
            "accent": (cls.ACCENT, cls.ACCENT_MUTED),
            "neutral": (cls.SECONDARY_TEXT, cls.ELEVATED_PANEL),
        }
        foreground, background = colors.get(kind, colors["neutral"])
        return (
            f"color: {foreground};"
            f"background-color: {background};"
            f"border: 1px solid {foreground};"
            f"border-radius: {DesignSystem.Radius.MD}px;"
            f"padding: {DesignSystem.Spacing.XS}px {DesignSystem.Spacing.SM}px;"
            "font-weight: 700;"
        )

    @classmethod
    def button_style(cls, kind="secondary"):
        if kind == "primary":
            return (
                f"background-color: {cls.ACCENT};"
                f"color: {cls.PRIMARY_TEXT};"
                f"border: 1px solid {cls.ACCENT};"
                f"border-radius: {DesignSystem.Radius.MD}px;"
                f"padding: {DesignSystem.Spacing.SM}px {DesignSystem.Spacing.LG}px;"
                "font-weight: 700;"
            )
        return (
            f"background-color: {cls.ELEVATED_PANEL};"
            f"color: {cls.PRIMARY_TEXT};"
            f"border: 1px solid {cls.BORDER};"
            f"border-radius: {DesignSystem.Radius.MD}px;"
            f"padding: {DesignSystem.Spacing.SM}px {DesignSystem.Spacing.MD}px;"
            "font-weight: 600;"
        )

    @classmethod
    def table_style(cls):
        return (
            f"background-color: {cls.PANEL_BACKGROUND};"
            f"alternate-background-color: {cls.CARD_BACKGROUND};"
            f"color: {cls.PRIMARY_TEXT};"
            f"border: 1px solid {cls.BORDER};"
            f"border-radius: {DesignSystem.Table.RADIUS}px;"
            "gridline-color: transparent;"
            f"selection-background-color: {cls.ACCENT_MUTED};"
            f"selection-color: {cls.PRIMARY_TEXT};"
        )

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

        QStatusBar {{
            background-color: {cls.HEADER_BACKGROUND};
            color: {cls.SECONDARY_TEXT};
            border-top: 1px solid {cls.MUTED_BORDER};
            padding: 5px 8px;
        }}

        QWidget {{
            background-color: {cls.BACKGROUND};
            color: {cls.TEXT};
            font-family: "Segoe UI", Arial, sans-serif;
            font-size: {DesignSystem.Typography.BASE_PT}pt;
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
            background-color: {cls.ELEVATED_PANEL};
            color: {cls.TEXT};
            border: 1px solid {cls.BORDER};
            border-radius: {DesignSystem.Radius.MD}px;
            padding: {DesignSystem.Spacing.SM}px {DesignSystem.Spacing.LG}px;
            min-height: 30px;
            font-weight: 600;
        }}

        QPushButton:hover {{
            border-color: {cls.PRIMARY};
            background-color: {cls.CARD_BACKGROUND};
        }}

        QPushButton:pressed {{
            background-color: {cls.PRIMARY_SOFT};
            color: {cls.TEXT};
        }}

        QPushButton:disabled {{
            background-color: {cls.SECONDARY};
            color: {cls.SUBTLE_TEXT};
            border-color: {cls.SOFT_BORDER};
            font-weight: 600;
        }}

        QPushButton[variant="primary"] {{
            background-color: {cls.ACCENT};
            border-color: {cls.ACCENT};
            color: {cls.PRIMARY_TEXT};
            font-weight: 800;
        }}

        QPushButton[variant="secondary"] {{
            background-color: {cls.ELEVATED_PANEL};
            border-color: {cls.BORDER};
        }}

        QTableWidget {{
            background-color: {cls.SECONDARY};
            alternate-background-color: {cls.SURFACE};
            color: {cls.TEXT};
            gridline-color: transparent;
            border: 1px solid {cls.BORDER};
            border-radius: {DesignSystem.Table.RADIUS}px;
            selection-background-color: {cls.PRIMARY_SOFT};
            selection-color: {cls.TEXT};
            outline: none;
        }}

        QTableWidget::item {{
            padding: {DesignSystem.Table.CELL_PADDING_VERTICAL}px {DesignSystem.Table.CELL_PADDING_HORIZONTAL}px;
            border: none;
        }}

        QTableWidget::item:hover {{
            background-color: {cls.ELEVATED_PANEL};
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
            background-color: {cls.HEADER_BACKGROUND};
            color: {cls.SECONDARY_TEXT};
            border: none;
            border-right: 1px solid {cls.SOFT_BORDER};
            border-bottom: 1px solid {cls.BORDER};
            padding: {DesignSystem.Table.HEADER_PADDING_VERTICAL}px {DesignSystem.Table.HEADER_PADDING_HORIZONTAL}px;
            font-weight: 800;
        }}

        QTableCornerButton::section {{
            background-color: {cls.HEADER_BACKGROUND};
            border: none;
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
            border-radius: {DesignSystem.Radius.LG}px;
            margin-top: {DesignSystem.Spacing.LG}px;
            padding-top: {DesignSystem.Spacing.LG}px;
            font-weight: 700;
        }}

        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: {DesignSystem.Spacing.MD}px;
            padding: 0 {DesignSystem.Spacing.SM}px;
            color: {cls.SECONDARY_TEXT};
            background-color: {cls.SECONDARY};
            font-size: {DesignSystem.Typography.SMALL_PT}pt;
            font-weight: 800;
        }}

        QFrame {{
            background-color: {cls.SURFACE};
            border: 1px solid {cls.BORDER};
            border-radius: 6px;
        }}

        QFrame#HeaderBar {{
            background-color: {cls.HEADER_BACKGROUND};
            border: 1px solid {cls.BORDER};
            border-radius: {DesignSystem.Radius.XL}px;
        }}

        QLabel#HeaderTitle {{
            color: {cls.TEXT};
            font-size: {DesignSystem.Typography.TITLE_PT}pt;
            font-weight: 800;
            letter-spacing: 0px;
        }}

        QLabel#HeaderSubtitle,
        QLabel#HeaderStatus,
        QLabel#HeaderVersion,
        QLabel#ToolbarGroupLabel,
        QLabel#ResearchPreviewTimestamp,
        QLabel#ResearchPreviewSectionTitle {{
            color: {cls.MUTED_TEXT};
        }}

        QLabel#HeaderStatus {{
            font-weight: 600;
        }}

        QLabel#HeaderMarketStatus {{
            color: {cls.SECONDARY_TEXT};
            background-color: {cls.ACCENT_MUTED};
            border: 1px solid {cls.BORDER};
            border-radius: 6px;
            padding: 4px 8px;
            font-weight: 700;
        }}

        QLabel#HeaderRefreshStatus {{
            color: {cls.SECONDARY_TEXT};
            background-color: {cls.PANEL_BACKGROUND};
            border: 1px solid {cls.MUTED_BORDER};
            border-radius: 5px;
            padding: 3px 8px;
        }}

        QLabel#ToolbarGroupLabel {{
            font-size: {DesignSystem.Typography.CAPTION_PT}pt;
            font-weight: 800;
            text-transform: uppercase;
            padding-left: {DesignSystem.Spacing.XS}px;
            padding-right: {DesignSystem.Spacing.XS}px;
        }}

        QWidget#OperationsToolbar {{
            background-color: transparent;
            padding-top: {DesignSystem.Spacing.XS}px;
            padding-bottom: {DesignSystem.Spacing.XS}px;
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
            background-color: {cls.CARD_BACKGROUND};
            border: 1px solid {cls.BORDER};
            border-radius: {DesignSystem.Radius.LG}px;
        }}

        QFrame#KpiCard {{
            background-color: {cls.CARD_BACKGROUND};
            border: 1px solid {cls.BORDER};
            border-radius: {DesignSystem.Radius.LG}px;
        }}

        QLabel#KpiTitle {{
            color: {cls.MUTED_TEXT};
            font-size: {DesignSystem.Typography.SMALL_PT}pt;
            font-weight: 800;
        }}

        QLabel#KpiValue {{
            color: {cls.PRIMARY_TEXT};
            font-size: 18pt;
            font-weight: 800;
        }}

        QLabel#ResearchPreviewTicker {{
            color: {cls.TEXT};
            font-size: 17pt;
            font-weight: 700;
        }}

        QLabel#ResearchPreviewCompany,
        QLabel#ResearchPreviewFieldLabel {{
            color: {cls.MUTED_TEXT};
            font-weight: 600;
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
            background-color: {cls.PANEL_BACKGROUND};
            border: 1px solid {cls.BORDER};
            border-radius: 8px;
            padding: 9px;
        }}

        QLabel#ResearchPreviewOverall {{
            color: {cls.PRIMARY};
            font-size: 27pt;
            font-weight: 700;
        }}

        QLabel#ResearchPreviewWarnings {{
            color: {cls.SECONDARY_TEXT};
            background-color: {cls.PANEL_BACKGROUND};
            border: 1px solid {cls.MUTED_BORDER};
            border-radius: 6px;
            padding: 8px;
            line-height: 125%;
        }}

        QLabel#EmptyStateLabel {{
            color: {cls.SECONDARY_TEXT};
            background-color: {cls.PANEL_BACKGROUND};
            border: 1px solid {cls.MUTED_BORDER};
            border-radius: {DesignSystem.Radius.LG}px;
            padding: {DesignSystem.Spacing.XL}px;
            font-weight: 600;
            line-height: 130%;
        }}

        QGroupBox#ResearchPreviewCard,
        QGroupBox#ActivityLogGroup {{
            background-color: {cls.SECONDARY};
            border-color: {cls.BORDER};
        }}

        QDockWidget {{
            color: {cls.SECONDARY_TEXT};
        }}

        QDockWidget::title {{
            background-color: {cls.HEADER_BACKGROUND};
            color: {cls.SECONDARY_TEXT};
            border: 1px solid {cls.BORDER};
            border-bottom: none;
            padding: 7px 9px;
            font-weight: 800;
            text-align: left;
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
            color: {cls.SECONDARY_TEXT};
            background-color: {cls.PANEL_BACKGROUND};
            border: 1px solid {cls.BORDER};
            border-radius: 8px;
            padding: 18px;
            font-weight: 600;
        }}

        QFrame#PriceChartHeader {{
            background-color: {cls.HEADER_BACKGROUND};
            border: 1px solid {cls.BORDER};
            border-radius: 7px;
        }}

        QLabel#PriceChartHeaderTitle {{
            color: {cls.PRIMARY_TEXT};
            font-size: 13pt;
            font-weight: 800;
        }}

        QLabel#PriceChartHeaderMeta {{
            color: {cls.SECONDARY_TEXT};
            font-size: 9pt;
            font-weight: 600;
        }}

        QLabel#PriceChartReadout {{
            color: {cls.MUTED_TEXT};
            background-color: {cls.PANEL_BACKGROUND};
            border: 1px solid {cls.SOFT_BORDER};
            border-radius: 6px;
            padding: 8px 10px;
            font-family: "Consolas", "Segoe UI", monospace;
            font-size: 9pt;
        }}

        QWidget#PriceChartPanel {{
            background-color: {cls.PANEL_BACKGROUND};
            border: 1px solid {cls.BORDER};
            border-radius: {DesignSystem.Radius.LG}px;
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
