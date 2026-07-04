import pytest

from services.strategy_validation_analytics_service import (
    StrategyValidationAnalyticsService,
)


class FakeRepository:
    def __init__(self, rows=None):
        self.rows = rows or []

    def get_samples_by_date_range(self, run_id=None):
        if run_id is None:
            return list(self.rows)
        return [row for row in self.rows if row.get("run_id") == run_id]


def row(
    ticker,
    bucket,
    return_20d,
    outcome="win",
    sector=None,
    return_5d=None,
    return_10d=None,
    return_60d=None,
    max_gain=0,
    max_drawdown=0,
):
    return {
        "ticker": ticker,
        "score_bucket": bucket,
        "return_5d": return_5d if return_5d is not None else return_20d,
        "return_10d": return_10d if return_10d is not None else return_20d,
        "return_20d": return_20d,
        "return_60d": return_60d,
        "max_gain": max_gain,
        "max_drawdown": max_drawdown,
        "outcome": outcome,
        "sector": sector,
    }


def test_empty_repository_returns_empty_report():
    report = StrategyValidationAnalyticsService(FakeRepository()).analyze()

    assert report.overall.total_samples == 0
    assert report.overall.completed_samples == 0
    assert report.overall.win_rate == 0.0
    assert report.forward_returns["20d"].count == 0
    assert report.outcome_distribution == {
        "win": 0,
        "loss": 0,
        "flat": 0,
        "incomplete": 0,
    }


def test_overall_win_rate_averages_expectancy_and_profit_factor():
    rows = [
        row("AAA", "90-100", 10, max_gain=15, max_drawdown=-3),
        row("BBB", "80-89", -5, outcome="loss", max_gain=4, max_drawdown=-8),
        row("CCC", "70-79", 0, outcome="flat", max_gain=2, max_drawdown=-2),
    ]

    report = StrategyValidationAnalyticsService(FakeRepository(rows)).analyze()

    assert report.overall.total_samples == 3
    assert report.overall.completed_samples == 3
    assert report.overall.win_rate == pytest.approx(1 / 3)
    assert report.overall.average_return == pytest.approx(5 / 3)
    assert report.overall.median_return == pytest.approx(0.0)
    assert report.overall.average_drawdown == pytest.approx((-3 - 8 - 2) / 3)
    assert report.overall.average_max_gain == pytest.approx(7.0)
    assert report.overall.expectancy == pytest.approx(5 / 3)
    assert report.overall.profit_factor == pytest.approx(2.0)


def test_forward_return_statistics_by_horizon():
    rows = [
        row("AAA", "90-100", 8, return_5d=2, return_10d=4, return_60d=20),
        row("BBB", "90-100", -4, return_5d=-1, return_10d=-2, return_60d=-10),
    ]

    report = StrategyValidationAnalyticsService(FakeRepository(rows)).analyze()

    assert report.forward_returns["5d"].average == pytest.approx(0.5)
    assert report.forward_returns["10d"].median == pytest.approx(1.0)
    assert report.forward_returns["20d"].best == pytest.approx(8.0)
    assert report.forward_returns["20d"].worst == pytest.approx(-4.0)
    assert report.forward_returns["60d"].std_deviation > 0


def test_score_bucket_summaries():
    rows = [
        row("AAA", "90-100", 10),
        row("BBB", "80-89", -5, outcome="loss"),
        row("CCC", "70-79", 4),
        row("DDD", "below 70", None, outcome="incomplete"),
    ]

    report = StrategyValidationAnalyticsService(FakeRepository(rows)).analyze()

    assert report.score_buckets["90-100"].count == 1
    assert report.score_buckets["90-100"].win_rate == pytest.approx(1.0)
    assert report.score_buckets["80-89"].average_return == pytest.approx(-5.0)
    assert report.score_buckets["below 70"].completed_count == 0


def test_incomplete_samples_are_counted_but_excluded_from_return_stats():
    rows = [
        row("AAA", "90-100", 10),
        row("BBB", "80-89", None, outcome="incomplete"),
    ]

    report = StrategyValidationAnalyticsService(FakeRepository(rows)).analyze()

    assert report.overall.total_samples == 2
    assert report.overall.completed_samples == 1
    assert report.overall.average_return == pytest.approx(10.0)
    assert report.outcome_distribution["incomplete"] == 1


def test_sector_grouping_when_sector_exists():
    rows = [
        row("AAA", "90-100", 10, sector="Technology"),
        row("BBB", "80-89", -4, outcome="loss", sector="Technology"),
        row("CCC", "70-79", 6, sector="Healthcare"),
        row("DDD", "70-79", 3, sector=None),
    ]

    report = StrategyValidationAnalyticsService(FakeRepository(rows)).analyze()

    assert set(report.sector_performance) == {"Healthcare", "Technology"}
    assert report.sector_performance["Technology"].count == 2
    assert report.sector_performance["Technology"].win_rate == pytest.approx(0.5)
    assert report.sector_performance["Healthcare"].average_return == pytest.approx(6.0)


def test_repository_run_filter_is_used():
    rows = [
        {**row("AAA", "90-100", 10), "run_id": "run-a"},
        {**row("BBB", "80-89", -5, outcome="loss"), "run_id": "run-b"},
    ]

    report = StrategyValidationAnalyticsService(FakeRepository(rows)).analyze(
        run_id="run-a"
    )

    assert report.overall.total_samples == 1
    assert report.overall.average_return == pytest.approx(10.0)
