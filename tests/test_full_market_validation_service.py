from services.full_market_pipeline import PipelineResult
from services.full_market_validation_service import FullMarketValidationService


class FakeClock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        self.value += 1.0
        return self.value


class UniverseService:
    def update_universe(self):
        return PipelineResult(
            processed=1200,
            persisted=1100,
            warnings=["partial page warning"],
            details={"eligible_count": 1100, "skipped": 100},
        )


class HistoricalService:
    def update_history(self, tickers, **kwargs):
        return PipelineResult(processed=len(tickers), persisted=250000)


class FundamentalService:
    def update_fundamentals(self, tickers, **kwargs):
        return PipelineResult(processed=len(tickers), persisted=len(tickers) - 5)


class InstitutionalService:
    def update_institutional_data(self, tickers, **kwargs):
        return PipelineResult(
            processed=len(tickers),
            persisted=0,
            warnings=["Provider does not expose institutional data"],
        )


class ScanRunner:
    def run_scan(self, **kwargs):
        return PipelineResult(
            processed=1095,
            persisted=12,
            details={"run_id": "run-1", "skipped": 1083},
        )


class CoverageService:
    def report(self):
        return {
            "ticker_count": 1100,
            "ohlcv_covered_count": 1095,
            "scan_ready_count": 1095,
            "missing_ohlcv": ["MISS1", "MISS2", "MISS3", "MISS4", "MISS5"],
            "missing_fundamentals": [],
            "missing_institutional": ["AAPL"],
            "warnings": ["Missing institutional data for 1 ticker(s)"],
        }


def test_full_market_validation_service_instruments_all_stages():
    service = FullMarketValidationService(
        universe_service=UniverseService(),
        historical_service=HistoricalService(),
        fundamental_service=FundamentalService(),
        institutional_service=InstitutionalService(),
        scan_runner=ScanRunner(),
        coverage_service=CoverageService(),
        ticker_source=lambda: [f"T{i:04d}" for i in range(1100)],
        clock=FakeClock(),
    )

    report = service.validate()

    assert report.success is True
    assert [stage.stage for stage in report.stages] == [
        "Update Universe",
        "Refresh Market Data",
        "Refresh Fundamentals",
        "Refresh Institutional Data",
        "Run Full Market Scan",
    ]
    assert report.universe_size == 1100
    assert report.stages[0].processed == 1200
    assert report.stages[0].skipped == 100
    assert report.stages[1].throughput_per_second == 1100
    assert "Provider does not expose institutional data" in report.warnings
    assert report.errors == []


def test_full_market_validation_service_captures_stage_exceptions():
    class ProviderException(RuntimeError):
        provider = "polygon"
        endpoint = "/v3/reference/tickers"
        ticker = "AAPL"

    class BrokenUniverseService:
        def update_universe(self):
            raise ProviderException("planned failure")

    service = FullMarketValidationService(
        universe_service=BrokenUniverseService(),
        historical_service=HistoricalService(),
        scan_runner=ScanRunner(),
        coverage_service=CoverageService(),
        ticker_source=lambda: ["AAPL"],
        clock=FakeClock(),
    )

    report = service.validate()

    assert report.success is False
    assert "provider=polygon" in report.stages[0].errors[0]
    assert "endpoint=/v3/reference/tickers" in report.stages[0].errors[0]
    assert "ticker=AAPL" in report.stages[0].errors[0]
    assert any("Update Universe errors" in item for item in report.recommendations)


def test_full_market_validation_markdown_contains_core_metrics():
    report = FullMarketValidationService(
        universe_service=UniverseService(),
        historical_service=HistoricalService(),
        scan_runner=ScanRunner(),
        coverage_service=CoverageService(),
        ticker_source=lambda: ["AAPL"],
        clock=FakeClock(),
    ).validate()

    markdown = FullMarketValidationService.markdown(report)

    assert "# Full Market Validation" in markdown
    assert "Universe size: 1,100" in markdown
    assert "Refresh Market Data" in markdown
    assert "Throughput:" in markdown
