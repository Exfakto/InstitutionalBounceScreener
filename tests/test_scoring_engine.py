import unittest

from analysis import BaseScore, ScoreResult, ScoringEngine


class TestScoreProvider(BaseScore):

    name = "test_score"

    def calculate(self, context):
        return ScoreResult(
            name=self.name,
            value=context["value"],
        )


class FailingScoreProvider(BaseScore):

    name = "failing_score"

    def calculate(self, context):
        raise RuntimeError("planned failure")


class InvalidScoreProvider(BaseScore):

    name = "invalid_score"

    def calculate(self, context):
        return 50


class ScoringEngineTest(unittest.TestCase):

    def test_register_requires_base_score_provider(self):
        engine = ScoringEngine(providers=[])

        with self.assertRaises(TypeError):
            engine.register(object())

    def test_execute_returns_score_results(self):
        engine = ScoringEngine(providers=[TestScoreProvider()])

        results = engine.execute({"value": 88.0})

        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], ScoreResult)
        self.assertEqual(results[0].name, "test_score")
        self.assertEqual(results[0].value, 88.0)

    def test_execute_returns_failure_result_when_provider_fails(self):
        engine = ScoringEngine(
            providers=[
                FailingScoreProvider(),
                TestScoreProvider(),
            ]
        )

        results = engine.execute({"value": 91.0})

        self.assertEqual(len(results), 2)
        self.assertTrue(results[0].failed)
        self.assertEqual(results[1].value, 91.0)

    def test_execute_requires_score_result(self):
        engine = ScoringEngine(providers=[InvalidScoreProvider()])

        with self.assertRaises(TypeError):
            engine.execute({})

    def test_discover_providers_finds_composite_score(self):
        providers = ScoringEngine.discover_providers()
        names = {provider.name for provider in providers}

        self.assertIn("composite_score", names)


if __name__ == "__main__":
    unittest.main()
