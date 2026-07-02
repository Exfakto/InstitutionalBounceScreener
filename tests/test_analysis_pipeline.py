import unittest

from analysis import CandidateScore, ScoreResult
from analysis.pipeline import AnalysisPipeline


class FakePipelineDatabase:

    def __init__(self, tickers):
        self.tickers = tickers

    def get_all_tickers(self):
        return self.tickers


class FakeScoringService:

    def __init__(self, scores, failing_tickers=None, gen2_scores=None):
        self.db = FakePipelineDatabase(list(scores.keys()))
        self.scores = scores
        self.gen2_scores = gen2_scores or {}
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
            institutional_bounce_score=self.gen2_scores.get(ticker),
            metrics={
                "company_name": f"{ticker} Corp",
                "market_cap": 1000000000,
                "revenue_growth_ttm": 12,
                "eps_growth_ttm": 10,
                "roe": 20,
                "gross_margin": 45,
                "free_cash_flow": 1000000,
                "debt_to_equity": 0.5,
                "current_ratio": 1.8,
            },
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

    def test_run_sorts_by_gen2_score_when_available(self):
        service = FakeScoringService(
            {
                "AAA": 95.0,
                "BBB": 50.0,
                "CCC": 70.0,
            },
            gen2_scores={
                "AAA": 40.0,
                "BBB": 99.0,
            },
        )

        summary = AnalysisPipeline(service).run()

        self.assertEqual(
            [candidate.ticker for candidate in summary["candidates"]],
            ["BBB", "CCC", "AAA"],
        )

    def test_run_falls_back_to_composite_when_gen2_unavailable(self):
        service = FakeScoringService(
            {
                "AAA": 95.0,
                "BBB": 50.0,
            },
            gen2_scores={
                "BBB": 80.0,
            },
        )

        summary = AnalysisPipeline(service).run()

        self.assertEqual(
            [candidate.ticker for candidate in summary["candidates"]],
            ["AAA", "BBB"],
        )

    def test_run_attaches_decision_fields_to_candidates(self):
        service = FakeScoringService(
            {
                "AAA": 85.0,
            },
            gen2_scores={
                "AAA": 90.0,
            },
        )

        summary = AnalysisPipeline(service).run()
        candidate = summary["candidates"][0]

        self.assertIsNotNone(candidate.opportunity_rating)
        self.assertIn(
            candidate.opportunity_rating.rating_label,
            {"Avoid", "Weak Setup", "Watch List", "High Probability", "Elite Bounce"},
        )
        self.assertIsNotNone(candidate.institutional_checklist)
        self.assertEqual(candidate.institutional_checklist.total_checks, 10)
        self.assertIsNotNone(candidate.trade_thesis)
        self.assertIn("AAA", candidate.trade_thesis.title)
        self.assertIsNotNone(candidate.research_report)
        self.assertIn("AAA", candidate.research_report.title)
        self.assertEqual(candidate.metrics["company_name"], "AAA Corp")
        self.assertEqual(
            [
                check.name
                for check in candidate.institutional_checklist.checks
            ][0],
            "Near validated support",
        )

    def test_metrics_for_candidate_includes_live_fundamentals(self):
        candidate = FakeScoringService({"AAA": 85.0}).score_candidate("AAA")

        metrics = AnalysisPipeline.metrics_for_candidate(candidate)

        self.assertEqual(metrics["company_name"], "AAA Corp")
        self.assertEqual(metrics["market_cap"], 1000000000)
        self.assertEqual(metrics["revenue_growth_ttm"], 12)

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
