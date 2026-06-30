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


if __name__ == "__main__":
    unittest.main()
