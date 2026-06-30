import unittest

from analysis import ScoreResult


class ScoreResultTest(unittest.TestCase):

    def test_score_result_tracks_success(self):
        result = ScoreResult(
            name="quality_score",
            value=72.5,
            details={"source": "test"},
        )

        self.assertEqual(result.name, "quality_score")
        self.assertEqual(result.value, 72.5)
        self.assertFalse(result.failed)

    def test_score_result_tracks_failure(self):
        result = ScoreResult(
            name="quality_score",
            value=0.0,
            error="planned failure",
        )

        self.assertTrue(result.failed)


if __name__ == "__main__":
    unittest.main()
