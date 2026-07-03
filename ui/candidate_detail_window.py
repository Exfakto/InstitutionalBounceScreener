from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLabel,
    QTabWidget,
    QTextEdit,
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

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        for key, label, value in [
            ("ticker", "Ticker", self.ticker_text()),
            ("company_name", "Company", self.company_text()),
            ("current_price", "Current Price", self.price_text()),
            ("score", "Institutional Bounce Score", self.score_text()),
            ("signal", "Signal", self.signal_text()),
            ("opportunity", "Opportunity Rating", self.opportunity_text()),
            ("risk", "Risk Rating", self.risk_text()),
        ]:
            value_label = QLabel(value)
            value_label.setObjectName("ResearchPreviewFieldValue")
            value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self.summary_labels[key] = value_label
            form.addRow(label, value_label)

        layout.addLayout(form)

        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setPlainText(self.summary_body_text())
        layout.addWidget(self.summary_text)
        return tab

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
            return "High Conviction"
        if score >= 70:
            return "Watch"
        if score >= 55:
            return "Developing"
        return "Avoid"

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
