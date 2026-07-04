from services.full_market_pipeline import InstitutionalDataRefreshService, PipelineResult
from tests.full_market_test_utils import FakeProviderFactory, build_manager


class NoInstitutionalProvider:
    pass


def test_institutional_refresh_persists_existing_repository_model():
    manager = build_manager()

    result = InstitutionalDataRefreshService(
        repository=manager,
        provider_factory=FakeProviderFactory(),
    ).update_institutional_data(["AAPL", "FAIL"])

    assert result.success is False
    assert result.persisted == 1
    assert "FAIL: institutional unavailable" in result.errors
    assert manager.get_institutional_data("AAPL").institutional_ownership_pct == 70


def test_institutional_refresh_handles_unsupported_provider_and_missing_factory():
    unsupported = InstitutionalDataRefreshService(
        repository=None,
        provider_factory=FakeProviderFactory(NoInstitutionalProvider()),
    ).update_institutional_data(["AAPL"])
    missing = InstitutionalDataRefreshService(repository=None, provider_factory=None).update_institutional_data(["AAPL"])

    assert unsupported.success is True
    assert unsupported.warnings == ["Provider does not expose institutional data"]
    assert missing.success is False
    assert missing.errors == ["provider factory unavailable"]
