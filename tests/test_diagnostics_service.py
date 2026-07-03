import json

from services.diagnostics_service import DiagnosticsService


def test_diagnostics_service_returns_expected_keys(tmp_path):
    provider_config_path = tmp_path / "providers.json"
    provider_config_path.write_text(
        json.dumps(
            {
                "active_provider": "local",
                "providers": {"local": {"enabled": True}},
            }
        ),
        encoding="utf-8",
    )
    service = DiagnosticsService(
        provider_config_path=provider_config_path,
        database_path=tmp_path / "InstitutionalBounce.db",
        log_path=tmp_path / "logs",
    )

    diagnostics = service.get_diagnostics()

    assert diagnostics["app_name"] == "Institutional Bounce Screener"
    assert diagnostics["version"] == "4.0.0"
    assert diagnostics["build_date"] == "2026-07-03"
    assert diagnostics["schema_version"] == "1"
    assert diagnostics["qt_version"]
    assert diagnostics["python_version"]
    assert diagnostics["operating_system"]
    assert diagnostics["active_provider"] == "local"
    assert diagnostics["provider_config_path"] == str(provider_config_path)
    assert diagnostics["database_path"].endswith("InstitutionalBounce.db")
    assert diagnostics["working_directory"]
    assert diagnostics["log_path"].endswith("logs")
    assert diagnostics["test_build_mode"] == "Unavailable"


def test_diagnostics_service_handles_missing_config_safely(tmp_path):
    service = DiagnosticsService(provider_config_path=tmp_path / "missing.json")

    diagnostics = service.get_diagnostics()

    assert diagnostics["active_provider"] == "local"
    assert diagnostics["provider_config_available"] is False
    assert diagnostics["warnings"]


def test_diagnostics_service_does_not_display_secrets(tmp_path, monkeypatch):
    monkeypatch.setenv("POLYGON_API_KEY", "very-secret")
    service = DiagnosticsService(provider_config_path=tmp_path / "missing.json")

    diagnostics = service.get_diagnostics()
    text = service.diagnostics_text()

    assert "very-secret" not in str(diagnostics)
    assert "very-secret" not in text


def test_diagnostics_text_is_readable(tmp_path):
    service = DiagnosticsService(provider_config_path=tmp_path / "missing.json")

    text = service.diagnostics_text()

    assert "Application: Institutional Bounce Screener" in text
    assert "Version: 4.0.0" in text
    assert "Schema Version: 1" in text
    assert "Active Provider: local" in text
