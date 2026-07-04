from services.live_provider_resilience_service import ProviderHealthResult
from services.provider_configuration_validation_service import (
    ProviderConfigurationValidationService,
    VALIDATION_FAILED,
    VALIDATION_PASSED,
    VALIDATION_WARNING,
)


def settings(**overrides):
    data = {
        "selected_market_data_provider": "polygon",
        "polygon_api_key": "polygon-key",
        "fmp_api_key": "fmp-key",
        "alpaca_api_key": "alpaca-key",
        "alpaca_api_secret": "alpaca-secret",
        "request_timeout_seconds": 10,
        "max_retries": 2,
        "rate_limit_sleep_seconds": 1,
    }
    data.update(overrides)
    return data


def health(name="polygon", status="healthy"):
    return ProviderHealthResult(provider_name=name, status=status)


def messages(result):
    return [issue.message for issue in result.issues]


def test_provider_configuration_validation_valid_configuration():
    service = ProviderConfigurationValidationService()

    result = service.validate(
        settings=settings(),
        health=[health("polygon", "healthy"), health("fmp", "healthy")],
    )

    assert result.status == VALIDATION_PASSED
    assert result.passed is True
    assert result.issues == []


def test_provider_configuration_validation_missing_api_key():
    service = ProviderConfigurationValidationService()

    result = service.validate(
        settings=settings(polygon_api_key=""),
        health=[health("polygon", "healthy"), health("fmp", "healthy")],
    )

    assert result.status == VALIDATION_FAILED
    assert "Polygon API key is required" in messages(result)
    assert result.issues[0].affected_setting == "polygon_api_key"


def test_provider_configuration_validation_invalid_timeout():
    service = ProviderConfigurationValidationService()

    result = service.validate(
        settings=settings(request_timeout_seconds=0),
        health=[health("polygon", "healthy"), health("fmp", "healthy")],
    )

    assert result.status == VALIDATION_FAILED
    assert "Request timeout must be greater than zero" in messages(result)


def test_provider_configuration_validation_invalid_retry_settings():
    service = ProviderConfigurationValidationService()

    result = service.validate(
        settings=settings(max_retries=-1, rate_limit_sleep_seconds=-2),
        health=[health("polygon", "healthy"), health("fmp", "healthy")],
    )

    assert result.status == VALIDATION_FAILED
    assert "Max retries cannot be negative" in messages(result)
    assert "Rate-limit sleep cannot be negative" in messages(result)


def test_provider_configuration_validation_missing_failover_provider_warning():
    service = ProviderConfigurationValidationService()

    result = service.validate(
        settings=settings(),
        health=[health("polygon", "healthy")],
    )

    assert result.status == VALIDATION_WARNING
    assert "No failover provider is currently available" in messages(result)


def test_provider_configuration_validation_requires_healthy_provider():
    service = ProviderConfigurationValidationService()

    result = service.validate(
        settings=settings(),
        health=[health("polygon", "unavailable"), health("fmp", "degraded")],
    )

    assert result.status == VALIDATION_FAILED
    assert "No healthy market data provider is configured" in messages(result)


def test_provider_configuration_validation_local_csv_does_not_require_api_key_or_failover():
    service = ProviderConfigurationValidationService()

    result = service.validate(
        settings=settings(
            selected_market_data_provider="local_csv",
            polygon_api_key="",
            request_timeout_seconds=10,
        ),
        health=[],
    )

    assert result.status == VALIDATION_PASSED


def test_provider_configuration_validation_bad_endpoint():
    service = ProviderConfigurationValidationService()

    result = service.validate(
        settings=settings(polygon_endpoint="polygon.example.com"),
        health=[health("polygon", "healthy"), health("fmp", "healthy")],
    )

    assert result.status == VALIDATION_FAILED
    assert "polygon endpoint must be a valid HTTP URL" in messages(result)
