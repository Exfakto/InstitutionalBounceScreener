from pathlib import Path

from providers.provider_config import ProviderConfig


def write_config(path, text):
    Path(path).write_text(text, encoding="utf-8")


def test_valid_config(tmp_path):
    path = tmp_path / "providers.json"
    write_config(
        path,
        """
        {
          "active_provider": "polygon",
          "providers": {
            "local": {"enabled": true},
            "polygon": {"enabled": false, "api_key_env": "POLYGON_API_KEY"}
          }
        }
        """,
    )

    config = ProviderConfig.load(path)

    assert config.active_provider == "polygon"
    assert config.is_enabled("local") is True
    assert config.is_enabled("polygon") is False
    assert config.provider_settings("polygon") == {
        "enabled": False,
        "api_key_env": "POLYGON_API_KEY",
    }
    assert config.warnings == []


def test_missing_config_uses_safe_defaults(tmp_path):
    config = ProviderConfig.load(tmp_path / "missing.json")

    assert config.active_provider == "local"
    assert config.is_enabled("local") is True
    assert config.provider_settings("polygon") == {}
    assert "Provider config not found; using defaults." in config.warnings


def test_malformed_config_uses_safe_defaults(tmp_path):
    path = tmp_path / "providers.json"
    write_config(path, "{not-json")

    config = ProviderConfig.load(path)

    assert config.active_provider == "local"
    assert config.is_enabled("local") is True
    assert "Provider config malformed; using defaults." in config.warnings


def test_non_object_config_uses_safe_defaults(tmp_path):
    path = tmp_path / "providers.json"
    write_config(path, "[]")

    config = ProviderConfig.load(path)

    assert config.active_provider == "local"
    assert config.is_enabled("local") is True
    assert "Provider config malformed; using defaults." in config.warnings


def test_provider_settings_unknown_and_bad_settings():
    config = ProviderConfig(
        active_provider="local",
        providers={"local": {"enabled": True}, "bad": "enabled"},
    )

    assert config.provider_settings("missing") == {}
    assert config.provider_settings("bad") == {}
    assert config.is_enabled("missing") is False


def test_config_adds_local_default_when_missing(tmp_path):
    path = tmp_path / "providers.json"
    write_config(
        path,
        """
        {
          "active_provider": "local",
          "providers": {
            "polygon": {"enabled": false}
          }
        }
        """,
    )

    config = ProviderConfig.load(path)

    assert config.is_enabled("local") is True
    assert config.is_enabled("polygon") is False
