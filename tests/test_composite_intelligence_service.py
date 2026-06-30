import unittest

from analysis.composite_intelligence import CompositeIntelligenceCalculator
from analysis.score_result import ScoreResult
from services.composite_intelligence_service import CompositeIntelligenceService


class FakeCandidate:

    def __init__(self):
        self.scores = [
            ScoreResult("quality_score", 80),
            ScoreResult("institutional_score", 70),
            ScoreResult("technical_score", 60),
            ScoreResult("support_score", 75),
            ScoreResult("bounce_score", 65),
        ]


class FakeScoringDatabase:

    def __init__(self):
        self.closed = False

    def get_all_tickers(self):
        return ["AAA", "EMPTY"]

    def get_earnings(self, ticker):
        if ticker == "AAA":
            return {"earnings_risk_score": 55}
        return None


class FakeScoringService:

    def __init__(self, missing=False):
        self.db = FakeScoringDatabase()
        self.closed = False
        self.missing = missing

    def score_candidate(self, ticker):
        if self.missing or ticker == "EMPTY":
            raise ValueError("missing core data")
        return FakeCandidate()

    def close(self):
        self.closed = True


class FakeRelativeStrengthService:

    def calculate_relative_strength(self, tickers):
        ticker = tickers[0]
        if ticker == "AAA":
            return {"results": {ticker: type("RS", (), {"rs_score": 72})()}}
        return {"results": {}}

    def close(self):
        pass


class FakeSingleResultService:

    def __init__(self, attribute, value):
        self.attribute = attribute
        self.value = value
        self.closed = False

    def calculate_for_ticker(self, ticker):
        if ticker != "AAA":
            return {"processed": False, "result": None}

        return {
            "processed": True,
            "result": type(
                "Result",
                (),
                {
                    self.attribute: self.value,
                },
            )(),
        }

    def close(self):
        self.closed = True


class FakeMomentumService:

    def calculate_for_ticker(self, ticker):
        if ticker != "AAA":
            return {"processed": False, "result": None}

        return {
            "processed": True,
            "result": type("Momentum", (), {"momentum_score": 68})(),
        }


class CompositeIntelligenceServiceTest(unittest.TestCase):

    def build_service(self, missing_core=False):
        service = CompositeIntelligenceService.__new__(CompositeIntelligenceService)
        service.scoring_service = FakeScoringService(missing=missing_core)
        service.relative_strength_service = FakeRelativeStrengthService()
        service.volume_service = FakeSingleResultService("volume_score", 66)
        service.trend_service = FakeSingleResultService("trend_score", 64)
        service.atr_service = FakeSingleResultService("risk_score", 58)
        service.support_distance_service = FakeSingleResultService(
            "entry_quality_score",
            82,
        )
        service.institutional_momentum_service = FakeMomentumService()
        service.earnings_score = None
        service.calculator = CompositeIntelligenceCalculator(
            weights={
                "quality_score": 15,
                "institutional_score": 12,
                "institutional_momentum_score": 10,
                "technical_score": 10,
                "relative_strength_score": 10,
                "support_score": 12,
                "bounce_score": 12,
                "entry_quality_score": 8,
                "volume_score": 5,
                "trend_score": 4,
                "earnings_risk_score": 1,
                "risk_score": 1,
            }
        )
        return service

    def test_calculate_for_ticker_gathers_components(self):
        service = self.build_service()

        result = service.calculate_for_ticker("AAA")

        self.assertTrue(result["processed"])
        self.assertFalse(result["skipped"])
        self.assertIn("quality_score", result["component_scores"])
        self.assertIn("relative_strength_score", result["component_scores"])
        self.assertIn("entry_quality_score", result["component_scores"])
        self.assertIn("institutional_momentum_score", result["component_scores"])
        self.assertGreater(result["result"].institutional_bounce_score, 0.0)

    def test_calculate_for_ticker_skips_when_all_data_missing(self):
        service = self.build_service(missing_core=True)

        result = service.calculate_for_ticker("EMPTY")

        self.assertFalse(result["processed"])
        self.assertTrue(result["skipped"])
        self.assertIn("No valid component scores available", result["warnings"])

    def test_calculate_all_processes_active_tickers(self):
        service = self.build_service()

        results = service.calculate_all()

        self.assertEqual(results["tickers"], 2)
        self.assertEqual(results["processed"], 1)
        self.assertEqual(results["processed_tickers"], ["AAA"])
        self.assertEqual(results["skipped"], 1)
        self.assertEqual(results["skipped_tickers"], ["EMPTY"])
        self.assertIn("AAA", results["results"])

    def test_calculate_all_accepts_explicit_tickers(self):
        service = self.build_service()

        results = service.calculate_all(["AAA"])

        self.assertEqual(results["tickers"], 1)
        self.assertEqual(results["processed"], 1)
        self.assertEqual(results["processed_tickers"], ["AAA"])


if __name__ == "__main__":
    unittest.main()
