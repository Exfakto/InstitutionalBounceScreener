from PySide6.QtWidgets import QFormLayout, QGroupBox, QLabel, QVBoxLayout, QWidget


class ResearchPreview(QWidget):
    """
    Read-only preview of the selected candidate score.
    """

    SCORE_FIELDS = [
        ("overall", "Overall"),
        ("quality_score", "Quality"),
        ("institutional_score", "Institutional"),
        ("technical_score", "Technical"),
        ("support_score", "Support"),
        ("bounce_score", "Bounce"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        group = QGroupBox("Research Preview")
        form = QFormLayout()

        self.ticker_label = QLabel("No candidate selected")
        self.timestamp_label = QLabel("Unavailable")
        self.score_labels = {}
        self.warning_label = QLabel("Unavailable")
        self.warning_label.setWordWrap(True)

        form.addRow("Ticker", self.ticker_label)
        form.addRow("Analysis Time", self.timestamp_label)

        for key, label in self.SCORE_FIELDS:
            value_label = QLabel("Unavailable")
            self.score_labels[key] = value_label
            form.addRow(label, value_label)

        form.addRow("Warnings", self.warning_label)

        group.setLayout(form)
        layout.addWidget(group)

    def clear(self):
        """
        Clear the preview display.
        """

        self.ticker_label.setText("No candidate selected")
        self.timestamp_label.setText("Unavailable")

        for label in self.score_labels.values():
            label.setText("Unavailable")

        self.warning_label.setText("Unavailable")

    def set_candidate(self, candidate_score):
        """
        Display a CandidateScore object.
        """

        if candidate_score is None:
            self.clear()
            return

        score_map = candidate_score.score_map

        self.ticker_label.setText(candidate_score.ticker)
        self.timestamp_label.setText(str(candidate_score.timestamp))
        self.score_labels["overall"].setText(
            self.format_score(candidate_score.composite_score)
        )
        self.score_labels["quality_score"].setText(
            self.format_score(score_map.get("quality_score"))
        )
        self.score_labels["institutional_score"].setText(
            self.format_score(score_map.get("institutional_score"))
        )
        self.score_labels["technical_score"].setText(
            self.format_score(score_map.get("technical_score"))
        )
        self.score_labels["support_score"].setText(
            self.format_score(score_map.get("support_score"))
        )
        self.score_labels["bounce_score"].setText(
            self.format_score(score_map.get("bounce_score"))
        )
        self.warning_label.setText(self.format_warnings(candidate_score))

    @staticmethod
    def format_score(score):
        if score is None:
            return "Missing"

        return f"{score.value:.1f}"

    @staticmethod
    def format_warnings(candidate_score):
        warnings = []

        for score in candidate_score.scores:
            warnings.extend(score.details.get("warnings", []))

            if score.error:
                warnings.append(score.error)

        return "; ".join(warnings) if warnings else "None"
