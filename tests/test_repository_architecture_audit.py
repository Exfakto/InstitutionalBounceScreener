from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE_UI_IMPORT_EXCEPTIONS = {
    Path("services/diagnostics_service.py"),
    Path("services/exception_handler.py"),
}
CONTROLLER_UI_IMPORT_EXCEPTIONS = {
    Path("controllers/application_controller.py"),
}
MAJOR_SERVICES = {
    "screening_orchestrator": "test_screening_orchestrator.py",
    "candidate_ranking_engine": "test_candidate_ranking_engine.py",
    "bounce_composite_scoring_engine": "test_bounce_composite_scoring_engine.py",
    "technical_indicator_engine": "test_technical_indicator_engine.py",
    "support_zone_engine": "test_support_zone_engine.py",
    "bounce_detection_engine": "test_bounce_detection_engine.py",
    "institutional_intelligence_engine": "test_institutional_intelligence_engine.py",
    "market_data_service": "test_market_data_service.py",
    "live_provider_resilience_service": "test_live_provider_resilience_service.py",
    "provider_configuration_validation_service": "test_provider_configuration_validation_service.py",
    "provider_failover_event_service": "test_provider_failover_event_service.py",
    "results_export_service": "test_results_export_service.py",
    "model_calibration_service": "test_model_calibration_service.py",
    "production_readiness_dashboard_service": "test_production_readiness_dashboard_service.py",
    "release_candidate_validation_service": "test_release_candidate_validation_service.py",
}
MAJOR_CONTROLLERS = {
    "market_data_controller": "test_market_data_controller.py",
    "diagnostics_controller": "test_diagnostics_controller.py",
    "model_calibration_controller": "test_model_calibration_controller.py",
    "results_export_controller": "test_end_to_end_export_workflow.py",
    "export_controller": "test_export_controller.py",
    "screening_controller": "test_full_universe_validation_service.py",
    "chart_controller": "test_chart_controller.py",
    "dashboard_controller": "test_dashboard_controller.py",
    "trade_journal_controller": "test_trade_journal_controller.py",
    "watchlist_controller": "test_watchlist_controller.py",
}


def python_files(*parts):
    base = ROOT.joinpath(*parts)
    return [
        path
        for path in base.rglob("*.py")
        if "__pycache__" not in path.parts
    ]


def imports_for(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


def relative(path):
    return path.relative_to(ROOT)


def imports_module(path, prefixes):
    return [
        name
        for name in imports_for(path)
        if any(name == prefix or name.startswith(prefix + ".") for prefix in prefixes)
    ]


def test_services_and_database_do_not_import_ui_except_documented_boundaries():
    violations = {}
    for path in [*python_files("services"), *python_files("database")]:
        rel = relative(path)
        if rel in SERVICE_UI_IMPORT_EXCEPTIONS:
            continue
        matches = imports_module(path, {"ui", "PySide6"})
        if matches:
            violations[str(rel)] = matches

    assert violations == {}


def test_controllers_do_not_import_ui_except_application_shell_boundary():
    violations = {}
    for path in python_files("controllers"):
        rel = relative(path)
        if rel in CONTROLLER_UI_IMPORT_EXCEPTIONS:
            continue
        matches = imports_module(path, {"ui", "PySide6"})
        if matches:
            violations[str(rel)] = matches

    assert violations == {}


def test_ui_does_not_import_database_layer_directly():
    violations = {}
    for path in python_files("ui"):
        matches = imports_module(path, {"database"})
        if matches:
            violations[str(relative(path))] = matches

    assert violations == {}


def test_major_services_have_corresponding_tests():
    test_files = {path.name for path in python_files("tests")}
    missing = {
        service: expected_test
        for service, expected_test in MAJOR_SERVICES.items()
        if expected_test not in test_files
    }

    assert missing == {}


def test_major_controllers_have_corresponding_tests():
    test_files = {path.name for path in python_files("tests")}
    missing = {
        controller: expected_test
        for controller, expected_test in MAJOR_CONTROLLERS.items()
        if expected_test not in test_files
    }

    assert missing == {}


def test_repository_has_no_duplicate_service_module_names():
    names = [path.stem for path in python_files("services")]
    duplicates = sorted({name for name in names if names.count(name) > 1})

    assert duplicates == []


def test_release_critical_filenames_match_repository_manifest():
    required_files = [
        "ui/widgets/dashboard.py",
        "ui/widgets/screening_results_panel.py",
        "ui/widgets/provider_health_panel.py",
        "ui/widgets/provider_configuration_panel.py",
        "ui/widgets/provider_failover_history_panel.py",
        "ui/widgets/production_readiness_panel.py",
        "controllers/market_data_controller.py",
        "controllers/diagnostics_controller.py",
        "controllers/model_calibration_controller.py",
        "controllers/results_export_controller.py",
        "services/live_provider_resilience_service.py",
        "services/provider_configuration_validation_service.py",
        "services/provider_failover_event_service.py",
        "services/production_readiness_dashboard_service.py",
        "services/release_candidate_validation_service.py",
        "docs/repository_architecture_audit.md",
        "docs/end_to_end_validation.md",
        "docs/release_candidate_validation.md",
    ]
    missing = [path for path in required_files if not (ROOT / path).exists()]

    assert missing == []


def test_deprecated_or_compatibility_modules_are_documented():
    documented = (ROOT / "docs" / "repository_architecture_audit.md").read_text(
        encoding="utf-8"
    )
    for phrase in [
        "Compatibility and Legacy Modules",
        "`main.py`",
        "`services/exception_handler.py`",
        "`services/diagnostics_service.py`",
        "`controllers/application_controller.py`",
    ]:
        assert phrase in documented


def test_architecture_documentation_mentions_current_release_layers():
    required_docs = [
        ROOT / "docs" / "repository_architecture_audit.md",
        ROOT / "docs" / "PROJECT_MANIFEST.md",
        ROOT / "docs" / "CODEX_INSTRUCTIONS.md",
        ROOT / "README.md",
    ]
    for path in required_docs:
        assert path.exists(), f"Missing architecture document: {path}"

    combined = "\n".join(path.read_text(encoding="utf-8") for path in required_docs)
    for phrase in [
        "Repository -> Services -> Controllers -> UI",
        "Provider resilience",
        "Model calibration",
        "Release Candidate Validation",
        "v2.0",
        "dashboard.py",
    ]:
        assert phrase in combined
