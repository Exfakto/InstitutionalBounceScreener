from datetime import date, timedelta

from services.algorithm_validation_service import SignalOutcome, HistoricalSignal


def price_rows(start="2024-01-01", count=120, base=100.0, step=1.0):
    current = date.fromisoformat(start)
    rows = []
    for index in range(count):
        close = base + index * step
        rows.append(
            {
                "date": current.isoformat(),
                "open": close - 0.25,
                "high": close + 1.0,
                "low": close - 1.0,
                "close": close,
                "volume": 1_000_000 + index,
            }
        )
        current += timedelta(days=1)
    return rows


def sample_signal(ticker="AAPL", signal_date="2024-02-01", entry_price=100.0):
    return HistoricalSignal(
        ticker=ticker,
        signal_date=signal_date,
        entry_price=entry_price,
        support_score=82,
        bounce_score=78,
        technical_score=74,
        institutional_score=70,
        final_score=77,
        grade="B",
    )


def sample_outcome(
    ticker="AAPL",
    signal_date="2024-02-01",
    return_20=5.0,
    final_score=77,
    support_score=82,
    bounce_score=78,
    technical_score=74,
    institutional_score=70,
):
    return SignalOutcome(
        ticker=ticker,
        signal_date=signal_date,
        entry_price=100,
        forward_returns={"5": return_20 / 4, "10": return_20 / 2, "20": return_20, "60": return_20 * 2},
        max_gain_pct=max(return_20, 0) + 2,
        max_drawdown_pct=min(return_20, 0) - 2,
        hit_profit_target=return_20 >= 20,
        hit_stop_loss=return_20 <= -8,
        support_score=support_score,
        bounce_score=bounce_score,
        technical_score=technical_score,
        institutional_score=institutional_score,
        final_score=final_score,
        grade="B",
        warnings=[],
    )
