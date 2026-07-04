from types import SimpleNamespace

from services.beta_review_pack_service import BetaReviewPackService
from services.beta_testing_service import CandidateReviewPackService
from services.model_calibration_recommendation_service import CalibrationRecommendationView


class ReviewRepository:
    def fetch_ohlcv(self, ticker):
        return [{"date": "2026-01-01"}] if ticker == "AAPL" else []

    def get_support_levels(self, ticker):
        return [{"zone_low": 95, "zone_high": 100, "strength_score": 82}]

    def get_bounce_validations(self, ticker):
        return [{"successful_bounces": 4, "total_touches": 5, "bounce_success_rate": 80}]

    def get_institutional_data(self, ticker):
        return SimpleNamespace(
            institutional_ownership_pct=70,
            institutional_ownership_change_qoq=2,
        )


def test_candidate_review_pack_generates_top_candidates_with_summaries():
    candidates = [
        {"ticker": "MSFT", "rank": 2, "final_score": 75, "grade": "B", "setup_label": "Watch"},
        {"ticker": "AAPL", "rank": 1, "final_score": 90, "grade": "A", "setup_label": "Elite", "warnings": ["note"]},
    ]

    pack = CandidateReviewPackService(ReviewRepository()).generate(candidates, top_n=1)
    checklist = CandidateReviewPackService.checklist(pack)

    assert len(pack) == 1
    assert pack[0].ticker == "AAPL"
    assert "95" in pack[0].support_zone_summary
    assert "4/5" in pack[0].bounce_history_summary
    assert "Ownership 70" in pack[0].institutional_summary
    assert pack[0].chart_data_available is True
    assert checklist[0].ticker == "AAPL"
    assert checklist[0].decision == ""


def test_candidate_review_pack_missing_data_is_safe():
    pack = CandidateReviewPackService(repository=None).generate(
        [{"ticker": "AAPL", "final_score": None}],
        top_n=1,
    )

    assert pack[0].support_zone_summary == "N/A"
    assert pack[0].chart_data_available is False


def test_beta_review_pack_includes_calibration_recommendations():
    class RecommendationService:
        def get_recommendations(self, run_id=None):
            assert run_id == "cal-1"
            return [
                CalibrationRecommendationView(
                    title="Minimum Final Score",
                    severity="HIGH",
                    recommended_action="75",
                    reason="Lower buckets underperformed",
                    related_metric="minimum_final_score",
                    timestamp="2026-01-01T00:00:00Z",
                )
            ]

    pack = BetaReviewPackService(
        repository=ReviewRepository(),
        calibration_recommendation_service=RecommendationService(),
    ).generate(
        [{"ticker": "AAPL", "rank": 1, "final_score": 90, "grade": "A", "setup_label": "Elite"}],
        top_n=1,
        calibration_run_id="cal-1",
    )

    assert pack.candidates[0].ticker == "AAPL"
    assert pack.calibration_recommendations == [
        {
            "title": "Minimum Final Score",
            "severity": "HIGH",
            "recommended_action": "75",
            "reason": "Lower buckets underperformed",
            "related_metric": "minimum_final_score",
            "timestamp": "2026-01-01T00:00:00Z",
        }
    ]


def test_beta_review_pack_empty_calibration_recommendations():
    class EmptyRecommendationService:
        def get_recommendations(self, run_id=None):
            return []

    pack = BetaReviewPackService(
        repository=None,
        calibration_recommendation_service=EmptyRecommendationService(),
    ).generate(
        [{"ticker": "AAPL", "final_score": 80}],
        top_n=1,
    )

    assert pack.calibration_recommendations == []
