import unittest
from datetime import datetime

from analysis import CandidateScore, ScoreResult
from analysis.institutional_checklist import InstitutionalChecklistEvaluator
from analysis.opportunity_rating import OpportunityRatingCalculator
from analysis.trade_thesis import TradeThesisGenerator


class CandidateScoreTest(unittest.TestCase):

    def test_candidate_score_tracks_scores_and_timestamp(self):
        quality = ScoreResult("quality_score", 75.0)
        composite = ScoreResult("composite_score", 80.0)

        candidate = CandidateScore(
            ticker="AAPL",
            scores=[quality],
            composite_score=composite,
        )

        self.assertEqual(candidate.ticker, "AAPL")
        self.assertEqual(candidate.score_map["quality_score"], quality)
        self.assertEqual(candidate.composite_score, composite)
        self.assertIsInstance(candidate.timestamp, datetime)
        self.assertIsNone(candidate.institutional_bounce_score)
        self.assertIsNone(candidate.opportunity_rating)
        self.assertIsNone(candidate.institutional_checklist)
        self.assertIsNone(candidate.trade_thesis)
        self.assertEqual(candidate.primary_score_value, 80.0)

    def test_candidate_score_uses_gen2_as_primary_score_when_available(self):
        candidate = CandidateScore(
            ticker="AAPL",
            scores=[],
            composite_score=ScoreResult("composite_score", 40.0),
            institutional_bounce_score=92.0,
            composite_intelligence_component_scores={"quality_score": 90.0},
            missing_components=["risk_score"],
            warnings=["Missing components reduced confidence"],
        )

        self.assertEqual(candidate.primary_score_value, 92.0)
        self.assertEqual(
            candidate.composite_intelligence_component_scores["quality_score"],
            90.0,
        )
        self.assertEqual(candidate.missing_components, ["risk_score"])
        self.assertEqual(
            candidate.warnings,
            ["Missing components reduced confidence"],
        )

    def test_candidate_score_stores_decision_fields(self):
        metrics = {
            "ticker": "AAPL",
            "institutional_bounce_score": 80.0,
            "institutional_score": 80.0,
            "institutional_momentum_score": 80.0,
            "relative_strength_score": 80.0,
            "trend_score": 80.0,
            "support_score": 80.0,
            "bounce_score": 80.0,
            "volume_score": 80.0,
            "earnings_risk_score": 20.0,
            "risk_score": 80.0,
            "distance_to_support_pct": 2.0,
            "bounce_success_rate": 80.0,
        }
        opportunity = OpportunityRatingCalculator().calculate(metrics)
        metrics["opportunity_rating"] = opportunity
        metrics["opportunity_rating_score"] = opportunity.rating_score
        checklist = InstitutionalChecklistEvaluator().evaluate(
            metrics
        )
        metrics["institutional_checklist"] = checklist
        thesis = TradeThesisGenerator().generate(metrics)
        candidate = CandidateScore(
            ticker="AAPL",
            scores=[],
            composite_score=ScoreResult("composite_score", 80.0),
            opportunity_rating=opportunity,
            institutional_checklist=checklist,
            trade_thesis=thesis,
        )

        self.assertEqual(candidate.opportunity_rating, opportunity)
        self.assertEqual(candidate.institutional_checklist, checklist)
        self.assertEqual(candidate.trade_thesis, thesis)
        self.assertEqual(
            candidate.institutional_checklist.overall_label,
            "Exceptional",
        )


if __name__ == "__main__":
    unittest.main()
