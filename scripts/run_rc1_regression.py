from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class RegressionSection:
    name: str
    description: str
    pytest_args: list[str]


@dataclass(frozen=True)
class RegressionSectionResult:
    name: str
    passed: bool
    returncode: int
    command: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RegressionRunResult:
    passed: bool
    section_results: list[RegressionSectionResult] = field(default_factory=list)


def build_rc1_sections() -> list[RegressionSection]:
    return [
        RegressionSection(
            name="startup",
            description="Application startup and main-window smoke coverage",
            pytest_args=["tests/test_rc1_smoke_startup.py"],
        ),
        RegressionSection(
            name="smoke",
            description="RC1 screening, export, and UI smoke tests",
            pytest_args=[
                "tests/test_rc1_smoke_screening.py",
                "tests/test_rc1_smoke_export.py",
                "tests/test_rc1_smoke_ui.py",
            ],
        ),
        RegressionSection(
            name="architecture_audit",
            description="Repository architecture audit",
            pytest_args=["tests/test_repository_architecture_audit.py"],
        ),
        RegressionSection(
            name="production_readiness",
            description="Production readiness dashboard and release diagnostics",
            pytest_args=[
                "tests/test_production_readiness.py",
                "tests/test_production_readiness_dashboard_service.py",
                "tests/test_release_candidate_validation_service.py",
            ],
        ),
        RegressionSection(
            name="provider_validation",
            description="Provider configuration, health, failover, and resilience checks",
            pytest_args=[
                "tests/test_provider_configuration_validation_service.py",
                "tests/test_provider_configuration_panel.py",
                "tests/test_provider_health_panel.py",
                "tests/test_provider_failover_event_service.py",
                "tests/test_provider_failover_history_panel.py",
                "tests/test_live_provider_resilience_service.py",
            ],
        ),
        RegressionSection(
            name="calibration",
            description="Model calibration services, UI, validation, and integration audit",
            pytest_args=[
                "tests/test_model_calibration_persistence.py",
                "tests/test_model_calibration_service.py",
                "tests/test_model_calibration_panel.py",
                "tests/test_model_calibration_controller.py",
                "tests/test_model_calibration_history_service.py",
                "tests/test_model_calibration_history_panel.py",
                "tests/test_model_calibration_trend_service.py",
                "tests/test_model_calibration_trend_panel.py",
                "tests/test_model_calibration_comparison_service.py",
                "tests/test_model_calibration_comparison_panel.py",
                "tests/test_model_calibration_apply_service.py",
                "tests/test_model_calibration_validation_service.py",
                "tests/test_model_calibration_integration_audit_service.py",
            ],
        ),
        RegressionSection(
            name="export",
            description="Results, beta, signal quality, and end-to-end export workflows",
            pytest_args=[
                "tests/test_export_service.py",
                "tests/test_export_controller.py",
                "tests/test_results_export_service.py",
                "tests/test_beta_report_export_service.py",
                "tests/test_signal_quality_export.py",
                "tests/test_end_to_end_export_workflow.py",
            ],
        ),
        RegressionSection(
            name="packaging",
            description="RC1 release freeze and packaging verification",
            pytest_args=[
                "tests/test_release_freeze_checklist.py",
                "tests/test_rc1_packaging_verification.py",
            ],
        ),
        RegressionSection(
            name="clean_install",
            description="Clean Windows install readiness validation",
            pytest_args=["tests/test_clean_install_readiness.py"],
        ),
    ]


def run_section(section, python_executable=None, project_root=None):
    python = python_executable or sys.executable
    root = Path(project_root or PROJECT_ROOT)
    command = [python, "-m", "pytest", *section.pytest_args, "-q"]
    completed = subprocess.run(command, cwd=root)
    return RegressionSectionResult(
        name=section.name,
        passed=completed.returncode == 0,
        returncode=completed.returncode,
        command=command,
    )


def run_rc1_regression(
    sections=None,
    python_executable=None,
    project_root=None,
    stop_on_failure=False,
):
    results = []
    for section in sections or build_rc1_sections():
        print(f"\n=== RC1 Regression: {section.name} ===")
        print(section.description)
        result = run_section(
            section,
            python_executable=python_executable,
            project_root=project_root,
        )
        results.append(result)
        print(f"{section.name}: {'PASS' if result.passed else 'FAIL'}")
        if stop_on_failure and not result.passed:
            break
    return RegressionRunResult(
        passed=all(result.passed for result in results),
        section_results=results,
    )


def format_summary(result):
    lines = [
        "",
        "RC1 Full Regression Summary",
        f"Overall: {'PASS' if result.passed else 'FAIL'}",
    ]
    for section in result.section_results:
        lines.append(
            f"- {section.name}: {'PASS' if section.passed else 'FAIL'} "
            f"(exit {section.returncode})"
        )
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run the ordered RC1 regression checks.")
    parser.add_argument(
        "--project-root",
        default=None,
        help="Project root to run from. Defaults to the repository root.",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable used to invoke pytest.",
    )
    parser.add_argument(
        "--stop-on-failure",
        action="store_true",
        help="Stop after the first failed section.",
    )
    args = parser.parse_args(argv)
    result = run_rc1_regression(
        python_executable=args.python,
        project_root=args.project_root,
        stop_on_failure=args.stop_on_failure,
    )
    print(format_summary(result))
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
