from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class ResearchPreview(QWidget):
    """
    Read-only preview of the selected candidate score.
    """

    SCORE_FIELDS = [
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

        self.group = QGroupBox("Research Preview")
        group_layout = QVBoxLayout()
        group_layout.setContentsMargins(12, 14, 12, 12)
        group_layout.setSpacing(10)

        self.empty_state_label = QLabel("Select a candidate to view research preview.")
        self.empty_state_label.setAlignment(Qt.AlignCenter)
        self.empty_state_label.setWordWrap(True)

        summary_layout = QVBoxLayout()
        summary_layout.setContentsMargins(0, 0, 0, 0)
        summary_layout.setSpacing(4)

        self.ticker_label = QLabel("")
        self.ticker_label.setObjectName("ResearchPreviewTicker")
        self.ticker_label.setAlignment(Qt.AlignCenter)

        self.signal_label = QLabel("")
        self.signal_label.setObjectName("ResearchPreviewSignal")
        self.signal_label.setAlignment(Qt.AlignCenter)

        self.overall_score_label = QLabel("")
        self.overall_score_label.setObjectName("ResearchPreviewOverall")
        self.overall_score_label.setAlignment(Qt.AlignCenter)

        summary_layout.addWidget(self.ticker_label)
        summary_layout.addWidget(self.signal_label)
        summary_layout.addWidget(self.overall_score_label)

        self.separator = QFrame()
        self.separator.setFrameShape(QFrame.HLine)
        self.separator.setFrameShadow(QFrame.Plain)

        self.timestamp_label = QLabel("")
        self.timestamp_label.setObjectName("ResearchPreviewTimestamp")
        self.timestamp_label.setWordWrap(True)

        self.score_rows = {}
        self.score_labels = {}

        scores_layout = QVBoxLayout()
        scores_layout.setContentsMargins(0, 0, 0, 0)
        scores_layout.setSpacing(6)

        for key, label in self.SCORE_FIELDS:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(8)

            name_label = QLabel(label)
            value_label = QLabel("Missing")
            value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            self.score_rows[key] = row
            self.score_labels[key] = value_label

            row_layout.addWidget(name_label, stretch=1)
            row_layout.addWidget(value_label)
            scores_layout.addWidget(row)

        self.warning_title_label = QLabel("Warnings")
        self.warning_title_label.setObjectName("ResearchPreviewSectionTitle")

        self.warning_label = QLabel("None")
        self.warning_label.setWordWrap(True)

        group_layout.addWidget(self.empty_state_label)
        group_layout.addLayout(summary_layout)
        group_layout.addWidget(self.separator)
        group_layout.addWidget(self.timestamp_label)
        group_layout.addLayout(scores_layout)
        group_layout.addWidget(self.warning_title_label)
        group_layout.addWidget(self.warning_label)
        group_layout.addStretch()

        self.group.setLayout(group_layout)
        layout.addWidget(self.group)

        self.clear()

    def clear(self):
        """
        Clear the preview display.
        """

        self.empty_state_label.show()
        self.ticker_label.hide()
        self.signal_label.hide()
        self.overall_score_label.hide()
        self.separator.hide()
        self.timestamp_label.hide()
        self.warning_title_label.hide()
        self.warning_label.hide()

        self.ticker_label.setText("")
        self.signal_label.setText("")
        self.overall_score_label.setText("")
        self.timestamp_label.setText("")

        for key, label in self.score_labels.items():
            self.score_rows[key].hide()
            label.setText("Missing")

        self.warning_label.setText("None")

    def set_candidate(self, candidate_score):
        """
        Display a CandidateScore object.
        """

        if candidate_score is None:
            self.clear()
            return

        score_map = candidate_score.score_map

        self.empty_state_label.hide()
        self.ticker_label.show()
        self.signal_label.show()
        self.overall_score_label.show()
        self.separator.show()
        self.timestamp_label.show()
        self.warning_title_label.show()
        self.warning_label.show()

        self.ticker_label.setText(candidate_score.ticker)
        self.signal_label.setText(
            self.signal_label_for_score(candidate_score.composite_score.value)
        )
        self.overall_score_label.setText(
            self.format_score(candidate_score.composite_score)
        )
        self.timestamp_label.setText(f"Analysis Time: {candidate_score.timestamp}")

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

        for row in self.score_rows.values():
            row.show()

        self.warning_label.setText(self.format_warnings(candidate_score))

    @staticmethod
    def format_score(score):
        if score is None:
            return "Missing"

        return f"{score.value:.1f}"

    @staticmethod
    def signal_label_for_score(score):
        if score >= 90.0:
            return "STRONG BUY"

        if score >= 80.0:
            return "BUY"

        if score >= 70.0:
            return "WATCH"

        return "AVOID"

    @staticmethod
    def format_warnings(candidate_score):
        warnings = []

        for score in candidate_score.scores:
            warnings.extend(score.details.get("warnings", []))

            if score.error:
                warnings.append(score.error)

        return "; ".join(warnings) if warnings else "None"
