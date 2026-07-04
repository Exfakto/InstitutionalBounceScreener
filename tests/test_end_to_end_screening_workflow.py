from types import SimpleNamespace

from PySide6.QtWidgets import QApplication

from services.bounce_composite_scoring_engine import BounceCompositeScoreResult
from services.screening_orchestrator import ScreeningOrchestrator
from ui.main_window import MainWindow
from ui.widgets.screening_results_panel import ScreeningResultsPanel


def app():
    return QApplication.instance() or QApplication([])


def price_rows():
    return [
        {
            "date": f"2026-06-{day:02d}",
            "open": 100 + day,
            "high": 102 + day,
            "low": 98 + day,
            "close": 101 + day,
            "volume": 1_000_000 + day,
        }
        for day in range(1, 21)
    ]


class FakeUniverseLoader:
    def load_tickers(self):
        return ["aapl", "MSFT", "aapl", "", None]


class FakePriceProvider:
    def __init__(self):
        self.calls = []

    def get_price_history(self, ticker):
        self.calls.append(ticker)
        return price_rows()


class RecordingSupportEngine:
    def __init__(self):
        self.calls = []

    def detect_support_zones(self, ticker, prices):
        self.calls.append((ticker, len(prices)))
        return SimpleNamespace(
            ticker=ticker,
            zones=[SimpleNamespace(zone_low=98.0, zone_high=102.0)],
            primary_zone=SimpleNamespace(zone_low=98.0, zone_high=102.0),
            warnings=[],
        )


class RecordingBounceEngine:
    def __init__(self):
        self.calls = []

    def analyze_bounces(self, ticker, prices, zones):
        self.calls.append((ticker, len(prices), len(zones)))
        return SimpleNamespace(
            ticker=ticker,
            total_support_tests=4,
            bounce_success_rate=82.0,
            average_bounce_pct=13.0,
            warnings=[],
        )


class RecordingTechnicalEngine:
    def __init__(self):
        self.calls = []

    def calculate(self, prices, ticker=None):
        self.calls.append((ticker, len(prices)))
        return SimpleNamespace(ticker=ticker, rsi14=61.0, ema20=101.0, warnings=[])


class RecordingInstitutionalEngine:
    def __init__(self):
        self.calls = []

    def score_ticker(self, ticker):
        self.calls.append(ticker)
        return SimpleNamespace(
            ticker=ticker,
            score_result=SimpleNamespace(overall_score=88.0),
            warnings=[],
        )


class RecordingCompositeEngine:
    def __init__(self):
        self.calls = []

    def score(self, ticker, support, bounce, technical, institutional):
        self.calls.append((ticker, support, bounce, technical, institutional))
        score = 92.0 if ticker == "AAPL" else 84.0
        return BounceCompositeScoreResult(
            ticker=ticker,
            final_score=score,
            support_score=90.0,
            bounce_score=86.0,
            technical_score=82.0,
            institutional_score=88.0,
            confidence_level="HIGH",
            explanation=["End-to-end institutional bounce setup"],
            warnings=[],
        )


def test_end_to_end_screening_workflow_startup_to_results_display():
    app()
    window = MainWindow()
    universe = FakeUniverseLoader()
    tickers = ScreeningOrchestrator.normalize_tickers(universe.load_tickers())
    price_provider = FakePriceProvider()
    support = RecordingSupportEngine()
    bounce = RecordingBounceEngine()
    technical = RecordingTechnicalEngine()
    institutional = RecordingInstitutionalEngine()
    composite = RecordingCompositeEngine()
    orchestrator = ScreeningOrchestrator(
        price_history_provider=price_provider,
        support_engine=support,
        bounce_engine=bounce,
        technical_engine=technical,
        institutional_engine=institutional,
        composite_engine=composite,
        batch_size=1,
    )

    result = orchestrator.run(tickers, run_id="e2e-screening", allow_low_confidence=True)
    panel = ScreeningResultsPanel()
    panel.populate_ranked_candidates(result.ranked_candidates, total_count=len(result.ranked_candidates))

    assert window.windowTitle() == "Institutional Bounce Screener"
    assert tickers == ["AAPL", "MSFT"]
    assert result.status == "COMPLETED"
    assert result.tickers_processed == 2
    assert [candidate.ticker for candidate in result.ranked_candidates] == ["AAPL", "MSFT"]
    assert price_provider.calls == ["AAPL", "MSFT"]
    assert [call[0] for call in support.calls] == ["AAPL", "MSFT"]
    assert [call[0] for call in bounce.calls] == ["AAPL", "MSFT"]
    assert [call[0] for call in technical.calls] == ["AAPL", "MSFT"]
    assert institutional.calls == ["AAPL", "MSFT"]
    assert [call[0] for call in composite.calls] == ["AAPL", "MSFT"]
    assert panel.ranked_candidates_table.rowCount() == 2
    rendered_tickers = {
        panel.ranked_candidates_table.item(row, 1).text()
        for row in range(panel.ranked_candidates_table.rowCount())
    }
    assert rendered_tickers == {"AAPL", "MSFT"}
    window.close()
