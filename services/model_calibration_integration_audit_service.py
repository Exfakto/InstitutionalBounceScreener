from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CalibrationIntegrationAuditItem:
    component_name: str
    status: str
    issue_description: str = ""
    recommended_fix: str = ""


@dataclass(frozen=True)
class CalibrationIntegrationAuditResult:
    items: list[CalibrationIntegrationAuditItem] = field(default_factory=list)

    @property
    def status(self):
        statuses = {item.status for item in self.items}
        if "Fail" in statuses:
            return "Fail"
        if "Warning" in statuses:
            return "Warning"
        return "Pass"


class ModelCalibrationIntegrationAuditService:
    """Verify model calibration wiring without changing calibration behavior."""

    REPOSITORY_METHODS = {
        "Persistence": (
            "save_calibration_run",
            "save_calibration_recommendations",
            "fetch_latest_calibration_run",
            "fetch_calibration_recommendations",
            "fetch_calibration_run_history",
            "fetch_calibration_run",
            "clear_calibration_run",
        ),
        "Recommendations": (
            "fetch_latest_calibration_run",
            "fetch_calibration_recommendations",
        ),
        "History": ("fetch_calibration_run_history", "fetch_calibration_run"),
    }
    CONTROLLER_METHODS = {
        "Recommendations": ("get_calibration_recommendations",),
        "History": ("get_calibration_history", "get_calibration_run_details"),
        "Trend Visualization": ("get_calibration_trend",),
        "Version Comparison": ("compare_calibration_runs",),
        "Apply Recommendations": ("apply_calibration_recommendations",),
        "Automated Validation": ("validate_calibration_changes",),
    }
    CONTROLLER_ATTRIBUTES = {
        "Recommendations": ("recommendation_service",),
        "History": ("history_service",),
        "Trend Visualization": ("trend_service",),
        "Version Comparison": ("comparison_service",),
        "Apply Recommendations": ("apply_service",),
        "Automated Validation": ("validation_service",),
    }
    OPTIONAL_COMPONENTS = {
        "Analysis": ("analysis_service", "calibration_service"),
        "Recommendation Export": ("export_service", "beta_report_export_service"),
    }

    def audit(self, controller=None, repository=None):
        items = []
        items.extend(self.audit_repository(repository))
        items.extend(self.audit_controller(controller))
        items.extend(self.audit_optional(controller))
        return CalibrationIntegrationAuditResult(items=items)

    def audit_repository(self, repository):
        items = []
        for component, methods in self.REPOSITORY_METHODS.items():
            missing = missing_methods(repository, methods)
            if missing:
                items.append(
                    CalibrationIntegrationAuditItem(
                        component_name=component,
                        status="Fail",
                        issue_description=f"Missing persistence methods: {', '.join(missing)}",
                        recommended_fix="Wire the calibration repository/database manager with the required persistence methods.",
                    )
                )
            else:
                items.append(
                    CalibrationIntegrationAuditItem(
                        component_name=component,
                        status="Pass",
                        issue_description="Persistence methods are available.",
                        recommended_fix="No action required.",
                    )
                )
        return items

    def audit_controller(self, controller):
        items = []
        for component, methods in self.CONTROLLER_METHODS.items():
            missing = missing_methods(controller, methods)
            missing_attrs = missing_attributes(
                controller,
                self.CONTROLLER_ATTRIBUTES.get(component, ()),
            )
            if missing or missing_attrs:
                issues = []
                if missing:
                    issues.append(f"missing methods: {', '.join(missing)}")
                if missing_attrs:
                    issues.append(f"missing dependencies: {', '.join(missing_attrs)}")
                items.append(
                    CalibrationIntegrationAuditItem(
                        component_name=component,
                        status="Fail",
                        issue_description="; ".join(issues),
                        recommended_fix="Inject and expose the calibration component through ModelCalibrationController.",
                    )
                )
            else:
                items.append(
                    CalibrationIntegrationAuditItem(
                        component_name=component,
                        status="Pass",
                        issue_description="Controller wiring is available.",
                        recommended_fix="No action required.",
                    )
                )
        return items

    def audit_optional(self, controller):
        items = []
        for component, attrs in self.OPTIONAL_COMPONENTS.items():
            if any(getattr(controller, attr, None) is not None for attr in attrs):
                items.append(
                    CalibrationIntegrationAuditItem(
                        component_name=component,
                        status="Pass",
                        issue_description="Optional component dependency is available.",
                        recommended_fix="No action required.",
                    )
                )
            else:
                items.append(
                    CalibrationIntegrationAuditItem(
                        component_name=component,
                        status="Warning",
                        issue_description="No dedicated dependency is attached to the controller.",
                        recommended_fix="Attach the service when this workflow is exposed through the controller.",
                    )
                )
        return items


def missing_methods(source, methods):
    if source is None:
        return list(methods)
    return [method for method in methods if not callable(getattr(source, method, None))]


def missing_attributes(source, attributes):
    if source is None:
        return list(attributes)
    return [attribute for attribute in attributes if getattr(source, attribute, None) is None]
