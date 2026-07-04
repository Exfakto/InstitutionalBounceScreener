from types import SimpleNamespace

from PySide6.QtWidgets import QApplication

from services.bounce_composite_scoring_engine import BounceCompositeScoreResult
from services.screening_orchestrator import ScreeningOrchestrator
from ui.widgets.screening_results_panel import ScreeningResultsPanel


def app():
    return QApplication.instance() or QApplication([])


class SmokePriceProvider:
    def __init__(self):
        self.calls = []

    def get_price_history(self, ticker):
        self.calls.append(ticker)
        return [
            {
                "date": f"2026-06-{day:02d}",
                "open": 100.0,
                "high": 104.0,
                "low": 98.0,
                "close": 102.0,
                "volume": 1_000_000,
            }
            for day in range(1, 22)
        ]


class SmokeSupportEngine:
    def detect_support_zones(self, ticker, prices):
        return SimpleNamespace(
            ticker=ticker,
            zones=[SimpleNamespace(zone_low=98.0, zone_high=101.0)],
            primary_zone=SimpleNamespace(zone_low=98.0, zone_high=101.0),
            warnings=[],
        )


class SmokeBounceEngine:
    def analyze_bounces(self, ticker, prices, zones):
        return SimpleNamespace(
            ticker=ticker,
            bounce_success_rate=80.0,
            average_bounce_pct=12.0,
            warnings=[],
        )


class SmokeTechnicalEngine:
    def calculate(self, prices, ticker=None):
        return SimpleNamespace(ticker=ticker, rsi14=62.0, ema20=101.0, warnings=[])


class SmokeInstitutionalEngine:
    def score_ticker(self, ticker):
        return SimpleNamespace(ticker=ticker, score_result=SimpleNamespace(overall_score=86.0), warnings=[])


class SmokeCompositeEngine:
    def score(self, ticker, support, bounce, technical, institutional):
        return BounceCompositeScoreResult(
            ticker=ticker,
            final_score=88.0,
            support_score=86.0,
            bounce_score=84.0,
            technical_score=82.0,
            institutional_score=87.0,
            confidence_level="HIGH",
            explanation=["RC1 smoke candidate"],
            warnings=[],
        )


def test_rc1_smoke_mocked_screening_run_completes_and_displays_candidates():
    app()
    price_provider = SmokePriceProvider()
    orchestrator = ScreeningOrchestrator(
        price_history_provider=price_provider,
        support_engine=SmokeSupportEngine(),
        bounce_engine=SmokeBounceEngine(),
        technical_engine=SmokeTechnicalEngine(),
        institutional_engine=SmokeInstitutionalEngine(),
        composite_engine=SmokeCompositeEngine(),
    )

    result = orchestrator.run(["aapl"], run_id="rc1-smoke-screening")
    panel = ScreeningResultsPanel()
    panel.populate_ranked_candidates(result.ranked_candidates, total_count=1)

    assert result.status == "COMPLETED"
    assert result.tickers_processed == 1
    assert price_provider.calls == ["AAPL"]
    assert len(result.ranked_candidates) == 1
    assert result.ranked_candidates[0].ticker == "AAPL"
    assert panel.ranked_candidates_table.rowCount() == 1
    assert panel.ranked_candidates_table.item(0, 1).text() == "AAPL"
