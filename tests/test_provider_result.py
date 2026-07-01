from providers.provider_result import ProviderResult


def test_provider_result_success():
    result = ProviderResult.ok(
        data={"ticker": "AAPL"},
        message="ok",
        source="local",
        warnings=["partial"],
        metadata={"rows": 1},
    )

    assert result.success is True
    assert result.data == {"ticker": "AAPL"}
    assert result.message == "ok"
    assert result.source == "local"
    assert result.warnings == ["partial"]
    assert result.metadata == {"rows": 1}


def test_provider_result_failure():
    result = ProviderResult.fail(
        "missing",
        source="local",
        warnings=["Missing ticker."],
    )

    assert result.success is False
    assert result.data is None
    assert result.message == "missing"
    assert result.source == "local"
    assert result.warnings == ["Missing ticker."]
    assert result.metadata == {}
