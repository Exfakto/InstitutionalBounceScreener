from controllers.screening_controller import ScreeningController
from services.full_universe_validation_service import FullUniverseValidationService


class Universe:
    def __init__(self, tickers):
        self.tickers = tickers

    def load_tickers(self):
        return list(self.tickers)


def test_full_universe_validation_successful_validation():
    progress = []
    service = FullUniverseValidationService(
        universe_adapter=Universe(["AAPL", "MSFT"]),
        screening_runner=lambda tickers: {"processed": 2, "warnings": [], "errors": []},
    )

    result = service.validate(progress_callback=progress.append)

    assert result.status == "passed"
    assert result.total_symbols == 2
    assert result.processed_symbols == 2
    assert result.skipped_symbols == 0
    assert result.failed_symbols == 0
    assert result.completion_rate == 100
    assert progress[-1]["completion_rate"] == 100


def test_full_universe_validation_partial_failures():
    service = FullUniverseValidationService(
        universe_adapter=Universe(["AAPL", "MSFT", "NVDA"]),
        screening_runner=lambda tickers: {
            "processed": 2,
            "warnings": ["MSFT: missing OHLCV coverage"],
            "errors": ["NVDA: support calculation failed"],
        },
    )

    result = service.validate()

    assert result.status == "failed"
    assert result.total_symbols == 3
    assert result.processed_symbols == 2
    assert result.failed_symbols == 2
    assert result.issues[0].category == "data missing"
    assert result.issues[1].category == "calculation failure"


def test_full_universe_validation_provider_error():
    def failing_runner(tickers):
        raise RuntimeError("provider timeout")

    service = FullUniverseValidationService(
        universe_adapter=Universe(["AAPL", "MSFT"]),
        screening_runner=failing_runner,
    )

    result = service.validate()

    assert result.status == "failed"
    assert result.failed_symbols == 2
    assert result.issues[0].category == "provider failure"
    assert "provider timeout" in result.errors[0]


def test_full_universe_validation_empty_universe():
    result = FullUniverseValidationService(universe_adapter=Universe([])).validate()

    assert result.status == "warning"
    assert result.total_symbols == 0
    assert result.issues[0].category == "data missing"
    assert "No eligible" in result.warnings[0]


def test_full_universe_validation_categorizes_ranking_and_export_issues():
    service = FullUniverseValidationService(
        universe_adapter=Universe(["AAPL", "MSFT"]),
        screening_runner=lambda tickers: {
            "processed": 1,
            "warnings": ["AAPL: ranking skipped"],
            "errors": ["MSFT: export failed"],
        },
    )

    result = service.validate()
    categories = {issue.category for issue in result.issues}

    assert "ranking failure" in categories
    assert "export failure" in categories


def test_screening_controller_full_universe_validation_integration():
    class ValidationService:
        def __init__(self):
            self.called = False

        def validate(self, progress_callback=None, cancellation_callback=None):
            self.called = True
            return "validated"

    service = ValidationService()
    controller = ScreeningController(full_universe_validation_service=service)

    assert controller.validate_full_universe() == "validated"
    assert service.called is True
