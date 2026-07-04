import pytest

from services.score_calibration_service import ScoreCalibrationService


class FakeRepository:
    def __init__(self, rows=None):
        self.rows = rows or []

    def get_samples_by_date_range(self, run_id=None):
        if run_id is None:
            return list(self.rows)
        return [row for row in self.rows if row.get("run_id") == run_id]


def row(
    ticker,
    overall,
    quality,
    institutional,
    technical,
    support,
    bounce,
    return_20d,
    max_drawdown=-2,
    run_id=None,
):
    return {
        "ticker": ticker,
        "score": overall,
        "quality_score": quality,
        "institutional_score": institutional,
        "technical_score": technical,
        "support_score": support,
        "bounce_score": bounce,
        "return_5d": return_20d / 4,
        "return_10d": return_20d / 2,
        "return_20d": return_20d,
        "return_60d": return_20d * 1.5,
        "max_drawdown": max_drawdown,
        "max_gain": max(return_20d, 0),
        "outcome": "win" if return_20d > 0 else "loss",
        "run_id": run_id,
    }


def test_empty_data_returns_neutral_report():
    report = ScoreCalibrationService(FakeRepository()).calibrate()

    assert report.sample_count == 0
    assert set(report.metrics) == {
        "overall_score",
        "quality_score",
        "institutional_score",
        "technical_score",
        "support_score",
        "bounce_score",
    }
    assert all(metric.sample_count == 0 for metric in report.metrics.values())
    assert all(
        recommendation.action == "keep current weight"
        for recommendation in report.recommendations
    )


def test_correlation_calculation_for_predictive_component():
    rows = [
        row("AAA", 95, 95, 50, 50, 50, 50, 20),
        row("BBB", 85, 85, 50, 50, 50, 50, 10),
        row("CCC", 75, 75, 50, 50, 50, 50, 0),
        row("DDD", 65, 65, 50, 50, 50, 50, -10),
    ]

    report = ScoreCalibrationService(FakeRepository(rows)).calibrate()

    assert report.metrics["quality_score"].correlations["20d"] == pytest.approx(1.0)
    assert report.metrics["institutional_score"].correlations["20d"] == pytest.approx(0.0)


def test_bucket_calculations_for_component_scores():
    rows = [
        row("AAA", 95, 95, 50, 50, 50, 50, 20, max_drawdown=-3),
        row("BBB", 85, 85, 50, 50, 50, 50, -10, max_drawdown=-7),
        row("CCC", 75, 75, 50, 50, 50, 50, 5, max_drawdown=-4),
        row("DDD", 65, 65, 50, 50, 50, 50, -5, max_drawdown=-8),
    ]

    metric = ScoreCalibrationService(FakeRepository(rows)).calibrate().metrics["quality_score"]

    assert metric.bucket_summaries["90-100"].count == 1
    assert metric.bucket_summaries["90-100"].win_rate == pytest.approx(1.0)
    assert metric.bucket_summaries["80-89"].average_return == pytest.approx(-10.0)
    assert metric.bucket_summaries["below 70"].drawdown == pytest.approx(-8.0)


def test_feature_ranking_orders_by_predictive_power():
    rows = [
        row("AAA", 95, 95, 10, 60, 60, 60, 20),
        row("BBB", 85, 85, 20, 60, 60, 60, 10),
        row("CCC", 75, 75, 30, 60, 60, 60, 0),
        row("DDD", 65, 65, 40, 60, 60, 60, -10),
    ]

    ranked = ScoreCalibrationService(FakeRepository(rows)).calibrate().ranked_components

    assert ranked[0].component in {"overall_score", "quality_score", "institutional_score"}
    assert ranked[0].predictive_power == pytest.approx(1.0)
    assert ranked[0].rank == 1


def test_recommendation_generation():
    rows = [
        row("AAA", 95, 95, 50, 50, 50, 50, 20),
        row("BBB", 85, 85, 50, 50, 50, 50, 10),
        row("CCC", 75, 75, 50, 50, 50, 50, 0),
        row("DDD", 65, 65, 50, 50, 50, 50, -10),
    ]

    report = ScoreCalibrationService(FakeRepository(rows)).calibrate()
    recommendations = {
        recommendation.component: recommendation
        for recommendation in report.recommendations
    }

    assert recommendations["quality_score"].action == "increase weight"
    assert recommendations["institutional_score"].action == "decrease weight"


def test_run_filter_uses_repository_samples():
    rows = [
        row("AAA", 95, 95, 50, 50, 50, 50, 20, run_id="run-a"),
        row("BBB", 65, 65, 50, 50, 50, 50, -10, run_id="run-b"),
    ]

    report = ScoreCalibrationService(FakeRepository(rows)).calibrate(run_id="run-a")

    assert report.sample_count == 1
    assert report.metrics["quality_score"].sample_count == 1
