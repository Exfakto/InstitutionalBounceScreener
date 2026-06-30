import unittest

from analysis.composite_intelligence import CompositeIntelligenceCalculator
from analysis.score_result import ScoreResult


class CompositeIntelligenceCalculatorTest(unittest.TestCase):

    def test_full_component_set_scores_weighted_average(self):
        calculator = CompositeIntelligenceCalculator(weights={"a": 50, "b": 50})

        result = calculator.calculate({"a": 80, "b": 60})

        self.assertEqual(result.institutional_bounce_score, 70.0)
        self.assertEqual(result.missing_components, [])
        self.assertEqual(result.component_scores["a"], 80.0)
        self.assertEqual(result.weighted_breakdown["a"]["weight"], 0.5)

    def test_missing_components_reduce_confidence(self):
        calculator = CompositeIntelligenceCalculator(weights={"a": 50, "b": 50})

        result = calculator.calculate({"a": 80})

        self.assertEqual(result.missing_components, ["b"])
        self.assertEqual(result.institutional_bounce_score, 60.0)
        self.assertIn("Missing components reduced confidence", result.warnings)

    def test_all_components_missing_returns_zero(self):
        calculator = CompositeIntelligenceCalculator(weights={"a": 100})

        result = calculator.calculate({})

        self.assertEqual(result.institutional_bounce_score, 0.0)
        self.assertEqual(result.missing_components, ["a"])
        self.assertIn("No valid component scores available", result.warnings)

    def test_invalid_component_values_are_ignored(self):
        calculator = CompositeIntelligenceCalculator(weights={"a": 50, "b": 50})

        result = calculator.calculate({"a": "bad", "b": 80})

        self.assertNotIn("a", result.component_scores)
        self.assertIn("Invalid component value for a", result.warnings)
        self.assertIn("a", result.missing_components)

    def test_weights_are_normalized(self):
        calculator = CompositeIntelligenceCalculator(weights={"a": 2, "b": 1})

        result = calculator.calculate({"a": 90, "b": 60})

        self.assertAlmostEqual(result.institutional_bounce_score, 80.0)
        self.assertAlmostEqual(result.weighted_breakdown["a"]["weight"], 2 / 3)

    def test_scores_are_clamped(self):
        calculator = CompositeIntelligenceCalculator(weights={"a": 50, "b": 50})

        result = calculator.calculate({"a": 150, "b": -20})

        self.assertEqual(result.component_scores["a"], 100.0)
        self.assertEqual(result.component_scores["b"], 0.0)
        self.assertEqual(result.institutional_bounce_score, 50.0)

    def test_injected_test_weights_accept_score_result_values(self):
        calculator = CompositeIntelligenceCalculator(weights={"quality_score": 100})

        result = calculator.calculate(
            {
                "quality_score": ScoreResult(
                    name="quality_score",
                    value=77,
                )
            }
        )

        self.assertEqual(result.institutional_bounce_score, 77.0)


if __name__ == "__main__":
    unittest.main()
