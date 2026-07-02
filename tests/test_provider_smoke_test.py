from providers.provider_result import ProviderResult
from tools import provider_smoke_test


class FakeSuccessfulProvider:
    def get_price_history(self, ticker):
        return ProviderResult.ok(
            data=[{"ticker": ticker}],
            message="Price history retrieved.",
            source="fake",
        )

    def get_company_profile(self, ticker):
        return ProviderResult.ok(
            data={"ticker": ticker, "name": "Apple Inc."},
            message="Company profile retrieved.",
            source="fake",
        )

    def get_institutional_metrics(self, ticker):
        return ProviderResult.ok(
            data=[{"ticker": ticker, "filing": "13F"}],
            message="Institutional metrics retrieved.",
            source="fake",
        )


class FakeFailedProvider:
    def get_price_history(self, ticker):
        return ProviderResult.fail(
            message="Provider request failed.",
            source="fake",
            warnings=["Failure."],
        )

    def get_company_profile(self, ticker):
        return ProviderResult.fail(
            message="Provider request failed.",
            source="fake",
            warnings=["Failure."],
        )

    def get_institutional_metrics(self, ticker):
        return ProviderResult.fail(
            message="Provider request failed.",
            source="fake",
            warnings=["Failure."],
        )


def collect_output():
    lines = []
    return lines, lines.append


def test_no_live_mode_prints_dry_run(monkeypatch):
    monkeypatch.delenv("POLYGON_API_KEY", raising=False)
    lines, output = collect_output()

    code = provider_smoke_test.run_smoke_test(
        provider="polygon",
        ticker="aapl",
        live=False,
        output=output,
    )

    assert code == 0
    assert "Provider: Polygon" in lines[0]
    assert "Ticker: AAPL" in lines[0]
    assert "Key status: Not Configured" in lines[0]
    assert "Live mode: false" in lines[0]
    assert "Result: not run" in lines[0]


def test_live_mode_successful_mocked_provider(monkeypatch):
    monkeypatch.setenv("POLYGON_API_KEY", "secret")
    lines, output = collect_output()

    code = provider_smoke_test.run_smoke_test(
        provider="polygon",
        ticker="msft",
        live=True,
        provider_factories={"polygon": FakeSuccessfulProvider},
        output=output,
    )

    assert code == 0
    assert "Ticker: MSFT" in lines[0]
    assert "Result: success" in lines[0]
    assert "Record count: 1" in lines[0]


def test_live_mode_missing_key(monkeypatch):
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    lines, output = collect_output()

    code = provider_smoke_test.run_smoke_test(
        provider="fmp",
        ticker="AAPL",
        live=True,
        provider_factories={"fmp": FakeSuccessfulProvider},
        output=output,
    )

    assert code == 1
    assert "Key status: Not Configured" in lines[0]
    assert "Result: failure" in lines[0]


def test_provider_selection_finnhub(monkeypatch):
    monkeypatch.setenv("FINNHUB_API_KEY", "secret")
    lines, output = collect_output()

    code = provider_smoke_test.run_smoke_test(
        provider="finnhub",
        ticker="AAPL",
        live=True,
        provider_factories={"finnhub": FakeSuccessfulProvider},
        output=output,
    )

    assert code == 0
    assert len(lines) == 1
    assert "Provider: Finnhub" in lines[0]


def test_all_providers(monkeypatch):
    monkeypatch.setenv("POLYGON_API_KEY", "secret")
    monkeypatch.setenv("FMP_API_KEY", "secret")
    monkeypatch.setenv("FINNHUB_API_KEY", "secret")
    lines, output = collect_output()

    code = provider_smoke_test.run_smoke_test(
        provider="all",
        ticker="AAPL",
        live=True,
        provider_factories={
            "polygon": FakeSuccessfulProvider,
            "fmp": FakeSuccessfulProvider,
            "finnhub": FakeSuccessfulProvider,
            "sec": FakeSuccessfulProvider,
        },
        output=output,
    )

    assert code == 0
    assert len(lines) == 4
    assert "Provider: SEC EDGAR" in lines[3]


def test_invalid_provider():
    lines, output = collect_output()

    code = provider_smoke_test.run_smoke_test(
        provider="unknown",
        ticker="AAPL",
        live=False,
        output=output,
    )

    assert code == 2
    assert lines == ["Invalid provider: unknown"]


def test_output_does_not_reveal_secrets(monkeypatch):
    monkeypatch.setenv("POLYGON_API_KEY", "top-secret")
    lines, output = collect_output()

    provider_smoke_test.run_smoke_test(
        provider="polygon",
        ticker="AAPL",
        live=True,
        provider_factories={"polygon": FakeSuccessfulProvider},
        output=output,
    )

    assert "top-secret" not in "\n".join(lines)
    assert "Configured" in lines[0]


def test_failed_mocked_provider(monkeypatch):
    monkeypatch.setenv("POLYGON_API_KEY", "secret")
    lines, output = collect_output()

    code = provider_smoke_test.run_smoke_test(
        provider="polygon",
        ticker="AAPL",
        live=True,
        provider_factories={"polygon": FakeFailedProvider},
        output=output,
    )

    assert code == 1
    assert "Result: failure" in lines[0]
    assert "Warning count: 1" in lines[0]


def test_main_parses_arguments(monkeypatch):
    monkeypatch.setenv("POLYGON_API_KEY", "secret")
    lines, output = collect_output()

    monkeypatch.setattr(provider_smoke_test, "print", output, raising=False)
    code = provider_smoke_test.main(["--provider", "polygon", "--ticker", "aapl"])

    assert code == 0
