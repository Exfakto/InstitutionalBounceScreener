from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class LegacyResearchPreview(QWidget):
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

        self.group = QGroupBox("Research Preview - Gen 2 Overall")
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


class ResearchPreview(QWidget):
    """
    Read-only decision dashboard for the selected candidate score.
    """

    SUMMARY_FIELDS = [
        ("overall", "Overall Intelligence Score"),
        ("opportunity", "Opportunity Score"),
        ("checklist", "Checklist Completion"),
    ]
    SCORE_FIELDS = LegacyResearchPreview.SCORE_FIELDS
    CHECKLIST_ITEMS = [
        ("near_support", "Near Support", "Near validated support"),
        (
            "bounce_validation",
            "Bounce Validation",
            "Bounce success rate acceptable",
        ),
        ("relative_strength", "Relative Strength", "Relative Strength strong"),
        ("trend", "Trend", "Trend aligned"),
        (
            "institutional_buying",
            "Institutional Buying",
            "Institutional ownership acceptable",
        ),
        (
            "institutional_momentum",
            "Institutional Momentum",
            "Institutional momentum positive",
        ),
        ("volume", "Volume", "Volume accumulation present"),
        ("earnings_window", "Earnings Window", "Earnings window safe"),
        ("atr_risk", "ATR Risk", "ATR risk acceptable"),
        (
            "opportunity_rating",
            "Opportunity Rating",
            "Opportunity rating acceptable",
        ),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.group = QGroupBox("Research Preview 2.0")
        self.group.setObjectName("ResearchPreviewCard")
        group_layout = QVBoxLayout()
        group_layout.setContentsMargins(12, 14, 12, 12)
        group_layout.setSpacing(8)

        self.empty_state_label = QLabel("Select a candidate to begin research.")
        self.empty_state_label.setAlignment(Qt.AlignCenter)
        self.empty_state_label.setWordWrap(True)
        self.empty_state_label.setMinimumHeight(160)

        self.dashboard_frame = QFrame()
        self.dashboard_frame.setObjectName("ResearchPreviewDashboard")
        dashboard_layout = QVBoxLayout(self.dashboard_frame)
        dashboard_layout.setContentsMargins(0, 0, 0, 0)
        dashboard_layout.setSpacing(8)

        header_section = self.create_section()
        header_layout = header_section.layout()
        header_layout.setContentsMargins(8, 8, 8, 8)
        header_layout.setSpacing(3)

        self.ticker_label = QLabel("")
        self.ticker_label.setObjectName("ResearchPreviewTicker")
        self.ticker_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.company_label = QLabel("")
        self.company_label.setObjectName("ResearchPreviewCompany")
        self.company_label.setWordWrap(True)

        self.rating_label = QLabel("")
        self.rating_label.setObjectName("ResearchPreviewSignal")
        self.rating_label.setMinimumHeight(24)
        rating_font = self.rating_label.font()
        rating_font.setBold(True)
        self.rating_label.setFont(rating_font)
        self.signal_label = self.rating_label

        header_layout.addWidget(self.ticker_label)
        header_layout.addWidget(self.company_label)
        header_layout.addWidget(self.rating_label)

        summary_section = self.create_section("Score Summary")
        summary_layout = summary_section.layout()
        summary_layout.setContentsMargins(8, 8, 8, 8)
        summary_layout.setSpacing(5)

        self.summary_labels = {}
        for key, label in self.SUMMARY_FIELDS:
            self.summary_labels[key] = self.create_value_row(summary_layout, label)

        self.overall_score_label = self.summary_labels["overall"]
        self.score_labels = {}
        for key, label in self.SCORE_FIELDS:
            self.score_labels[key] = self.create_value_row(summary_layout, label)

        checklist_section = self.create_section("Institutional Checklist")
        checklist_layout = checklist_section.layout()
        checklist_layout.setContentsMargins(8, 8, 8, 8)
        checklist_layout.setSpacing(4)

        self.checklist_rows = {}
        self.checklist_name_labels = {}
        self.checklist_status_labels = {}
        for key, label, _check_name in self.CHECKLIST_ITEMS:
            self.checklist_status_labels[key] = self.create_checklist_row(
                checklist_layout,
                key,
                label,
            )

        self.checklist_unavailable_label = QLabel("Checklist unavailable.")
        self.checklist_unavailable_label.setObjectName("ResearchPreviewWarnings")
        self.checklist_unavailable_label.setWordWrap(True)
        checklist_layout.addWidget(self.checklist_unavailable_label)

        thesis_section = self.create_section("Trade Thesis")
        thesis_layout = thesis_section.layout()
        thesis_layout.setContentsMargins(8, 8, 8, 8)
        thesis_layout.setSpacing(4)

        self.thesis_title_label = QLabel("Trade thesis unavailable.")
        self.thesis_title_label.setObjectName("ResearchPreviewFieldValue")
        self.thesis_title_label.setWordWrap(True)
        thesis_layout.addWidget(self.thesis_title_label)

        self.thesis_label = QLabel("No trade thesis available.")
        self.thesis_label.setObjectName("ResearchPreviewThesis")
        self.thesis_label.setWordWrap(True)
        self.thesis_label.setMinimumHeight(42)
        thesis_layout.addWidget(self.thesis_label)

        self.strengths_label = QLabel("Strengths unavailable.")
        self.strengths_label.setObjectName("ResearchPreviewWarnings")
        self.strengths_label.setWordWrap(True)
        thesis_layout.addWidget(self.strengths_label)

        self.risks_label = QLabel("Risks unavailable.")
        self.risks_label.setObjectName("ResearchPreviewWarnings")
        self.risks_label.setWordWrap(True)
        thesis_layout.addWidget(self.risks_label)

        self.warning_title_label = QLabel("Warnings")
        self.warning_title_label.setObjectName("ResearchPreviewSectionTitle")
        self.warning_label = QLabel("No warnings")
        self.warning_label.setObjectName("ResearchPreviewWarnings")
        self.warning_label.setWordWrap(True)

        self.timestamp_label = QLabel("")
        self.timestamp_label.setObjectName("ResearchPreviewTimestamp")
        self.timestamp_label.setAlignment(Qt.AlignLeft)
        self.timestamp_label.setWordWrap(True)

        self.score_rows = {}
        self.summary_separator = self.create_separator()
        self.time_separator = self.create_separator()
        self.warning_separator = self.create_separator()

        dashboard_layout.addWidget(header_section)
        dashboard_layout.addWidget(summary_section)
        dashboard_layout.addWidget(checklist_section)
        dashboard_layout.addWidget(thesis_section)
        dashboard_layout.addWidget(self.warning_title_label)
        dashboard_layout.addWidget(self.warning_label)
        dashboard_layout.addWidget(self.timestamp_label)

        group_layout.addWidget(self.empty_state_label)
        group_layout.addWidget(self.dashboard_frame)
        group_layout.addStretch()

        self.group.setLayout(group_layout)
        layout.addWidget(self.group)

        self.clear()

    def clear(self):
        """
        Clear every dashboard section.
        """

        self.empty_state_label.show()
        self.dashboard_frame.hide()
        self.ticker_label.hide()
        self.company_label.hide()
        self.rating_label.hide()
        self.overall_score_label.hide()
        self.timestamp_label.hide()
        self.warning_title_label.hide()
        self.warning_label.hide()

        self.ticker_label.setText("")
        self.company_label.setText("")
        self.rating_label.setText("")
        self.timestamp_label.setText("")

        for label in self.summary_labels.values():
            label.setText("-")
        for label in self.score_labels.values():
            label.setText("-")

        self.set_checklist_unavailable()
        self.set_trade_thesis(None)
        self.warning_label.setText("No warnings")

    def set_candidate(self, candidate_score):
        """
        Display a CandidateScore object.
        """

        if candidate_score is None:
            self.clear()
            return

        opportunity = candidate_score.opportunity_rating
        checklist = candidate_score.institutional_checklist
        thesis = candidate_score.trade_thesis

        self.empty_state_label.hide()
        self.dashboard_frame.show()
        self.ticker_label.show()
        self.company_label.setVisible(
            bool(self.company_name_for_candidate(candidate_score))
        )
        self.rating_label.show()
        self.overall_score_label.show()
        self.timestamp_label.show()
        self.warning_title_label.show()
        self.warning_label.show()

        self.ticker_label.setText(candidate_score.ticker)
        self.company_label.setText(self.company_name_for_candidate(candidate_score))
        self.rating_label.setText(self.format_opportunity_header(opportunity))
        self.summary_labels["overall"].setText(
            self.format_score(candidate_score.primary_score_value)
        )
        self.summary_labels["opportunity"].setText(
            self.format_opportunity_summary(opportunity)
        )
        self.summary_labels["checklist"].setText(
            self.format_checklist_summary(checklist)
        )
        self.timestamp_label.setText(f"Analysis Time: {candidate_score.timestamp}")

        score_map = candidate_score.score_map
        for key, _label in self.SCORE_FIELDS:
            self.score_labels[key].setText(self.format_score(score_map.get(key)))

        self.set_checklist(checklist)
        self.set_trade_thesis(thesis)
        self.warning_label.setText(
            self.format_warnings(
                candidate_score,
                self.opportunity_warning_messages(opportunity)
                + self.checklist_warning_messages(checklist)
                + self.thesis_warning_messages(thesis),
            )
        )

    @staticmethod
    def trade_card_for_candidate(candidate_score):
        """
        Return the prepared trade card attached to a candidate, when present.
        """

        if candidate_score is None:
            return None

        if isinstance(candidate_score, dict):
            return candidate_score.get("trade_card")

        return getattr(candidate_score, "trade_card", None)

    def set_trade_thesis(self, thesis):
        """
        Display a generated trade thesis.
        """

        if thesis is None:
            self.thesis_title_label.setText("Trade thesis unavailable.")
            self.thesis_label.setText("No trade thesis available.")
            self.strengths_label.setText("Strengths unavailable.")
            self.risks_label.setText("Risks unavailable.")
            return

        if isinstance(thesis, str):
            cleaned = thesis.strip()
            self.thesis_title_label.setText("Trade thesis unavailable.")
            self.thesis_label.setText(cleaned or "No trade thesis available.")
            self.strengths_label.setText("Strengths unavailable.")
            self.risks_label.setText("Risks unavailable.")
            return

        self.thesis_title_label.setText(thesis.title or "Trade thesis unavailable.")
        self.thesis_label.setText(thesis.summary or "No trade thesis available.")
        self.strengths_label.setText(
            self.format_list("Strengths", thesis.strengths)
        )
        self.risks_label.setText(self.format_list("Risks", thesis.risks))

    def set_placeholder_checklist(self):
        """
        Backward-compatible alias for unavailable checklist state.
        """

        self.set_checklist_unavailable()

    def set_checklist_unavailable(self):
        for key, label, _check_name in self.CHECKLIST_ITEMS:
            self.checklist_name_labels[key].setText(label)
            self.update_checklist_status(key, "warning")
            self.checklist_rows[key].hide()

        self.checklist_unavailable_label.setText("Checklist unavailable.")
        self.checklist_unavailable_label.show()

    def set_checklist(self, checklist):
        """
        Display checklist statuses without rebuilding row widgets.
        """

        if checklist is None:
            self.set_checklist_unavailable()
            return

        checks_by_name = {
            check.name: check
            for check in checklist.checks
        }

        self.checklist_unavailable_label.hide()

        for key, label, check_name in self.CHECKLIST_ITEMS:
            check = checks_by_name.get(check_name)
            display_label = self.checklist_display_label(check.name) if check else label
            status = check.status if check else "warning"

            self.checklist_name_labels[key].setText(display_label)
            self.update_checklist_status(key, status)
            self.checklist_rows[key].show()

    def update_checklist_status(self, key, status):
        label = self.checklist_status_labels[key]
        normalized = status if status in {"pass", "warning", "fail"} else "warning"
        label.setText({
            "pass": "✓ Pass",
            "warning": "⚠ Warning",
            "fail": "✗ Fail",
        }[normalized])
        label.setProperty("status", normalized)
        label.style().unpolish(label)
        label.style().polish(label)

    def placeholder_checklist(self, metrics):
        """
        Deprecated placeholder helper retained for old direct tests.
        """

        return {
            key: "warning"
            for key, _label, _check_name in self.CHECKLIST_ITEMS
        }

    @staticmethod
    def status_for_metric(metric, value):
        if value is None:
            return "warning"

        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            return "warning"

        if metric == "earnings_risk_score":
            if numeric_value >= 70:
                return "fail"
            if numeric_value >= 50:
                return "warning"
            return "pass"

        if numeric_value >= 75:
            return "pass"
        if numeric_value >= 50:
            return "warning"
        return "fail"

    @staticmethod
    def checklist_completion(checklist):
        if checklist is None:
            return 0.0

        return checklist.overall_percentage

    @staticmethod
    def checklist_warning_messages(checklist):
        if checklist is None:
            return []

        return [
            check.message
            for check in checklist.checks
            if check.status in {"warning", "fail"}
        ]

    @staticmethod
    def opportunity_warning_messages(opportunity):
        if opportunity is None:
            return []

        return list(opportunity.warnings)

    @staticmethod
    def thesis_warning_messages(thesis):
        if thesis is None:
            return []

        return list(thesis.risks)

    @staticmethod
    def metrics_for_candidate(candidate_score):
        metrics = {
            name: score.value
            for name, score in candidate_score.score_map.items()
        }
        metrics.update(candidate_score.composite_intelligence_component_scores)
        metrics["composite_score"] = candidate_score.composite_score.value

        if candidate_score.institutional_bounce_score is not None:
            metrics["institutional_bounce_score"] = (
                candidate_score.institutional_bounce_score
            )

        return metrics

    @staticmethod
    def company_name_for_candidate(candidate_score):
        return (
            getattr(candidate_score, "company_name", "")
            or getattr(candidate_score, "company", "")
            or getattr(candidate_score, "name", "")
            or ""
        )

    @staticmethod
    def format_score(score):
        if score is None:
            return "-"

        if not hasattr(score, "value"):
            return f"{float(score):.1f}"

        return f"{score.value:.1f}"

    @staticmethod
    def format_percent(value):
        return f"{float(value):.0f}%"

    @classmethod
    def format_checklist_summary(cls, checklist):
        if checklist is None:
            return "Checklist unavailable."

        return f"{cls.format_percent(checklist.overall_percentage)} {checklist.overall_label}"

    @classmethod
    def format_opportunity_header(cls, opportunity):
        if opportunity is None:
            return "Opportunity rating unavailable."

        return cls.opportunity_label(opportunity.stars, opportunity.rating_label)

    @classmethod
    def format_opportunity_summary(cls, opportunity):
        if opportunity is None:
            return "Opportunity rating unavailable."

        return f"{cls.format_score(opportunity.rating_score)} {opportunity.rating_label}"

    @staticmethod
    def format_list(title, values):
        if not values:
            return f"{title}: None"

        return f"{title}: " + "; ".join(values)

    @staticmethod
    def checklist_display_label(name):
        labels = {
            "Near validated support": "Near Support",
            "Bounce success rate acceptable": "Bounce Validation",
            "Relative Strength strong": "Relative Strength",
            "Trend aligned": "Trend",
            "Institutional ownership acceptable": "Institutional Buying",
            "Institutional momentum positive": "Institutional Momentum",
            "Volume accumulation present": "Volume",
            "Earnings window safe": "Earnings Window",
            "ATR risk acceptable": "ATR Risk",
            "Opportunity rating acceptable": "Opportunity Rating",
        }
        return labels.get(name, name)

    @staticmethod
    def opportunity_label(stars, label):
        return f"{'★' * stars}{'☆' * (5 - stars)} {label}"

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
    def format_warnings(candidate_score, extra_warnings=None):
        warnings = []

        for score in candidate_score.scores:
            warnings.extend(score.details.get("warnings", []))

            if score.error:
                warnings.append(score.error)

        warnings.extend(candidate_score.warnings)
        warnings.extend(extra_warnings or [])

        if not warnings:
            return "No warnings"

        deduped_warnings = []
        for warning in warnings:
            if warning not in deduped_warnings:
                deduped_warnings.append(warning)
        warnings = deduped_warnings

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
    def create_section(title=None):
        section = QFrame()
        section.setObjectName("ResearchPreviewSection")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if title:
            title_label = QLabel(title)
            title_label.setObjectName("ResearchPreviewSectionTitle")
            layout.addWidget(title_label)

        return section

    @staticmethod
    def create_value_row(parent_layout, label):
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        name_label = QLabel(label)
        name_label.setObjectName("ResearchPreviewFieldLabel")
        value_label = QLabel("-")
        value_label.setObjectName("ResearchPreviewFieldValue")
        value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        row_layout.addWidget(name_label, stretch=1)
        row_layout.addWidget(value_label)
        parent_layout.addWidget(row)

        return value_label

    def create_checklist_row(self, parent_layout, key, label):
        row = QWidget()
        row.setObjectName("ResearchPreviewChecklistRow")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        name_label = QLabel(label)
        name_label.setObjectName("ResearchPreviewFieldLabel")
        status_label = QLabel("WARN")
        status_label.setObjectName("ResearchPreviewChecklistStatus")
        status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        status_label.setMinimumWidth(86)

        row_layout.addWidget(name_label, stretch=1)
        row_layout.addWidget(status_label)
        parent_layout.addWidget(row)
        self.checklist_rows[key] = row
        self.checklist_name_labels[key] = name_label

        return status_label

    @staticmethod
    def create_separator():
        separator = QFrame()
        separator.setObjectName("ResearchPreviewSeparator")
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Plain)

        return separator
