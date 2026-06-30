import unittest
from datetime import datetime

from analysis import CandidateScore, ScoreResult


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


if __name__ == "__main__":
    unittest.main()
