import sys

from services.resource_path_service import ResourcePathService


def test_resource_path_helper_dev_mode_paths(tmp_path):
    (tmp_path / "config").mkdir()
    service = ResourcePathService(base_path=tmp_path)

    assert service.path("config") == tmp_path / "config"
    assert service.exists("config") is True
    assert service.default_config_path("providers.json") == tmp_path / "config" / "providers.json"
    assert service.icon_path() == tmp_path / "resources" / "app_icon.ico"


def test_resource_path_helper_packaged_mode(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    assert ResourcePathService.is_packaged() is True
    assert ResourcePathService.default_base_path() == tmp_path
