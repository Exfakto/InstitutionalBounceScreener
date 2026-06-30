import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from analysis import CompositeScore, ScoreResult


class CompositeScoreTest(unittest.TestCase):

    def write_config(self, directory, weights):
        path = Path(directory) / "scoring.json"
        path.write_text(
            json.dumps({"weights": weights}),
            encoding="utf-8",
        )
        return path

    def test_calculate_uses_config_weights(self):
        with TemporaryDirectory() as directory:
            path = self.write_config(
                directory,
                {
                    "quality_score": 0.75,
                    "institutional_score": 0.25,
                },
            )

            result = CompositeScore(path).calculate(
                {
                    "quality_score": 80,
                    "institutional_score": 40,
                }
            )

        self.assertEqual(result.name, "composite_score")
        self.assertEqual(result.value, 70.0)
        self.assertEqual(result.details["values"]["quality_score"], 80.0)

    def test_calculate_accepts_score_result_values(self):
        with TemporaryDirectory() as directory:
            path = self.write_config(directory, {"quality_score": 1.0})

            result = CompositeScore(path).calculate(
                {
                    "quality_score": ScoreResult(
                        name="quality_score",
                        value=82.0,
                    )
                }
            )

        self.assertEqual(result.value, 82.0)

    def test_missing_config_returns_zero_score(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "missing.json"

            result = CompositeScore(path).calculate({"quality_score": 90})

        self.assertEqual(result.value, 0.0)

    def test_missing_weighted_values_are_ignored(self):
        with TemporaryDirectory() as directory:
            path = self.write_config(
                directory,
                {
                    "quality_score": 0.5,
                    "institutional_score": 0.5,
                },
            )

            result = CompositeScore(path).calculate({"quality_score": 90})

        self.assertEqual(result.value, 90.0)


if __name__ == "__main__":
    unittest.main()
