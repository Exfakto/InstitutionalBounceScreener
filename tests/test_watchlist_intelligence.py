from analysis.watchlist_intelligence import (
    WatchlistIntelligenceAnalyzer,
    WatchlistIntelligenceResult,
)


def strong_items():
    return [
        {
            "ticker": "AAPL",
            "company_name": "Apple Inc.",
            "status": "Ready",
            "opportunity_rating": {"rating_score": 91.0, "rating_label": "Elite Bounce"},
            "overall_score": 89.0,
            "quality_score": 90.0,
            "technical_score": 84.0,
            "institutional_score": 76.0,
            "risk_reward": 2.4,
            "confidence": "Very High",
            "last_price": 100.25,
            "percent_change": 1.2,
            "updated_at": "2026-07-02",
            "warnings": [],
        },
        {
            "ticker": "MSFT",
            "company_name": "Microsoft",
            "status": "Watching",
            "opportunity_rating": {"rating_score": 86.0, "rating_label": "High Probability"},
            "overall_score": 84.0,
            "quality_score": 82.0,
            "technical_score": 80.0,
            "institutional_score": 78.0,
            "risk_reward": 2.1,
            "confidence": "High",
            "updated_at": "2026-07-01",
        },
    ]


def test_empty_watchlist():
    result = WatchlistIntelligenceAnalyzer().analyze([])

    assert isinstance(result, WatchlistIntelligenceResult)
    assert result.total_items == 0
    assert result.ready_count == 0
    assert result.average_opportunity_score is None
    assert result.top_candidates == []
    assert result.weak_candidates == []
    assert result.stale_items == []
    assert result.warning_count == 0
    assert "empty" in result.summary


def test_strong_watchlist_summary():
    result = WatchlistIntelligenceAnalyzer().analyze(strong_items())

    assert result.total_items == 2
    assert result.ready_count == 1
    assert result.watching_count == 1
    assert result.rejected_count == 0
    assert result.high_conviction_count == 2
    assert result.average_opportunity_score == 88.5
    assert result.top_candidates[0]["ticker"] == "AAPL"
    assert result.top_candidates[0]["opportunity_score"] == 91.0
    assert result.weak_candidates == []
    assert "average opportunity score 88.5" in result.summary


def test_weak_watchlist_summary():
    items = [
        {
            "ticker": "TSLA",
            "status": "Watching",
            "opportunity_rating": {"rating_score": 42.0},
            "overall_score": 45.0,
            "confidence": "Low",
        },
        {
            "ticker": "NFLX",
            "status": "Rejected",
            "opportunity_rating": {"rating_score": 38.0},
            "technical_score": 35.0,
        },
    ]

    result = WatchlistIntelligenceAnalyzer().analyze(items)

    assert result.total_items == 2
    assert result.rejected_count == 1
    assert result.high_conviction_count == 0
    assert result.average_opportunity_score == 40.0
    assert [item["ticker"] for item in result.weak_candidates] == ["NFLX", "TSLA"]
    assert result.top_candidates[0]["ticker"] == "TSLA"


def test_mixed_statuses_are_counted_case_insensitively():
    items = [
        {"ticker": "AAPL", "status": "ready", "overall_score": 70},
        {"ticker": "MSFT", "status": "Watching", "overall_score": 72},
        {"ticker": "NVDA", "status": "REJECTED", "overall_score": 30},
        {"ticker": "AMZN", "status": "Closed", "overall_score": 68},
    ]

    result = WatchlistIntelligenceAnalyzer().analyze(items)

    assert result.total_items == 4
    assert result.ready_count == 1
    assert result.watching_count == 1
    assert result.rejected_count == 1


def test_stale_items_are_deterministic_from_supplied_dates():
    items = [
        {"ticker": "FRESH", "updated_at": "2026-07-02", "overall_score": 70},
        {"ticker": "OLD", "updated_at": "2026-06-20", "overall_score": 71},
        {"ticker": "OLDER", "updated_at": "2026-06-01", "overall_score": 72},
    ]

    result = WatchlistIntelligenceAnalyzer().analyze(items)

    assert [item["ticker"] for item in result.stale_items] == ["OLDER", "OLD"]
    assert "2 stale item(s)" in result.summary


def test_warning_propagation():
    items = [
        {"ticker": "AAPL", "warnings": ["Review liquidity.", "Review liquidity."]},
        {"ticker": "MSFT", "warnings": "Earnings window is close."},
    ]

    result = WatchlistIntelligenceAnalyzer().analyze(items)

    assert result.warning_count == 2
    assert result.warnings == [
        "AAPL: Review liquidity.",
        "MSFT: Earnings window is close.",
    ]
    assert "2 warning(s)" in result.summary


def test_deterministic_output():
    analyzer = WatchlistIntelligenceAnalyzer()
    items = strong_items()

    first = analyzer.analyze(items)
    second = analyzer.analyze(items)

    assert first == second


def test_missing_values_are_handled_safely():
    items = [
        {"ticker": "AAPL", "status": "Watching"},
        {"company_name": "No Ticker Inc.", "status": None, "warnings": []},
        None,
    ]

    result = WatchlistIntelligenceAnalyzer().analyze(items)

    assert result.total_items == 2
    assert result.watching_count == 1
    assert result.average_opportunity_score is None
    assert result.top_candidates == []
    assert result.weak_candidates == []
    assert "No Ticker" not in result.summary
