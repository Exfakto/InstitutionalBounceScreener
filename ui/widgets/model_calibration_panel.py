from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.design_system import DashboardDesignSystem as DesignSystem


class ModelCalibrationPanel(QWidget):
    HEADERS = [
        "Recommendation",
        "Severity",
        "Recommended Action",
        "Reason",
        "Related Metric",
        "Timestamp",
    ]

    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.current_recommendations = []
        self.setObjectName("ModelCalibrationPanel")
        self._build_ui()
        self.set_recommendations([])

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            DesignSystem.Spacing.MD,
            DesignSystem.Spacing.MD,
            DesignSystem.Spacing.MD,
            DesignSystem.Spacing.MD,
        )
        layout.setSpacing(DesignSystem.Spacing.SM)

        section = QFrame()
        section.setObjectName("ResearchPreviewSection")
        section.setStyleSheet(DesignSystem.card_style())
        layout.addWidget(section)

        section_layout = QVBoxLayout(section)
        section_layout.setContentsMargins(
            DesignSystem.Spacing.MD,
            DesignSystem.Spacing.MD,
            DesignSystem.Spacing.MD,
            DesignSystem.Spacing.MD,
        )
        section_layout.setSpacing(DesignSystem.Spacing.SM)

        header_layout = QHBoxLayout()
        self.title_label = QLabel("Calibration Recommendations")
        self.title_label.setObjectName("ResearchPreviewSectionTitle")
        self.apply_button = QPushButton("Apply Recommendations")
        self.apply_button.setObjectName("SecondaryButton")
        self.apply_button.clicked.connect(self.apply_current_recommendations)
        self.validate_button = QPushButton("Validate Changes")
        self.validate_button.setObjectName("SecondaryButton")
        self.validate_button.clicked.connect(self.validate_current_changes)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch(1)
        header_layout.addWidget(self.validate_button)
        header_layout.addWidget(self.apply_button)
        section_layout.addLayout(header_layout)

        self.apply_result_label = QLabel("")
        self.apply_result_label.setObjectName("ResearchPreviewFieldValue")
        self.apply_result_label.setWordWrap(True)
        section_layout.addWidget(self.apply_result_label)
        self.validation_result_label = QLabel("")
        self.validation_result_label.setObjectName("ResearchPreviewFieldValue")
        self.validation_result_label.setWordWrap(True)
        section_layout.addWidget(self.validation_result_label)

        self.message_label = QLabel("")
        self.message_label.setObjectName("EmptyStateLabel")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setWordWrap(True)
        section_layout.addWidget(self.message_label)

        self.recommendations_table = QTableWidget(0, len(self.HEADERS))
        self.recommendations_table.setObjectName("CalibrationRecommendationsTable")
        self.recommendations_table.setHorizontalHeaderLabels(self.HEADERS)
        self.recommendations_table.setAlternatingRowColors(True)
        self.recommendations_table.setSortingEnabled(False)
        self.recommendations_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.recommendations_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.recommendations_table.verticalHeader().setVisible(False)
        self.recommendations_table.setStyleSheet(DesignSystem.table_style())
        header = self.recommendations_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        section_layout.addWidget(self.recommendations_table)

    def refresh_recommendations(self):
        if self.controller is None:
            self.set_recommendations([])
            return []
        try:
            recommendations = self.controller.get_calibration_recommendations()
        except Exception:
            self.set_error("Unable to load calibration recommendations")
            return []
        self.set_recommendations(recommendations)
        return recommendations

    def set_recommendations(self, recommendations):
        recommendations = list(recommendations or [])
        self.current_recommendations = recommendations
        self.recommendations_table.setRowCount(0)
        self.message_label.setProperty("state", "empty")
        self.apply_button.setEnabled(bool(recommendations))
        self.validate_button.setEnabled(bool(recommendations))

        if not recommendations:
            self.message_label.setText("No calibration recommendations available")
            self.message_label.show()
            self.recommendations_table.hide()
            return

        self.message_label.clear()
        self.message_label.hide()
        self.recommendations_table.show()
        self.recommendations_table.setRowCount(len(recommendations))

        for row, recommendation in enumerate(recommendations):
            values = [
                self.value(recommendation, "title"),
                self.value(recommendation, "severity"),
                self.value(recommendation, "recommended_action"),
                self.value(recommendation, "reason"),
                self.value(recommendation, "related_metric"),
                self.value(recommendation, "timestamp"),
            ]
            for column, cell_value in enumerate(values):
                item = QTableWidgetItem(self.display_value(cell_value))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if column == 1:
                    item.setData(Qt.UserRole, self.display_value(cell_value))
                self.recommendations_table.setItem(row, column, item)
        self.recommendations_table.resizeRowsToContents()

    def apply_current_recommendations(self, confirmed=True):
        if self.controller is None:
            self.set_apply_result("Unable to apply calibration recommendations")
            return None
        try:
            result = self.controller.apply_calibration_recommendations(
                self.current_recommendations,
                confirmed=confirmed,
            )
        except Exception:
            self.set_apply_result("Unable to apply calibration recommendations")
            return None
        self.set_apply_result(self.value(result, "message") or self.value(result, "status"))
        return result

    def set_apply_result(self, message):
        self.apply_result_label.setText(message or "")

    def validate_current_changes(self, current_settings=None, proposed_settings=None):
        if self.controller is None:
            self.set_validation_result("Unable to validate calibration changes")
            return None
        try:
            result = self.controller.validate_calibration_changes(
                current_settings=current_settings or {},
                proposed_settings=proposed_settings or self.proposed_settings_from_recommendations(),
            )
        except Exception:
            self.set_validation_result("Unable to validate calibration changes")
            return None
        self.set_validation_result(
            self.value(result, "message") or self.value(result, "status")
        )
        return result

    def proposed_settings_from_recommendations(self):
        proposed = {}
        for recommendation in self.current_recommendations:
            metric = str(self.value(recommendation, "related_metric") or "")
            action = self.value(recommendation, "recommended_action")
            if metric:
                proposed[metric] = action
        return proposed

    def set_validation_result(self, message):
        self.validation_result_label.setText(message or "")

    def set_error(self, message):
        self.current_recommendations = []
        self.recommendations_table.setRowCount(0)
        self.recommendations_table.hide()
        self.apply_button.setEnabled(False)
        self.validate_button.setEnabled(False)
        self.message_label.setText(message or "Unable to load calibration recommendations")
        self.message_label.setProperty("state", "error")
        self.message_label.show()

    @staticmethod
    def value(source, key):
        if source is None:
            return None
        if isinstance(source, dict):
            return source.get(key)
        return getattr(source, key, None)

    @staticmethod
    def display_value(raw):
        if raw in (None, ""):
            return "N/A"
        return str(raw)
