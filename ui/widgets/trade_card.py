from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
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
    TARGET_FIELDS = [
        ("target_1", "Target 1", ("target_1",)),
        ("target_2", "Target 2", ("target_2",)),
        ("target_3", "Target 3", ("target_3",)),
    ]
    ENTRY_FIELDS = [
        ("entry", "Entry", ("entry", "recommended_entry", "entry_price")),
    ]
    RISK_MANAGEMENT_FIELDS = [
        ("stop", "Stop", ("stop", "recommended_stop", "stop_price")),
        (
            "risk_reward",
            "Risk / Reward",
            ("risk_reward", "risk_reward_ratio", "best_rr", "rr"),
        ),
        ("confidence", "Confidence", ("confidence",)),
    ]
    POSITION_FIELDS = [
        ("position_size", "Position Size", ("position_size", "shares")),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.group = QGroupBox("Trade Card")
        self.group.setObjectName("ResearchPreviewCard")
        group_layout = QVBoxLayout()
        group_layout.setContentsMargins(16, 22, 16, 16)
        group_layout.setSpacing(12)

        self.empty_state_label = QLabel("No trade card available.")
        self.empty_state_label.setObjectName("EmptyStateLabel")
        self.empty_state_label.setAlignment(Qt.AlignCenter)
        self.empty_state_label.setWordWrap(True)
        self.empty_state_label.setMinimumHeight(140)

        self.dashboard_frame = QFrame()
        self.dashboard_frame.setObjectName("ResearchPreviewDashboard")
        dashboard_layout = QVBoxLayout(self.dashboard_frame)
        dashboard_layout.setContentsMargins(0, 0, 0, 0)
        dashboard_layout.setSpacing(12)

        actions_layout = QHBoxLayout()
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(8)
        self.copy_button = QPushButton("Copy Summary")
        self.copy_button.setObjectName("TradeCardCopyButton")
        self.copy_button.setProperty("variant", "secondary")
        self.copy_button.setMinimumHeight(34)
        self.copy_button.clicked.connect(self.copy_summary)
        self.compact_toggle_button = QPushButton("Compact")
        self.compact_toggle_button.setObjectName("TradeCardCompactToggle")
        self.compact_toggle_button.setProperty("variant", "secondary")
        self.compact_toggle_button.setMinimumHeight(34)
        self.compact_toggle_button.clicked.connect(self.toggle_compact)
        actions_layout.addWidget(self.copy_button)
        actions_layout.addWidget(self.compact_toggle_button)
        actions_layout.addStretch()

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
        dashboard_layout.addLayout(actions_layout)
        dashboard_layout.addWidget(header_section)

        setup_section, setup_layout = self.create_titled_section("Setup")
        self.setup_badge_label = QLabel("Missing Data")
        self.setup_badge_label.setObjectName("ResearchPreviewSignal")
        self.setup_badge_label.setAlignment(Qt.AlignCenter)
        setup_layout.addWidget(self.setup_badge_label)
        dashboard_layout.addWidget(setup_section)

        trade_plan_section, trade_plan_layout = self.create_titled_section("Entry Plan")
        self.trade_plan_labels = {}
        for key, label, _fields in self.ENTRY_FIELDS:
            value_label = self.add_value_row(trade_plan_layout, label)
            self.trade_plan_labels[key] = value_label
        dashboard_layout.addWidget(trade_plan_section)

        risk_section, risk_layout = self.create_titled_section("Risk Management")
        self.risk_labels = {}
        for key, label, _fields in self.RISK_MANAGEMENT_FIELDS:
            value_label = self.add_value_row(risk_layout, label)
            self.risk_labels[key] = value_label
            if key == "stop":
                self.trade_plan_labels[key] = value_label
        dashboard_layout.addWidget(risk_section)

        targets_section, targets_layout = self.create_titled_section("Targets")
        for key, label, _fields in self.TARGET_FIELDS:
            value_label = self.add_value_row(targets_layout, label)
            self.trade_plan_labels[key] = value_label
        dashboard_layout.addWidget(targets_section)

        position_section, position_layout = self.create_titled_section("Position Sizing")
        for key, label, _fields in self.POSITION_FIELDS:
            value_label = self.add_value_row(position_layout, label)
            self.risk_labels[key] = value_label
        dashboard_layout.addWidget(position_section)

        thesis_section, thesis_layout = self.create_titled_section("Warnings / Notes")
        self.thesis_label = QLabel("No trade thesis available.")
        self.thesis_label.setObjectName("ResearchPreviewThesis")
        self.thesis_label.setWordWrap(True)
        thesis_layout.addWidget(self.thesis_label)

        self.warning_label = QLabel("No warnings")
        self.warning_label.setObjectName("ResearchPreviewWarnings")
        self.warning_label.setWordWrap(True)
        thesis_layout.addWidget(self.warning_label)
        dashboard_layout.addWidget(thesis_section)

        self.compact_sections = [
            targets_section,
            position_section,
            thesis_section,
        ]
        self.is_compact = False
        self.current_summary = ""

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

        self.set_placeholder("No trade card available.")

    def set_placeholder(self, text):
        """
        Show an unavailable message without rendering stale trade plan data.
        """

        self.empty_state_label.show()
        self.dashboard_frame.hide()
        self.empty_state_label.setText(text)

        self.ticker_label.setText("")
        self.company_label.setText("")
        self.rating_label.setText("Opportunity rating unavailable.")
        self.status_label.setText(self.MISSING_VALUE)
        self.setup_badge_label.setText("Missing Data")
        self.set_badge_style(self.setup_badge_label, "missing")

        for label in self.trade_plan_labels.values():
            label.setText(self.MISSING_VALUE)

        for label in self.risk_labels.values():
            label.setText(self.MISSING_VALUE)

        self.thesis_label.setText("No trade thesis available.")
        self.warning_label.setText("No warnings")
        self.current_summary = ""
        self.set_compact(False)

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
        self.update_setup_badge(card)

        for key, _label, fields in self.ENTRY_FIELDS + self.TARGET_FIELDS:
            self.trade_plan_labels[key].setText(
                self.format_price(self.first_value(card, fields))
            )

        for key, _label, fields in self.RISK_MANAGEMENT_FIELDS + self.POSITION_FIELDS:
            value = self.first_value(card, fields)
            if key == "stop":
                value = self.format_price(value)
            elif key == "risk_reward":
                value = self.format_risk_reward(value)
            else:
                value = self.format_text(value)
            self.risk_labels[key].setText(value)

        self.thesis_label.setText(self.format_trade_thesis(card))
        self.warning_label.setText(self.format_warnings(self.first_value(card, ("warnings",))))
        self.current_summary = self.trade_plan_summary(card)

    @classmethod
    def create_section(cls):
        section = QFrame()
        section.setObjectName("ResearchPreviewSection")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(9)
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

    def update_setup_badge(self, card):
        status = self.first_value(card, ("overall_status", "status"))
        risk_reward = self.first_value(card, ("risk_reward", "risk_reward_ratio", "best_rr", "rr"))

        if not self.is_missing(status):
            status_text = str(status)
            self.setup_badge_label.setText(status_text)
            self.set_badge_style(self.setup_badge_label, self.badge_kind(status_text))
            return

        if not self.is_missing(risk_reward):
            formatted = self.format_risk_reward(risk_reward)
            self.setup_badge_label.setText(
                "Favorable Risk/Reward"
                if self.risk_reward_value(risk_reward) is not None
                and self.risk_reward_value(risk_reward) >= 2
                else formatted
            )
            self.set_badge_style(self.setup_badge_label, self.risk_badge_kind(risk_reward))
            return

        self.setup_badge_label.setText("Missing Data")
        self.set_badge_style(self.setup_badge_label, "missing")

    @classmethod
    def badge_kind(cls, text):
        normalized = str(text or "").lower()
        if "avoid" in normalized or "weak" in normalized:
            return "negative"
        if "watch" in normalized:
            return "watch"
        if "high" in normalized or "strong" in normalized or "buy" in normalized:
            return "positive"
        return "missing"

    @classmethod
    def risk_badge_kind(cls, value):
        number = cls.risk_reward_value(value)
        if number is None:
            return "missing"
        if number >= 2:
            return "positive"
        if number >= 1.2:
            return "watch"
        return "negative"

    @staticmethod
    def set_badge_style(label, kind):
        colors = {
            "positive": ("#35B779", "#11281F"),
            "watch": ("#D6A23A", "#2A2314"),
            "negative": ("#E05A5A", "#2B1719"),
            "missing": ("#7F8C99", "#202833"),
        }
        foreground, background = colors.get(kind, colors["missing"])
        label.setStyleSheet(
            f"color: {foreground};"
            f"background-color: {background};"
            f"border: 1px solid {foreground};"
            "border-radius: 6px;"
            "padding: 6px 10px;"
            "font-weight: 700;"
        )

    def toggle_compact(self):
        self.set_compact(not self.is_compact)

    def set_compact(self, compact):
        self.is_compact = bool(compact)
        for section in getattr(self, "compact_sections", []):
            section.setVisible(not self.is_compact)
        if hasattr(self, "compact_toggle_button"):
            self.compact_toggle_button.setText(
                "Expanded" if self.is_compact else "Compact"
            )

    def copy_summary(self):
        summary = self.current_summary or "No trade plan available."
        QApplication.clipboard().setText(summary)
        return summary

    def trade_plan_summary(self, card):
        values = {
            "ticker": self.format_text(self.first_value(card, ("ticker",))),
            "entry": self.format_price(self.first_value(card, ("entry", "recommended_entry", "entry_price"))),
            "stop": self.format_price(self.first_value(card, ("stop", "recommended_stop", "stop_price"))),
            "target": self.format_price(self.first_value(card, ("target_1",))),
            "risk_reward": self.format_risk_reward(
                self.first_value(card, ("risk_reward", "risk_reward_ratio", "best_rr", "rr"))
            ),
            "position_size": self.format_text(self.first_value(card, ("position_size", "shares"))),
        }
        return (
            f"{values['ticker']} trade plan | Entry {values['entry']} | "
            f"Stop {values['stop']} | Target {values['target']} | "
            f"R/R {values['risk_reward']} | Size {values['position_size']}"
        )

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

    @staticmethod
    def risk_reward_value(value):
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).replace(":1", "").strip()
        try:
            return float(text)
        except (TypeError, ValueError):
            return None

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
