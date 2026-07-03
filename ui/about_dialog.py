from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from controllers.diagnostics_controller import DiagnosticsController
from services.app_config_service import AppConfigService
from services.beta_validation_service import BetaValidationService
from services.database_backup_service import DatabaseBackupService
from services.release_checklist_service import ReleaseChecklistService
from services.release_metadata_service import ReleaseMetadataService


class AboutDialog(QDialog):
    """
    Modal About and Diagnostics dialog.
    """

    DESCRIPTION = (
        "Local-first institutional bounce research workstation for screening, "
        "trade planning, portfolio diagnostics, and provider-backed market data."
    )

    def __init__(
        self,
        controller: DiagnosticsController | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.controller = controller or DiagnosticsController()
        self.config_service = AppConfigService()
        self.release_metadata_service = ReleaseMetadataService()
        self.release_checklist_service = ReleaseChecklistService()
        self.beta_validation_service = BetaValidationService()

        self.setWindowTitle("About & Diagnostics")
        self.setModal(True)
        self.resize(620, 520)

        self.app_name_label = QLabel("--")
        self.app_name_label.setObjectName("AboutDialogTitle")
        self.version_label = QLabel("--")
        self.description_label = QLabel(self.DESCRIPTION)
        self.description_label.setWordWrap(True)

        self.diagnostics_group = QGroupBox("Diagnostics")
        self.diagnostics_layout = QFormLayout(self.diagnostics_group)
        self.diagnostic_labels: dict[str, QLabel] = {}

        self.diagnostics_text = QTextEdit()
        self.diagnostics_text.setReadOnly(True)
        self.diagnostics_text.setMinimumHeight(150)
        self.release_group = QGroupBox("Release Readiness")
        self.release_layout = QFormLayout(self.release_group)
        self.release_labels: dict[str, QLabel] = {}
        for key, label_text in [
            ("version", "Version"),
            ("build_timestamp", "Build Timestamp"),
            ("release_channel", "Release Channel"),
            ("environment", "Environment"),
            ("checklist", "Checklist"),
            ("beta_validation", "Beta Validation"),
            ("beta_report", "Beta Report"),
        ]:
            label = QLabel("--")
            label.setWordWrap(True)
            self.release_layout.addRow(label_text, label)
            self.release_labels[key] = label
        self.backup_database_button = QPushButton("Backup Database")
        self.backup_database_button.clicked.connect(self.backup_database)
        self.restore_database_button = QPushButton("Restore Database")
        self.restore_database_button.clicked.connect(self.restore_database)
        self.run_beta_validation_button = QPushButton("Run Beta Validation")
        self.run_beta_validation_button.clicked.connect(self.run_beta_validation)

        self.copy_button = QPushButton("Copy Diagnostics")
        self.copy_button.clicked.connect(self.copy_diagnostics)
        self.refresh_button = QPushButton("Refresh Diagnostics")
        self.refresh_button.clicked.connect(self.load_diagnostics)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.button_box.rejected.connect(self.reject)

        outer_layout = QVBoxLayout(self)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.addWidget(self.app_name_label)
        layout.addWidget(self.version_label)
        layout.addWidget(self.description_label)
        layout.addWidget(self.diagnostics_group)
        layout.addWidget(self.release_group)
        layout.addWidget(self.diagnostics_text)
        layout.addWidget(self.backup_database_button)
        layout.addWidget(self.restore_database_button)
        layout.addWidget(self.run_beta_validation_button)
        layout.addWidget(self.refresh_button)
        layout.addWidget(self.copy_button)
        self.scroll_area.setWidget(content)
        outer_layout.addWidget(self.scroll_area)
        outer_layout.addWidget(self.button_box)

        self.load_diagnostics()

    def load_diagnostics(self) -> None:
        diagnostics = self.controller.get_diagnostics()
        self.app_name_label.setText(str(diagnostics.get("app_name") or "--"))
        self.version_label.setText(
            f"Version: {diagnostics.get('version') or '--'}"
            f" | Build: {diagnostics.get('build_date') or '--'}"
            f" | Schema: {diagnostics.get('schema_version') or '--'}"
        )
        self._render_diagnostics(diagnostics)
        self._render_release_readiness()
        self.diagnostics_text.setPlainText(self.full_diagnostics_text())

    def full_diagnostics_text(self) -> str:
        parts = [self.controller.diagnostics_text()]
        startup = self.controller.startup_report()
        health = self.controller.health_report()
        if startup is not None:
            parts.append(self.report_text("Startup Diagnostics", startup))
        if health is not None:
            parts.append(self.report_text("Health Check", health))
        return "\n\n".join(part for part in parts if part)

    def copy_diagnostics(self) -> None:
        QApplication.clipboard().setText(self.diagnostics_text.toPlainText())

    def _render_diagnostics(self, diagnostics: dict[str, Any]) -> None:
        labels = [
            ("python_version", "Python"),
            ("qt_version", "Qt/PySide"),
            ("build_date", "Build Date"),
            ("build_timestamp", "Build Timestamp"),
            ("release_channel", "Release Channel"),
            ("schema_version", "Schema Version"),
            ("operating_system", "Operating System"),
            ("active_provider", "Active Provider"),
            ("provider_config_path", "Provider Config"),
            ("database_path", "Database Path"),
            ("working_directory", "Working Directory"),
            ("log_path", "Log Path"),
            ("test_build_mode", "Test/Build Mode"),
            ("build_environment", "Build Environment"),
        ]

        for key, label_text in labels:
            label = self.diagnostic_labels.get(key)

            if label is None:
                label = QLabel("--")
                label.setTextInteractionFlags(label.textInteractionFlags())
                self.diagnostics_layout.addRow(label_text, label)
                self.diagnostic_labels[key] = label

            label.setText(str(diagnostics.get(key) or "--"))

    def _render_release_readiness(self) -> None:
        metadata = self.release_metadata_service.metadata()
        checklist = self.release_checklist_service.run(
            include_build_checks=False,
            include_test_checks=False,
        )
        self.release_labels["version"].setText(metadata.version)
        self.release_labels["build_timestamp"].setText(metadata.build_timestamp)
        self.release_labels["release_channel"].setText(metadata.release_channel)
        self.release_labels["environment"].setText(
            self.release_metadata_service.build_environment_summary()["platform"]
        )
        self.release_labels["checklist"].setText(checklist.summary)
        self.release_labels["beta_validation"].setText("Not run")
        self.release_labels["beta_report"].setText("--")

    def backup_database(self):
        config = self.config_service.load()
        result = DatabaseBackupService(
            config.database_path,
            config.data_directory / "backups",
        ).backup()
        self.release_labels["checklist"].setText(result.message)
        return result

    def restore_database(self):
        config = self.config_service.load()
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Restore Database Backup",
            str(config.data_directory / "backups"),
            "SQLite Database (*.db);;All Files (*)",
        )
        if not path:
            self.release_labels["checklist"].setText("Restore cancelled")
            return None
        answer = QMessageBox.question(
            self,
            "Restore Database",
            "Restore the database from this backup?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            self.release_labels["checklist"].setText("Restore cancelled")
            return None
        result = DatabaseBackupService(
            config.database_path,
            config.data_directory / "backups",
        ).restore(path)
        self.release_labels["checklist"].setText(result.message)
        return result

    def run_beta_validation(self):
        self.run_beta_validation_button.setEnabled(False)
        self.release_labels["beta_validation"].setText("Running beta validation...")
        try:
            report = self.beta_validation_service.run()
            export = self.beta_validation_service.export_report(report)
            self.release_labels["beta_validation"].setText(report.summary)
            self.release_labels["beta_report"].setText(export.get("json_path") or "--")
            return report
        except Exception as exc:
            self.release_labels["beta_validation"].setText(
                f"Beta validation failed: {exc}"
            )
            self.release_labels["beta_report"].setText("--")
            return None
        finally:
            self.run_beta_validation_button.setEnabled(True)

    @staticmethod
    def report_text(title, report) -> str:
        lines = [f"{title}: {getattr(report, 'status', '--')}"]
        for check in getattr(report, "checks", []) or []:
            lines.append(
                f"- {getattr(check, 'name', '--')}: "
                f"{getattr(check, 'status', '--')} - "
                f"{getattr(check, 'message', '--')}"
            )
        warnings = getattr(report, "warnings", []) or []
        errors = getattr(report, "errors", []) or []
        if warnings:
            lines.append("Warnings: " + "; ".join(str(item) for item in warnings))
        if errors:
            lines.append("Errors: " + "; ".join(str(item) for item in errors))
        return "\n".join(lines)
