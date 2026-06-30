import unittest

from analysis import CandidateScore, ScoreResult
from analysis.pipeline import AnalysisPipeline


class FakePipelineDatabase:

    def __init__(self, tickers):
        self.tickers = tickers

    def get_all_tickers(self):
        return self.tickers


class FakeScoringService:

    def __init__(self, scores, failing_tickers=None):
        self.db = FakePipelineDatabase(list(scores.keys()))
        self.scores = scores
        self.failing_tickers = set(failing_tickers or [])
        self.closed = False

    def score_candidate(self, ticker):
        if ticker in self.failing_tickers:
            raise RuntimeError("planned failure")

        return CandidateScore(
            ticker=ticker,
            scores=[],
            composite_score=ScoreResult(
                name="composite_score",
                value=self.scores[ticker],
            ),
        )

    def close(self):
        self.closed = True


class AnalysisPipelineTest(unittest.TestCase):

    def test_run_scores_all_tickers_and_sorts_by_composite_descending(self):
        service = FakeScoringService(
            {
                "AAA": 55.0,
                "BBB": 90.0,
                "CCC": 70.0,
            }
        )

        summary = AnalysisPipeline(service).run()

        self.assertEqual(summary["total_tickers"], 3)
        self.assertEqual(summary["processed"], 3)
        self.assertEqual(summary["skipped"], 0)
        self.assertEqual(
            [candidate.ticker for candidate in summary["candidates"]],
            ["BBB", "CCC", "AAA"],
        )
        self.assertGreaterEqual(summary["elapsed_seconds"], 0.0)

    def test_run_skips_failed_tickers(self):
        service = FakeScoringService(
            {
                "AAA": 55.0,
                "BBB": 90.0,
            },
            failing_tickers={"AAA"},
        )

        summary = AnalysisPipeline(service).run()

        self.assertEqual(summary["total_tickers"], 2)
        self.assertEqual(summary["processed"], 1)
        self.assertEqual(summary["skipped"], 1)
        self.assertEqual(summary["candidates"][0].ticker, "BBB")

    def test_run_handles_no_tickers(self):
        service = FakeScoringService({})

        summary = AnalysisPipeline(service).run()

        self.assertEqual(summary["total_tickers"], 0)
        self.assertEqual(summary["processed"], 0)
        self.assertEqual(summary["skipped"], 0)
        self.assertEqual(summary["candidates"], [])

    def test_close_closes_scoring_service(self):
        service = FakeScoringService({"AAA": 55.0})
        pipeline = AnalysisPipeline(service)

        pipeline.close()

        self.assertTrue(service.closed)


if __name__ == "__main__":
    unittest.main()
