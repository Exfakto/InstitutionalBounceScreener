from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from services.chart_data_service import ChartDataService
from ui.design_system import DashboardDesignSystem as DesignSystem


class EmptyChartDatabase:
    def get_price_history(self, ticker):
        return None

    def get_technical_indicators(self, ticker):
        return []

    def get_support_levels(self, ticker):
        return []

    def get_bounce_validations(self, ticker):
        return []

    def close(self):
        return None


class CandidateChartPanel(QWidget):
    """
    Compact chart placeholder for ranked institutional bounce candidates.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CandidateChartPanel")
        self.chart_data_service = ChartDataService(db=EmptyChartDatabase())
        self.current_chart_model = None
        self.build_ui()
        self.clear()

    def build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(DesignSystem.Spacing.SM)

        section = QFrame()
        section.setObjectName("ResearchPreviewSection")
        section.setStyleSheet(DesignSystem.card_style())
        section_layout = QVBoxLayout(section)
        section_layout.setContentsMargins(
            DesignSystem.Spacing.MD,
            DesignSystem.Spacing.MD,
            DesignSystem.Spacing.MD,
            DesignSystem.Spacing.MD,
        )
        section_layout.setSpacing(DesignSystem.Spacing.SM)

        self.title_label = QLabel("Candidate Chart")
        self.title_label.setObjectName("ResearchPreviewSectionTitle")
        section_layout.addWidget(self.title_label)

        self.empty_label = QLabel("Select a candidate to view chart context.")
        self.empty_label.setObjectName("EmptyStateLabel")
        self.empty_label.setAlignment(Qt.AlignCenter)
        section_layout.addWidget(self.empty_label)

        self.content = QWidget()
        grid = QGridLayout(self.content)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(DesignSystem.Spacing.LG)
        grid.setVerticalSpacing(DesignSystem.Spacing.XS)

        self.placeholder_label = QLabel("Lightweight chart preview")
        self.placeholder_label.setObjectName("ResearchPreviewFieldValue")
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.placeholder_label.setMinimumHeight(72)
        self.placeholder_label.setStyleSheet(
            "border: 1px solid rgba(148, 163, 184, 0.30);"
            "border-radius: 6px;"
            "padding: 12px;"
        )
        grid.addWidget(self.placeholder_label, 0, 0, 1, 2)

        self.overlay_labels = {}
        for row, (key, title) in enumerate(
            [
                ("ticker", "Ticker"),
                ("candles", "Candles"),
                ("support_zones", "Support Zones"),
                ("bounce_markers", "Bounce Markers"),
                ("technical_overlays", "Technical Overlays"),
                ("institutional_badges", "Institutional Badges"),
                ("candidate_score", "Candidate Score"),
                ("trade_markers", "Trade Markers"),
                ("price_overlays", "Price Overlays"),
                ("volume_bars", "Volume Bars"),
                ("warnings", "Warnings"),
            ],
            start=1,
        ):
            label = QLabel(title)
            label.setObjectName("ResearchPreviewFieldLabel")
            value = QLabel("N/A")
            value.setObjectName("ResearchPreviewFieldValue")
            value.setWordWrap(True)
            value.setTextInteractionFlags(Qt.TextSelectableByMouse)
            grid.addWidget(label, row, 0)
            grid.addWidget(value, row, 1)
            self.overlay_labels[key] = value

        section_layout.addWidget(self.content)
        layout.addWidget(section)

    def set_candidate(self, candidate):
        model = self.chart_data_service.build_candidate_chart_data(candidate=candidate)
        self.set_chart_model(model)

    def set_chart_model(self, model):
        if model is None:
            self.clear()
            return

        self.current_chart_model = model
        self.title_label.setText(f"Candidate Chart - {model.ticker or 'N/A'}")
        self.placeholder_label.setText(self.placeholder_text(model))
        self.overlay_labels["ticker"].setText(self.display_value(model.ticker))
        self.overlay_labels["candles"].setText(str(len(model.candles)))
        self.overlay_labels["support_zones"].setText(self.support_zone_text(model))
        self.overlay_labels["bounce_markers"].setText(self.bounce_marker_text(model))
        self.overlay_labels["technical_overlays"].setText(self.technical_text(model))
        self.overlay_labels["institutional_badges"].setText(
            self.institutional_text(model)
        )
        self.overlay_labels["candidate_score"].setText(self.annotation_text(model))
        self.overlay_labels["trade_markers"].setText(self.trade_marker_text(model))
        self.overlay_labels["price_overlays"].setText(self.price_overlay_text(model))
        self.overlay_labels["volume_bars"].setText(str(len(getattr(model, "volume_bars", []) or [])))
        self.overlay_labels["warnings"].setText(self.list_text(model.warnings))
        self.empty_label.hide()
        self.content.show()

    def clear(self):
        self.current_chart_model = None
        self.title_label.setText("Candidate Chart")
        self.empty_label.setText("Select a candidate to view chart context.")
        self.empty_label.show()
        self.content.hide()

    @staticmethod
    def placeholder_text(model):
        if not model.candles:
            return "Chart placeholder: price history unavailable."
        return (
            f"Chart placeholder: {len(model.candles)} candle(s), "
            f"{len(model.support_zones)} support zone(s), "
            f"{len(model.bounce_markers)} bounce marker(s), "
            f"{len(getattr(model, 'volume_bars', []) or [])} volume bar(s)."
        )

    @classmethod
    def support_zone_text(cls, model):
        if not model.support_zones:
            return "N/A"
        rows = []
        for zone in model.support_zones:
            rows.append(
                f"{cls.display_value(zone.zone_low)}-"
                f"{cls.display_value(zone.zone_high)} "
                f"(strength {cls.display_value(zone.strength_score)})"
            )
        return "\n".join(rows)

    @classmethod
    def bounce_marker_text(cls, model):
        if not model.bounce_markers:
            return "N/A"
        return "\n".join(
            f"{cls.display_value(marker.date)}: "
            f"{cls.display_value(marker.bounce_percentage)}%"
            for marker in model.bounce_markers
        )

    @classmethod
    def technical_text(cls, model):
        if not model.technical_overlays:
            return "N/A"
        return "\n".join(
            f"{overlay.name}: {cls.display_value(overlay.latest_value)}"
            for overlay in model.technical_overlays
        )

    @classmethod
    def institutional_text(cls, model):
        if not model.institutional_badges:
            return "N/A"
        return "\n".join(
            f"{badge.label}: {cls.display_value(badge.score)}"
            for badge in model.institutional_badges
        )

    @classmethod
    def annotation_text(cls, model):
        annotation = model.candidate_annotation
        if annotation is None:
            return "N/A"
        pieces = [
            cls.display_value(annotation.final_score),
            cls.display_value(annotation.grade),
            cls.display_value(annotation.confidence_level),
            cls.display_value(annotation.setup_label),
        ]
        return " | ".join(piece for piece in pieces if piece != "N/A") or "N/A"

    @classmethod
    def trade_marker_text(cls, model):
        markers = getattr(model, "trade_markers", []) or []
        if not markers:
            return "N/A"
        return "\n".join(
            f"{cls.display_value(marker.date)}: {marker.marker_type} @ {cls.display_value(marker.price)}"
            for marker in markers
        )

    @classmethod
    def price_overlay_text(cls, model):
        overlays = getattr(model, "price_overlays", []) or []
        if not overlays:
            return "N/A"
        return "\n".join(
            f"{overlay.label}: {cls.display_value(overlay.price)}"
            for overlay in overlays
        )

    @staticmethod
    def display_value(value):
        if value in (None, ""):
            return "N/A"
        if isinstance(value, float):
            return f"{value:.2f}"
        return str(value)

    @staticmethod
    def list_text(values):
        if not values:
            return "N/A"
        if isinstance(values, (list, tuple)):
            return "\n".join(str(value) for value in values)
        return str(values)
