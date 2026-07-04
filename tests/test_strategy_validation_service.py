from types import SimpleNamespace

import pytest

from services.strategy_validation_service import (
    StrategyValidationService,
)


def price_rows(closes, start_day=1, highs=None, lows=None):
    rows = []
    for index, close in enumerate(closes):
        rows.append(
            {
                "date": f"2024-01-{start_day + index:02d}",
                "close": close,
                "high": highs[index] if highs else close,
                "low": lows[index] if lows else close,
            }
        )
    return rows


def candidate(ticker="AAPL", signal_date="2024-01-01", score=85):
    return SimpleNamespace(
        ticker=ticker,
        signal_date=signal_date,
        final_score=score,
    )


def test_forward_return_calculation_for_standard_horizons():
    service = StrategyValidationService()
    prices = price_rows(
        [
            99,
            100,
            101,
            102,
            103,
            104,
            110,
            111,
            112,
            113,
            114,
            120,
            121,
            122,
            123,
            124,
            125,
            126,
            127,
            128,
            129,
            140,
        ],
    )

    sample = service.validate_sample(candidate(), {"AAPL": prices})

    assert sample.entry_date == "2024-01-02"
    assert sample.entry_price == 100
    assert sample.forward_returns[5].return_pct == pytest.approx(10.0)
    assert sample.forward_returns[10].return_pct == pytest.approx(20.0)
    assert sample.forward_returns[20].return_pct == pytest.approx(40.0)
    assert sample.forward_returns[60].complete is False


def test_insufficient_forward_data_marks_sample_incomplete():
    service = StrategyValidationService()
    prices = price_rows([100, 101, 102])

    sample = service.validate_sample(candidate(), {"AAPL": prices})

    assert sample.complete is False
    assert sample.forward_returns[5].complete is False
    assert "Insufficient forward data" in sample.forward_returns[5].warning


def test_max_forward_gain_and_drawdown_use_forward_rows_only():
    service = StrategyValidationService(horizons=(5,), primary_horizon=5)
    prices = price_rows(
        [80, 100, 103, 98, 104, 102, 101],
        highs=[80, 100, 112, 99, 104, 106, 101],
        lows=[70, 100, 101, 90, 97, 96, 94],
    )

    sample = service.validate_sample(candidate(), {"AAPL": prices})

    assert sample.entry_date == "2024-01-02"
    assert sample.max_forward_gain_pct == pytest.approx(12.0)
    assert sample.max_forward_drawdown_pct == pytest.approx(-10.0)


def test_report_win_rate_average_and_median_use_complete_primary_horizon():
    service = StrategyValidationService(horizons=(5,), primary_horizon=5)
    candidates = [
        candidate("AAA", score=95),
        candidate("BBB", score=75),
        candidate("CCC", score=65),
    ]
    prices = {
        "AAA": price_rows([99, 100, 101, 102, 103, 104, 110]),
        "BBB": price_rows([99, 100, 99, 98, 97, 96, 90]),
        "CCC": price_rows([99, 100, 100, 100, 100, 100, 100]),
    }

    report = service.validate(candidates, prices)

    assert report.sample_count == 3
    assert report.completed_count == 3
    assert report.average_return == pytest.approx(0.0)
    assert report.median_return == pytest.approx(0.0)
    assert report.win_rate == pytest.approx(1 / 3)


def test_score_bucket_grouping_uses_primary_horizon_results():
    service = StrategyValidationService(horizons=(5,), primary_horizon=5)
    candidates = [
        candidate("AAA", score=95),
        candidate("BBB", score=85),
        candidate("CCC", score=75),
        candidate("DDD", score=60),
    ]
    prices = {
        ticker: price_rows([99, 100, 101, 102, 103, 104, 110])
        for ticker in ["AAA", "BBB", "CCC", "DDD"]
    }

    report = service.validate(candidates, prices)

    assert report.score_buckets["90-100"].sample_count == 1
    assert report.score_buckets["80-89"].sample_count == 1
    assert report.score_buckets["70-79"].sample_count == 1
    assert report.score_buckets["below 70"].sample_count == 1
    assert report.score_buckets["90-100"].average_return == pytest.approx(10.0)


def test_empty_input_returns_empty_report():
    report = StrategyValidationService().validate([], {})

    assert report.sample_count == 0
    assert report.completed_count == 0
    assert report.average_return == 0.0
    assert report.win_rate == 0.0
    assert all(summary.sample_count == 0 for summary in report.score_buckets.values())


def test_no_lookahead_bias_uses_first_row_after_signal_date():
    service = StrategyValidationService(horizons=(5,), primary_horizon=5)
    prices = price_rows([1000, 100, 100, 100, 100, 100, 110])

    sample = service.validate_sample(candidate(signal_date="2024-01-01"), {"AAPL": prices})

    assert sample.entry_date == "2024-01-02"
    assert sample.entry_price == 100
    assert sample.forward_returns[5].return_pct == pytest.approx(10.0)
