from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QLabel,
    QTabWidget,
    QTextEdit,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)


class CandidateDetailWindow(QDialog):
    """
    Professional read-only detail window for a selected candidate.
    """

    def __init__(self, candidate=None, detail=None, parent=None):
        super().__init__(parent)

        self.candidate = candidate
        self.detail = detail or {}
        self.summary_labels = {}
        self.overview_cards = {}
        self.section_labels = {}

        ticker = self.ticker_text()
        self.setWindowTitle(f"{ticker} Candidate Detail")
        self.resize(860, 720)

        self.build_ui()

    def build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.header_label = QLabel(self.header_text())
        self.header_label.setObjectName("CandidateDetailHeader")
        layout.addWidget(self.header_label)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("CandidateDetailTabs")
        self.tabs.addTab(self.overview_tab(), "Overview")
        self.tabs.addTab(self.metrics_tab("Technicals", "technical"), "Technicals")
        self.tabs.addTab(
            self.metrics_tab("Institutional", "institutional"),
            "Institutional",
        )
        self.tabs.addTab(self.metrics_tab("Bounce History", "bounce"), "Bounce History")
        self.tabs.addTab(self.risk_tab(), "Risk")
        layout.addWidget(self.tabs)

    def overview_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(12)

        score_card = self.create_score_card()
        top_layout.addWidget(score_card, stretch=1)

        summary_grid = QGridLayout()
        summary_grid.setContentsMargins(0, 0, 0, 0)
        summary_grid.setHorizontalSpacing(10)
        summary_grid.setVerticalSpacing(10)

        cards = [
            ("company_name", "Company Name", self.company_text()),
            ("ticker", "Ticker", self.ticker_text()),
            ("exchange", "Exchange", self.exchange_text()),
            ("sector", "Sector", self.sector_text()),
            ("industry", "Industry", self.industry_text()),
            ("current_price", "Current Price", self.price_text()),
            ("overall_rating", "Overall Rating", self.overall_rating_text()),
            ("signal", "Signal", self.signal_text()),
            ("opportunity", "Opportunity Rating", self.opportunity_text()),
            ("risk", "Risk Rating", self.risk_text()),
        ]

        for index, (key, title, value) in enumerate(cards):
            card, value_label = self.create_summary_card(title, value)
            self.summary_labels[key] = value_label
            self.overview_cards[key] = card
            summary_grid.addWidget(card, index // 2, index % 2)

        summary_container = QWidget()
        summary_container.setLayout(summary_grid)
        top_layout.addWidget(summary_container, stretch=3)

        layout.addLayout(top_layout)

        why_section = self.create_why_section()
        layout.addWidget(why_section)

        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setPlainText(self.summary_body_text())
        self.summary_text.setObjectName("CandidateDetailSummaryText")
        layout.addWidget(self.summary_text)
        return tab

    def create_score_card(self):
        card = QFrame()
        card.setObjectName("CandidateDetailScoreCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        title = QLabel("Institutional Bounce Score")
        title.setObjectName("CandidateDetailCardTitle")
        title.setAlignment(Qt.AlignCenter)

        value = QLabel(self.score_text())
        value.setObjectName("CandidateDetailScoreValue")
        value.setAlignment(Qt.AlignCenter)
        self.summary_labels["score"] = value

        rating = QLabel(self.overall_rating_text())
        rating.setObjectName("CandidateDetailScoreRating")
        rating.setAlignment(Qt.AlignCenter)

        layout.addWidget(title)
        layout.addWidget(value)
        layout.addWidget(rating)
        layout.addStretch()
        return card

    def create_summary_card(self, title, value):
        card = QFrame()
        card.setObjectName("CandidateDetailSummaryCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setObjectName("CandidateDetailCardTitle")

        value_label = QLabel(value)
        value_label.setObjectName("CandidateDetailCardValue")
        value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        value_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(value_label)
        return card, value_label

    def create_why_section(self):
        section = QFrame()
        section.setObjectName("CandidateDetailWhySection")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        title = QLabel("Why this candidate?")
        title.setObjectName("CandidateDetailSectionTitle")
        layout.addWidget(title)

        self.why_labels = []
        reasons = self.why_candidate_reasons()
        for reason in reasons:
            label = QLabel(reason)
            label.setObjectName("CandidateDetailWhyItem")
            label.setWordWrap(True)
            self.why_labels.append(label)
            layout.addWidget(label)

        return section

    def metrics_tab(self, title, key):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)

        form = QFormLayout()
        values = self.detail.get(key) or self.metric_group(key)

        if values:
            for metric, value in values.items():
                label = QLabel(self.format_value(value))
                label.setTextInteractionFlags(Qt.TextSelectableByMouse)
                self.section_labels[f"{key}.{metric}"] = label
                form.addRow(str(metric), label)
        else:
            label = QLabel("N/A")
            label.setObjectName("EmptyStateLabel")
            self.section_labels[key] = label
            form.addRow(title, label)

        layout.addLayout(form)
        layout.addStretch()
        return tab

    def risk_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)

        form = QFormLayout()
        values = self.metric_group("risk")
        values.setdefault("risk_rating", self.risk_text())
        values.setdefault("risk_reward", self.risk_reward_text())

        for metric, value in values.items():
            label = QLabel(self.format_value(value))
            label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self.section_labels[f"risk.{metric}"] = label
            form.addRow(str(metric), label)

        layout.addLayout(form)
        layout.addStretch()
        return tab

    def header_text(self):
        ticker = self.ticker_text()
        company = self.company_text()
        if company == "N/A":
            return ticker
        return f"{ticker} - {company}"

    def ticker_text(self):
        return self.format_value(self.candidate_value("ticker") or self.detail.get("ticker"))

    def company_text(self):
        return self.format_value(
            self.candidate_value("company_name")
            or self.candidate_value("company")
            or self.detail.get("company_name")
        )

    def exchange_text(self):
        return self.format_value(
            self.candidate_value("exchange")
            or self.metrics().get("exchange")
            or self.detail.get("exchange")
        )

    def sector_text(self):
        return self.format_value(
            self.candidate_value("sector")
            or self.metrics().get("sector")
            or self.detail.get("sector")
        )

    def industry_text(self):
        return self.format_value(
            self.candidate_value("industry")
            or self.metrics().get("industry")
            or self.detail.get("industry")
        )

    def price_text(self):
        value = self.candidate_value("current_price") or self.candidate_value("price")
        if value is None:
            metrics = self.metrics()
            value = metrics.get("current_price") or metrics.get("price")
        number = self.number_value(value)
        if number is None:
            return "N/A"
        return f"${number:,.2f}"

    def score_text(self):
        value = self.candidate_value("primary_score_value")
        if value is None:
            value = self.candidate_value("institutional_bounce_score")
        number = self.number_value(value)
        if number is None:
            return "N/A"
        return f"{number:.1f}"

    def signal_text(self):
        signal = self.candidate_value("signal")
        if signal:
            return str(signal)

        score = self.number_value(self.candidate_value("primary_score_value"))
        if score is None:
            return "N/A"
        if score >= 85:
            return "Strong Buy"
        if score >= 70:
            return "Buy"
        if score >= 55:
            return "Watch"
        return "Avoid"

    def overall_rating_text(self):
        score = self.number_value(self.candidate_value("primary_score_value"))
        if score is None:
            score = self.number_value(self.candidate_value("institutional_bounce_score"))
        if score is None:
            return "N/A"
        if score >= 85:
            return "Elite"
        if score >= 70:
            return "Strong"
        if score >= 55:
            return "Developing"
        return "Weak"

    def opportunity_text(self):
        opportunity = self.candidate_value("opportunity_rating")
        label = self.object_value(opportunity, "rating_label")
        score = self.number_value(self.object_value(opportunity, "rating_score"))
        if label and score is not None:
            return f"{label} {score:.1f}"
        if label:
            return str(label)
        return self.format_value(self.candidate_value("opportunity"))

    def risk_text(self):
        risk = self.candidate_value("risk_rating")
        label = self.object_value(risk, "rating_label") or self.object_value(risk, "label")
        if label:
            return str(label)
        return self.format_value(risk)

    def risk_reward_text(self):
        value = self.metrics().get("risk_reward") or self.candidate_value("risk_reward")
        number = self.number_value(value)
        if number is None:
            return "N/A"
        return f"{number:.2f}:1"

    def summary_body_text(self):
        for value in [
            self.candidate_value("summary"),
            self.candidate_value("notes"),
            self.candidate_value("setup_quality"),
            self.object_value(self.candidate_value("trade_thesis"), "summary"),
        ]:
            if value:
                return str(value)
        return "N/A"

    def why_candidate_reasons(self):
        explicit = self.first_existing(
            self.candidate_value("reasons"),
            self.metrics().get("reasons"),
        )
        if isinstance(explicit, (list, tuple)) and explicit:
            return [self.reason_text(reason) for reason in explicit]

        reasons = []
        metrics = self.metrics()
        ownership = self.number_value(
            metrics.get("institutional_ownership_pct")
            or metrics.get("institutional_score")
        )
        support_tests = self.number_value(
            metrics.get("successful_support_tests")
            or metrics.get("validated_bounces")
            or metrics.get("bounce_count")
        )
        relative_strength = self.number_value(metrics.get("relative_strength_score"))
        bounce_probability = self.number_value(
            metrics.get("bounce_probability")
            or metrics.get("historical_bounce_success_rate")
            or metrics.get("bounce_score")
        )

        if ownership is not None and ownership >= 60:
            reasons.append("Strong institutional ownership")
        if support_tests is not None and support_tests >= 3:
            reasons.append("Three successful support tests")
        if relative_strength is not None and relative_strength >= 70:
            reasons.append("Positive relative strength")
        if bounce_probability is not None and bounce_probability >= 70:
            reasons.append("High bounce probability")

        thesis = self.candidate_value("trade_thesis")
        strengths = self.object_value(thesis, "strengths")
        if not reasons and isinstance(strengths, (list, tuple)) and strengths:
            reasons.extend(strengths[:4])

        if not reasons:
            return ["N/A"]

        return [self.reason_text(reason) for reason in reasons[:4]]

    @staticmethod
    def reason_text(reason):
        text = str(reason or "").strip()
        if not text:
            text = "N/A"
        if text == "N/A":
            return "N/A"
        return f"* {text}"

    def metric_group(self, group):
        metrics = self.metrics()
        value = metrics.get(group)
        if isinstance(value, dict):
            return dict(value)
        return {}

    def metrics(self):
        value = self.candidate_value("metrics")
        return value if isinstance(value, dict) else {}

    def candidate_value(self, name):
        if self.candidate is None:
            return None
        if isinstance(self.candidate, dict):
            return self.candidate.get(name)
        return getattr(self.candidate, name, None)

    @staticmethod
    def first_existing(*values):
        for value in values:
            if value not in (None, ""):
                return value
        return None

    @staticmethod
    def object_value(source, name):
        if source is None:
            return None
        if isinstance(source, dict):
            return source.get(name)
        return getattr(source, name, None)

    @staticmethod
    def number_value(value):
        if hasattr(value, "value"):
            value = value.value
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def format_value(value):
        if value in (None, ""):
            return "N/A"
        return str(value)
