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
        self.group.setObjectName("ResearchPreviewCard")
        group_layout = QVBoxLayout()
        group_layout.setContentsMargins(14, 16, 14, 14)
        group_layout.setSpacing(12)

        self.empty_state_label = QLabel("Select a candidate to begin research.")
        self.empty_state_label.setAlignment(Qt.AlignCenter)
        self.empty_state_label.setWordWrap(True)
        self.empty_state_label.setMinimumHeight(160)

        summary_layout = QVBoxLayout()
        summary_layout.setContentsMargins(0, 0, 0, 0)
        summary_layout.setSpacing(4)

        self.ticker_label = QLabel("")
        self.ticker_label.setObjectName("ResearchPreviewTicker")
        self.ticker_label.setAlignment(Qt.AlignCenter)
        ticker_font = self.ticker_label.font()
        ticker_font.setPointSize(18)
        ticker_font.setBold(True)
        self.ticker_label.setFont(ticker_font)

        self.signal_label = QLabel("")
        self.signal_label.setObjectName("ResearchPreviewSignal")
        self.signal_label.setAlignment(Qt.AlignCenter)
        self.signal_label.setMinimumHeight(28)
        signal_font = self.signal_label.font()
        signal_font.setBold(True)
        self.signal_label.setFont(signal_font)

        self.overall_score_label = QLabel("")
        self.overall_score_label.setObjectName("ResearchPreviewOverall")
        self.overall_score_label.setAlignment(Qt.AlignCenter)
        overall_font = self.overall_score_label.font()
        overall_font.setPointSize(28)
        overall_font.setBold(True)
        self.overall_score_label.setFont(overall_font)

        summary_layout.addWidget(self.ticker_label)
        summary_layout.addWidget(self.signal_label)
        summary_layout.addWidget(self.overall_score_label)

        self.summary_separator = self.create_separator()

        self.timestamp_label = QLabel("")
        self.timestamp_label.setObjectName("ResearchPreviewTimestamp")
        self.timestamp_label.setAlignment(Qt.AlignCenter)
        self.timestamp_label.setWordWrap(True)

        self.time_separator = self.create_separator()

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

        self.warning_separator = self.create_separator()

        self.warning_label = QLabel("No warnings")
        self.warning_label.setObjectName("ResearchPreviewWarnings")
        self.warning_label.setWordWrap(True)

        group_layout.addWidget(self.empty_state_label)
        group_layout.addLayout(summary_layout)
        group_layout.addWidget(self.summary_separator)
        group_layout.addWidget(self.timestamp_label)
        group_layout.addWidget(self.time_separator)
        group_layout.addLayout(scores_layout)
        group_layout.addWidget(self.warning_separator)
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
        self.summary_separator.hide()
        self.timestamp_label.hide()
        self.time_separator.hide()
        self.warning_separator.hide()
        self.warning_title_label.hide()
        self.warning_label.hide()

        self.ticker_label.setText("")
        self.signal_label.setText("")
        self.overall_score_label.setText("")
        self.timestamp_label.setText("")

        for key, label in self.score_labels.items():
            self.score_rows[key].hide()
            label.setText("—")

        self.warning_label.setText("No warnings")

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
        self.summary_separator.show()
        self.timestamp_label.show()
        self.time_separator.show()
        self.warning_separator.show()
        self.warning_title_label.show()
        self.warning_label.show()

        self.ticker_label.setText(candidate_score.ticker)
        self.signal_label.setText(
            self.signal_label_for_score(candidate_score.primary_score_value)
        )
        self.overall_score_label.setText(
            self.format_score(candidate_score.primary_score_value)
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
            return "—"

        if not hasattr(score, "value"):
            return f"{float(score):.1f}"

        return f"{score.value:.1f}"

    @staticmethod
    def signal_label_for_score(score):
        if score >= 90.0:
            return "🟢 STRONG BUY"

        if score >= 80.0:
            return "🟢 BUY"

        if score >= 70.0:
            return "🟡 WATCH"

        return "🔴 AVOID"

    @staticmethod
    def format_warnings(candidate_score):
        warnings = []

        for score in candidate_score.scores:
            warnings.extend(score.details.get("warnings", []))

            if score.error:
                warnings.append(score.error)

        warnings.extend(candidate_score.warnings)

        if not warnings:
            return "No warnings"

        missing_count = sum(
            1
            for warning in warnings
            if warning.lower().startswith("missing ")
        )
        lines = []

        if missing_count:
            metric_word = "metric" if missing_count == 1 else "metrics"
            lines.append(f"{missing_count} missing {metric_word}")

        lines.extend(warnings[:2])

        remaining = len(warnings) - 2

        if remaining > 0:
            lines.append(f"...and {remaining} more")

        return "\n".join(lines)

    @staticmethod
    def create_separator():
        separator = QFrame()
        separator.setObjectName("ResearchPreviewSeparator")
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Plain)

        return separator
