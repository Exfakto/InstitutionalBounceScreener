from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLabel,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class StockDetailWindow(QDialog):
    """
    Read-only stock detail window.
    """

    def __init__(self, detail, parent=None):
        super().__init__(parent)

        self.detail = detail
        self.setWindowTitle(f'{detail["ticker"]} Details')
        self.resize(700, 800)

        self.build_ui()

    def build_ui(self):

        layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        content = QWidget()
        content_layout = QVBoxLayout(content)

        candidate = self.detail["candidate"]

        content_layout.addWidget(QLabel(f"<h2>{candidate.ticker}</h2>"))
        content_layout.addWidget(
            QLabel(
                "Overall intelligence score: "
                f"{candidate.primary_score_value:.1f}"
            )
        )
        content_layout.addWidget(
            QLabel(f'Last analysis: {self.format_value(self.detail.get("timestamp"))}')
        )

        content_layout.addWidget(QLabel("<h3>Score Breakdown</h3>"))
        content_layout.addLayout(self.score_breakdown_layout(candidate))

        content_layout.addWidget(QLabel("<h3>Score Details</h3>"))
        content_layout.addWidget(self.score_details_text(candidate))

        self.add_section(content_layout, "Fundamental Metrics", "fundamentals")
        self.add_section(content_layout, "Institutional Metrics", "institutional")
        self.add_section(content_layout, "Latest Technical Metrics", "technical")
        self.add_section(content_layout, "Best Support Zone", "support")
        self.add_section(content_layout, "Best Bounce Validation", "bounce")

        scroll.setWidget(content)
        layout.addWidget(scroll)

    def score_breakdown_layout(self, candidate):

        layout = QFormLayout()
        scores = candidate.score_map

        layout.addRow("Quality", QLabel(self.format_score(scores.get("quality_score"))))
        layout.addRow(
            "Institutional",
            QLabel(self.format_score(scores.get("institutional_score"))),
        )
        layout.addRow(
            "Technical",
            QLabel(self.format_score(scores.get("technical_score"))),
        )
        layout.addRow("Support", QLabel(self.format_score(scores.get("support_score"))))
        layout.addRow("Bounce", QLabel(self.format_score(scores.get("bounce_score"))))

        return layout

    def score_details_text(self, candidate):

        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(self.format_score_details(candidate))

        return text

    def format_score_details(self, candidate):

        lines = []

        for score in candidate.scores:
            lines.append(f"{score.name}: {score.value:.1f}")

            warnings = score.details.get("warnings", [])

            if warnings:
                lines.append("Warnings:")

                for warning in warnings:
                    lines.append(f"- {warning}")
            else:
                lines.append("Warnings: None")

            lines.append("")

        return "\n".join(lines).strip() or "Unavailable"

    def add_section(self, parent_layout, title, key):

        parent_layout.addWidget(QLabel(f"<h3>{title}</h3>"))

        metrics = self.detail.get(key) or {}

        if not metrics:
            parent_layout.addWidget(QLabel("Unavailable"))
            return

        form = QFormLayout()

        for metric, value in metrics.items():
            form.addRow(metric, QLabel(self.format_value(value)))

        parent_layout.addLayout(form)

    @staticmethod
    def format_score(score):

        if score is None:
            return "Missing"

        return f"{score.value:.1f}"

    @staticmethod
    def format_value(value):

        if value is None or value == "":
            return "Unavailable"

        return str(value)
