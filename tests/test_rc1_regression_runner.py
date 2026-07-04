from pathlib import Path

from scripts.run_rc1_regression import (
    RegressionSection,
    build_rc1_sections,
    format_summary,
    main,
    run_rc1_regression,
)


class Completed:
    def __init__(self, returncode):
        self.returncode = returncode


def test_rc1_regression_sections_cover_required_release_areas():
    sections = build_rc1_sections()
    names = [section.name for section in sections]

    assert names == [
        "startup",
        "smoke",
        "architecture_audit",
        "production_readiness",
        "provider_validation",
        "calibration",
        "export",
        "packaging",
        "clean_install",
    ]
    all_args = " ".join(arg for section in sections for arg in section.pytest_args)
    assert "test_rc1_smoke_startup.py" in all_args
    assert "test_repository_architecture_audit.py" in all_args
    assert "test_production_readiness_dashboard_service.py" in all_args
    assert "test_provider_configuration_validation_service.py" in all_args
    assert "test_model_calibration_validation_service.py" in all_args
    assert "test_end_to_end_export_workflow.py" in all_args
    assert "test_rc1_packaging_verification.py" in all_args
    assert "test_clean_install_readiness.py" in all_args


def test_rc1_regression_runner_runs_sections_in_order(monkeypatch, tmp_path):
    calls = []

    def fake_run(command, cwd):
        calls.append((command, cwd))
        return Completed(0)

    monkeypatch.setattr("scripts.run_rc1_regression.subprocess.run", fake_run)
    sections = [
        RegressionSection("first", "First section", ["tests/test_first.py"]),
        RegressionSection("second", "Second section", ["tests/test_second.py"]),
    ]

    result = run_rc1_regression(sections=sections, python_executable="python", project_root=tmp_path)

    assert result.passed is True
    assert [section.name for section in result.section_results] == ["first", "second"]
    assert calls[0][0] == ["python", "-m", "pytest", "tests/test_first.py", "-q"]
    assert calls[1][0] == ["python", "-m", "pytest", "tests/test_second.py", "-q"]
    assert calls[0][1] == tmp_path


def test_rc1_regression_runner_reports_failure_and_nonzero_exit(monkeypatch, tmp_path):
    returncodes = [0, 1, 0]

    def fake_run(command, cwd):
        return Completed(returncodes.pop(0))

    monkeypatch.setattr("scripts.run_rc1_regression.subprocess.run", fake_run)
    sections = [
        RegressionSection("startup", "Startup", ["tests/test_startup.py"]),
        RegressionSection("smoke", "Smoke", ["tests/test_smoke.py"]),
        RegressionSection("export", "Export", ["tests/test_export.py"]),
    ]

    result = run_rc1_regression(sections=sections, python_executable="python", project_root=tmp_path)
    summary = format_summary(result)

    assert result.passed is False
    assert [section.passed for section in result.section_results] == [True, False, True]
    assert "Overall: FAIL" in summary
    assert "- smoke: FAIL (exit 1)" in summary


def test_rc1_regression_runner_stop_on_failure(monkeypatch, tmp_path):
    calls = []

    def fake_run(command, cwd):
        calls.append(command)
        return Completed(1)

    monkeypatch.setattr("scripts.run_rc1_regression.subprocess.run", fake_run)
    sections = [
        RegressionSection("startup", "Startup", ["tests/test_startup.py"]),
        RegressionSection("smoke", "Smoke", ["tests/test_smoke.py"]),
    ]

    result = run_rc1_regression(
        sections=sections,
        python_executable="python",
        project_root=tmp_path,
        stop_on_failure=True,
    )

    assert result.passed is False
    assert len(result.section_results) == 1
    assert len(calls) == 1


def test_rc1_regression_runner_cli_exit_codes(monkeypatch, tmp_path, capsys):
    def passing_run(command, cwd):
        return Completed(0)

    monkeypatch.setattr("scripts.run_rc1_regression.subprocess.run", passing_run)
    assert main(["--project-root", str(tmp_path), "--python", "python"]) == 0
    output = capsys.readouterr().out
    assert "RC1 Full Regression Summary" in output
    assert "Overall: PASS" in output

    def failing_run(command, cwd):
        return Completed(1)

    monkeypatch.setattr("scripts.run_rc1_regression.subprocess.run", failing_run)
    assert main(["--project-root", str(tmp_path), "--python", "python", "--stop-on-failure"]) == 1
    output = capsys.readouterr().out
    assert "Overall: FAIL" in output


def test_rc1_full_regression_documentation_is_linked():
    root = Path(__file__).resolve().parents[1]
    checklist = (root / "docs" / "rc1_full_regression_checklist.md").read_text(
        encoding="utf-8"
    )
    freeze = (root / "docs" / "rc1_release_freeze_checklist.md").read_text(
        encoding="utf-8"
    )
    readme = (root / "README.md").read_text(encoding="utf-8")

    assert "scripts\\run_rc1_regression.py" in checklist
    assert "Startup" in checklist
    assert "Provider Validation" in checklist
    assert "Clean Install" in checklist
    assert "docs/rc1_full_regression_checklist.md" in freeze
    assert "scripts/run_rc1_regression.py" in readme
