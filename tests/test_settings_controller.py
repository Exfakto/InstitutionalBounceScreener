from controllers.settings_controller import SettingsController


class FakeSettingsService:
    def __init__(self):
        self.saved_settings = None

    def load(self):
        return {"general": {"default_workspace": "Dashboard"}}

    def save(self, settings):
        self.saved_settings = settings
        return settings

    def provider_status(self):
        return {"current_provider": "local"}


def test_settings_controller_loads_from_service():
    service = FakeSettingsService()
    controller = SettingsController(settings_service=service)

    assert controller.load_settings()["general"]["default_workspace"] == "Dashboard"


def test_settings_controller_saves_through_service():
    service = FakeSettingsService()
    controller = SettingsController(settings_service=service)
    settings = {"general": {"default_workspace": "Research"}}

    result = controller.save_settings(settings)

    assert result == settings
    assert service.saved_settings == settings


def test_settings_controller_returns_provider_status():
    service = FakeSettingsService()
    controller = SettingsController(settings_service=service)

    assert controller.provider_status() == {"current_provider": "local"}
