from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class TradeCard(QWidget):
    """
    Read-only display of a prepared institutional trade plan.
    """

    MISSING_VALUE = "-"
    STAR = "\u2605"
    EMPTY_STAR = "\u2606"

    TRADE_PLAN_FIELDS = [
        ("entry", "Entry", ("entry", "recommended_entry", "entry_price")),
        ("stop", "Stop", ("stop", "recommended_stop", "stop_price")),
        ("target_1", "Target 1", ("target_1",)),
        ("target_2", "Target 2", ("target_2",)),
        ("target_3", "Target 3", ("target_3",)),
    ]

    RISK_FIELDS = [
        (
            "risk_reward",
            "Risk / Reward",
            ("risk_reward", "risk_reward_ratio", "best_rr", "rr"),
        ),
        ("position_size", "Position Size", ("position_size", "shares")),
        ("confidence", "Confidence", ("confidence",)),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.group = QGroupBox("Trade Card")
        self.group.setObjectName("ResearchPreviewCard")
        group_layout = QVBoxLayout()
        group_layout.setContentsMargins(14, 16, 14, 14)
        group_layout.setSpacing(10)

        self.empty_state_label = QLabel("No trade card available.")
        self.empty_state_label.setAlignment(Qt.AlignCenter)
        self.empty_state_label.setWordWrap(True)
        self.empty_state_label.setMinimumHeight(140)

        self.dashboard_frame = QFrame()
        self.dashboard_frame.setObjectName("ResearchPreviewDashboard")
        dashboard_layout = QVBoxLayout(self.dashboard_frame)
        dashboard_layout.setContentsMargins(0, 0, 0, 0)
        dashboard_layout.setSpacing(8)

        self.ticker_label = QLabel("")
        self.ticker_label.setObjectName("ResearchPreviewTicker")
        self.ticker_label.setAlignment(Qt.AlignCenter)

        self.company_label = QLabel("")
        self.company_label.setObjectName("ResearchPreviewCompany")
        self.company_label.setAlignment(Qt.AlignCenter)
        self.company_label.setWordWrap(True)

        self.rating_label = QLabel("")
        self.rating_label.setObjectName("ResearchPreviewSignal")
        self.rating_label.setAlignment(Qt.AlignCenter)
        self.rating_label.setWordWrap(True)

        self.status_label = QLabel("")
        self.status_label.setObjectName("ResearchPreviewChecklistStatus")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)

        header_section, header_layout = self.create_section()
        header_layout.addWidget(self.ticker_label)
        header_layout.addWidget(self.company_label)
        header_layout.addWidget(self.rating_label)
        header_layout.addWidget(self.status_label)
        dashboard_layout.addWidget(header_section)

        trade_plan_section, trade_plan_layout = self.create_titled_section("Trade Plan")
        self.trade_plan_labels = {}
        for key, label, _fields in self.TRADE_PLAN_FIELDS:
            value_label = self.add_value_row(trade_plan_layout, label)
            self.trade_plan_labels[key] = value_label
        dashboard_layout.addWidget(trade_plan_section)

        risk_section, risk_layout = self.create_titled_section("Risk")
        self.risk_labels = {}
        for key, label, _fields in self.RISK_FIELDS:
            value_label = self.add_value_row(risk_layout, label)
            self.risk_labels[key] = value_label
        dashboard_layout.addWidget(risk_section)

        thesis_section, thesis_layout = self.create_titled_section("Trade Thesis")
        self.thesis_label = QLabel("No trade thesis available.")
        self.thesis_label.setObjectName("ResearchPreviewThesis")
        self.thesis_label.setWordWrap(True)
        thesis_layout.addWidget(self.thesis_label)
        dashboard_layout.addWidget(thesis_section)

        warnings_section, warnings_layout = self.create_titled_section("Warnings")
        self.warning_label = QLabel("No warnings")
        self.warning_label.setObjectName("ResearchPreviewWarnings")
        self.warning_label.setWordWrap(True)
        warnings_layout.addWidget(self.warning_label)
        dashboard_layout.addWidget(warnings_section)

        group_layout.addWidget(self.empty_state_label)
        group_layout.addWidget(self.dashboard_frame)
        group_layout.addStretch()

        self.group.setLayout(group_layout)
        layout.addWidget(self.group)

        self.clear()

    def clear(self):
        """
        Reset every section to the empty state.
        """

        self.empty_state_label.show()
        self.dashboard_frame.hide()

        self.ticker_label.setText("")
        self.company_label.setText("")
        self.rating_label.setText("Opportunity rating unavailable.")
        self.status_label.setText(self.MISSING_VALUE)

        for label in self.trade_plan_labels.values():
            label.setText(self.MISSING_VALUE)

        for label in self.risk_labels.values():
            label.setText(self.MISSING_VALUE)

        self.thesis_label.setText("No trade thesis available.")
        self.warning_label.setText("No warnings")

    def set_trade_card(self, card):
        """
        Display a prepared trade card object or dictionary.
        """

        if card is None:
            self.clear()
            return

        self.empty_state_label.hide()
        self.dashboard_frame.show()

        self.ticker_label.setText(self.format_text(self.first_value(card, ("ticker",))))
        self.company_label.setText(
            self.format_text(self.first_value(card, ("company_name", "company", "name")))
        )
        self.rating_label.setText(self.format_opportunity_rating(card))
        self.status_label.setText(
            self.format_text(self.first_value(card, ("overall_status", "status")))
        )

        for key, _label, fields in self.TRADE_PLAN_FIELDS:
            self.trade_plan_labels[key].setText(
                self.format_price(self.first_value(card, fields))
            )

        for key, _label, fields in self.RISK_FIELDS:
            value = self.first_value(card, fields)
            if key == "risk_reward":
                value = self.format_risk_reward(value)
            else:
                value = self.format_text(value)
            self.risk_labels[key].setText(value)

        self.thesis_label.setText(self.format_trade_thesis(card))
        self.warning_label.setText(self.format_warnings(self.first_value(card, ("warnings",))))

    @classmethod
    def create_section(cls):
        section = QFrame()
        section.setObjectName("ResearchPreviewSection")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)
        return section, layout

    @classmethod
    def create_titled_section(cls, title):
        section, layout = cls.create_section()
        title_label = QLabel(title)
        title_label.setObjectName("ResearchPreviewSectionTitle")
        layout.addWidget(title_label)
        return section, layout

    @staticmethod
    def add_value_row(parent_layout, label_text):
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        name_label = QLabel(label_text)
        name_label.setObjectName("ResearchPreviewFieldLabel")
        value_label = QLabel(TradeCard.MISSING_VALUE)
        value_label.setObjectName("ResearchPreviewFieldValue")
        value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        value_label.setWordWrap(True)

        row_layout.addWidget(name_label, stretch=1)
        row_layout.addWidget(value_label, stretch=1)
        parent_layout.addWidget(row)

        return value_label

    @classmethod
    def first_value(cls, source, names):
        for name in names:
            value = cls.value_for(source, name)
            if not cls.is_missing(value):
                return value

        return None

    @classmethod
    def value_for(cls, source, name):
        if source is None:
            return None

        if isinstance(source, dict):
            return source.get(name)

        return getattr(source, name, None)

    @classmethod
    def format_opportunity_rating(cls, card):
        rating = cls.value_for(card, "opportunity_rating")

        if isinstance(rating, str) and rating.strip():
            return rating.strip()

        rating_source = rating if rating is not None else card
        stars = cls.first_value(rating_source, ("stars", "star_count"))
        label = cls.first_value(
            rating_source,
            (
                "opportunity_label",
                "opportunity_rating_label",
                "rating_label",
                "label",
            ),
        )

        star_text = ""
        if not cls.is_missing(stars):
            try:
                star_count = max(0, min(5, int(stars)))
                star_text = cls.STAR * star_count + cls.EMPTY_STAR * (5 - star_count)
            except (TypeError, ValueError):
                star_text = cls.format_text(stars)

        label_text = "" if cls.is_missing(label) else str(label).strip()
        combined = " ".join(part for part in (star_text, label_text) if part)

        if combined:
            return combined

        return "Opportunity rating unavailable."

    @classmethod
    def format_trade_thesis(cls, card):
        thesis = cls.first_value(card, ("trade_thesis", "thesis"))

        if isinstance(thesis, str):
            return thesis.strip() or "No trade thesis available."

        summary = cls.first_value(thesis, ("summary",)) if thesis is not None else None
        if cls.is_missing(summary):
            summary = cls.first_value(card, ("summary",))

        return cls.format_text(summary, missing="No trade thesis available.")

    @classmethod
    def format_warnings(cls, warnings):
        if cls.is_missing(warnings):
            return "No warnings"

        if isinstance(warnings, str):
            return warnings.strip() or "No warnings"

        try:
            lines = [str(warning) for warning in warnings if not cls.is_missing(warning)]
        except TypeError:
            return cls.format_text(warnings, missing="No warnings")

        if not lines:
            return "No warnings"

        return "\n".join(f"- {line}" for line in lines)

    @classmethod
    def format_price(cls, value):
        if cls.is_missing(value):
            return cls.MISSING_VALUE

        if isinstance(value, (int, float)):
            return f"${float(value):.2f}"

        return str(value)

    @classmethod
    def format_risk_reward(cls, value):
        if cls.is_missing(value):
            return cls.MISSING_VALUE

        if isinstance(value, (int, float)):
            return f"{float(value):.2f}:1"

        return str(value)

    @classmethod
    def format_text(cls, value, missing=None):
        missing_value = cls.MISSING_VALUE if missing is None else missing

        if cls.is_missing(value):
            return missing_value

        return str(value)

    @staticmethod
    def is_missing(value):
        if value is None:
            return True

        if isinstance(value, str):
            return not value.strip()

        return False
