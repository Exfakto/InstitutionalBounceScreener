from analysis.pipeline import AnalysisPipeline


class ScoringController:
    """
    Controller responsible for screener scoring actions.
    """

    def __init__(self):
        self.pipeline = AnalysisPipeline()

    def run_screener(self):
        """
        Run the analysis pipeline.
        """

        return self.pipeline.run()

    def get_candidate_detail(self, ticker):
        """
        Return read-only candidate detail data.
        """

        return self.pipeline.scoring_service.get_candidate_detail(ticker)

    def close(self):
        self.pipeline.close()
