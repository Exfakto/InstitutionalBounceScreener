import unittest

from controllers.scoring_controller import ScoringController


class FakePipeline:

    def __init__(self):
        self.closed = False
        self.ran = False

    def run(self):
        self.ran = True
        return {"candidates": []}

    def close(self):
        self.closed = True


class FakeScoringService:

    def __init__(self):
        self.detail_ticker = None

    def get_candidate_detail(self, ticker):
        self.detail_ticker = ticker
        return {"ticker": ticker}


class ScoringControllerTest(unittest.TestCase):

    def build_controller(self):
        controller = ScoringController.__new__(ScoringController)
        controller.pipeline = FakePipeline()
        controller.pipeline.scoring_service = FakeScoringService()
        return controller

    def test_run_screener_delegates_to_pipeline(self):
        controller = self.build_controller()

        result = controller.run_screener()

        self.assertTrue(controller.pipeline.ran)
        self.assertEqual(result, {"candidates": []})

    def test_close_closes_pipeline(self):
        controller = self.build_controller()

        controller.close()

        self.assertTrue(controller.pipeline.closed)

    def test_get_candidate_detail_delegates_to_scoring_service(self):
        controller = self.build_controller()

        detail = controller.get_candidate_detail("AAPL")

        self.assertEqual(detail, {"ticker": "AAPL"})
        self.assertEqual(controller.pipeline.scoring_service.detail_ticker, "AAPL")


if __name__ == "__main__":
    unittest.main()
