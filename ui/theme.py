class Theme:
    """
    Central application theme.
    """

    BACKGROUND = "#1E1E1E"
    SECONDARY = "#2A2A2A"
    SURFACE = "#323232"
    BORDER = "#4A4A4A"
    PRIMARY = "#4A90E2"
    SUCCESS = "#3FB950"
    WARNING = "#D29922"
    ERROR = "#F85149"
    TEXT = "#F2F2F2"
    MUTED_TEXT = "#B0B0B0"

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

        QLabel {{
            color: {cls.TEXT};
            background-color: transparent;
        }}

        QLabel:disabled {{
            color: {cls.MUTED_TEXT};
        }}

        QPushButton {{
            background-color: {cls.SURFACE};
            color: {cls.TEXT};
            border: 1px solid {cls.BORDER};
            border-radius: 4px;
            padding: 7px 12px;
        }}

        QPushButton:hover {{
            border-color: {cls.PRIMARY};
            background-color: {cls.SECONDARY};
        }}

        QPushButton:pressed {{
            background-color: {cls.PRIMARY};
            color: {cls.TEXT};
        }}

        QPushButton:disabled {{
            background-color: {cls.SECONDARY};
            color: {cls.MUTED_TEXT};
            border-color: {cls.SURFACE};
        }}

        QTableWidget {{
            background-color: {cls.SECONDARY};
            alternate-background-color: {cls.SURFACE};
            color: {cls.TEXT};
            gridline-color: {cls.BORDER};
            border: 1px solid {cls.BORDER};
            selection-background-color: {cls.PRIMARY};
            selection-color: {cls.TEXT};
        }}

        QTableWidget::item {{
            padding: 4px;
            border: none;
        }}

        QTableWidget::item:selected {{
            background-color: {cls.PRIMARY};
            color: {cls.TEXT};
        }}

        QHeaderView {{
            background-color: {cls.SURFACE};
            color: {cls.TEXT};
        }}

        QHeaderView::section {{
            background-color: {cls.SURFACE};
            color: {cls.TEXT};
            border: 1px solid {cls.BORDER};
            padding: 6px;
            font-weight: 600;
        }}

        QProgressBar {{
            background-color: {cls.SECONDARY};
            color: {cls.TEXT};
            border: 1px solid {cls.BORDER};
            border-radius: 4px;
            text-align: center;
            min-height: 18px;
        }}

        QProgressBar::chunk {{
            background-color: {cls.PRIMARY};
            border-radius: 3px;
        }}

        QTextEdit {{
            background-color: {cls.SECONDARY};
            color: {cls.TEXT};
            border: 1px solid {cls.BORDER};
            border-radius: 4px;
            padding: 6px;
            selection-background-color: {cls.PRIMARY};
        }}

        QLineEdit {{
            background-color: {cls.SECONDARY};
            color: {cls.TEXT};
            border: 1px solid {cls.BORDER};
            border-radius: 4px;
            padding: 6px;
            selection-background-color: {cls.PRIMARY};
        }}

        QLineEdit:focus {{
            border-color: {cls.PRIMARY};
        }}

        QGroupBox {{
            background-color: {cls.BACKGROUND};
            color: {cls.TEXT};
            border: 1px solid {cls.BORDER};
            border-radius: 4px;
            margin-top: 12px;
            padding-top: 10px;
            font-weight: 600;
        }}

        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 8px;
            padding: 0 4px;
            color: {cls.MUTED_TEXT};
        }}

        QFrame {{
            background-color: {cls.SURFACE};
            border: 1px solid {cls.BORDER};
            border-radius: 4px;
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
