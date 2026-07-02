import json

from services.settings_service import SettingsService


def test_settings_service_loads_defaults_for_missing_config(tmp_path):
    service = SettingsService(
        settings_path=tmp_path / "settings.json",
        provider_config_path=tmp_path / "providers.json",
    )

    settings = service.load()

    assert settings["general"]["default_workspace"] == "Dashboard"
    assert settings["refresh"]["interval"] == 300
    assert settings["appearance"]["theme"] == "Dark"
    assert settings["paths"]["database_path"].endswith("InstitutionalBounce.db")


def test_settings_service_saves_settings_and_preserves_unrelated_keys(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "unrelated": {"keep": True},
                "general": {"default_workspace": "Old"},
            }
        ),
        encoding="utf-8",
    )
    service = SettingsService(
        settings_path=settings_path,
        provider_config_path=tmp_path / "providers.json",
    )

    saved = service.save(
        {
            "general": {"default_workspace": "Research"},
            "paths": {"export_path": "C:/Exports"},
        }
    )
    persisted = json.loads(settings_path.read_text(encoding="utf-8"))

    assert saved["general"]["default_workspace"] == "Research"
    assert persisted["unrelated"]["keep"] is True
    assert persisted["paths"]["export_path"] == "C:/Exports"


def test_settings_service_loads_defaults_for_malformed_config(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text("{bad json", encoding="utf-8")
    service = SettingsService(
        settings_path=settings_path,
        provider_config_path=tmp_path / "providers.json",
    )

    settings = service.load()

    assert settings["general"]["default_workspace"] == "Dashboard"


def test_settings_service_provider_status_is_display_safe(tmp_path, monkeypatch):
    provider_config_path = tmp_path / "providers.json"
    provider_config_path.write_text(
        json.dumps(
            {
                "active_provider": "polygon",
                "providers": {
                    "local": {"enabled": True},
                    "polygon": {
                        "enabled": True,
                        "api_key_env": "POLYGON_API_KEY",
                    },
                    "fmp": {"enabled": False, "api_key_env": "FMP_API_KEY"},
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("POLYGON_API_KEY", "secret-value")
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    service = SettingsService(
        settings_path=tmp_path / "settings.json",
        provider_config_path=provider_config_path,
    )

    status = service.provider_status()

    assert status["current_provider"] == "polygon"
    assert status["enabled_providers"] == ["local", "polygon"]
    assert status["api_key_status"]["Polygon"] == "Configured"
    assert status["api_key_status"]["FMP"] == "Not Configured"
    assert status["api_key_status"]["Finnhub"] == "Not Configured"
    assert status["api_key_status"]["SEC EDGAR"] == "Configured"
    assert "secret-value" not in str(status)


def test_settings_service_export_path_update(tmp_path):
    settings_path = tmp_path / "settings.json"
    service = SettingsService(
        settings_path=settings_path,
        provider_config_path=tmp_path / "providers.json",
    )

    service.save({"paths": {"export_path": "D:/ResearchExports"}})

    assert service.load()["paths"]["export_path"] == "D:/ResearchExports"
