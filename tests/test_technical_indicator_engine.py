from types import SimpleNamespace

from services.technical_indicator_engine import (
    TechnicalIndicatorEngine,
    TechnicalIndicatorResult,
)


def price_rows(count=220, start=100.0):
    rows = []
    for index in range(count):
        close = start + index * 0.5
        rows.append(
            {
                "ticker": "TST",
                "date": f"2026-01-{index + 1:03d}",
                "open": close - 0.25,
                "high": close + 1.0,
                "low": close - 1.0,
                "close": close,
                "volume": 1_000_000 + index * 1_000,
            }
        )
    return rows


def assert_close(actual, expected, tolerance=1e-9):
    assert actual is not None
    assert abs(actual - expected) <= tolerance


def test_technical_indicator_engine_calculates_normal_indicators():
    rows = price_rows()
    result = TechnicalIndicatorEngine().calculate(rows)

    assert isinstance(result, TechnicalIndicatorResult)
    assert result.ticker == "TST"
    assert result.close == rows[-1]["close"]
    assert result.ema20 is not None
    assert result.ema50 is not None
    assert result.ema200 is not None
    assert result.rsi14 == 100.0
    assert result.macd is not None
    assert result.macd_signal is not None
    assert result.macd_histogram is not None
    assert result.atr14 == 2.0
    assert result.vwap is not None
    assert result.average_volume_20 == sum(row["volume"] for row in rows[-20:]) / 20
    assert_close(result.relative_volume, rows[-1]["volume"] / result.average_volume_20)
    assert_close(result.distance_from_ema20, ((result.close - result.ema20) / result.ema20) * 100)
    assert_close(result.distance_from_ema50, ((result.close - result.ema50) / result.ema50) * 100)
    assert_close(result.distance_from_ema200, ((result.close - result.ema200) / result.ema200) * 100)
    assert result.warnings == []


def test_technical_indicator_engine_handles_missing_history():
    result = TechnicalIndicatorEngine().calculate([], ticker="EMPTY")

    assert result.ticker == "EMPTY"
    assert result.close is None
    assert result.ema20 is None
    assert result.warnings == ["Missing price history"]


def test_technical_indicator_engine_handles_insufficient_history():
    rows = price_rows(count=10)
    result = TechnicalIndicatorEngine().calculate(rows)

    assert result.close == rows[-1]["close"]
    assert result.ema20 is None
    assert result.ema50 is None
    assert result.ema200 is None
    assert result.rsi14 is None
    assert result.macd is None
    assert result.atr14 is None
    assert result.average_volume_20 is None
    assert result.relative_volume is None


def test_technical_indicator_engine_skips_nan_and_bad_rows():
    rows = price_rows(count=30)
    rows.insert(
        5,
        {
            "date": "2026-01-005-bad",
            "high": float("nan"),
            "low": 10,
            "close": 10,
            "volume": 1_000,
        },
    )
    rows.insert(8, {"date": "2026-01-008-bad", "high": 10, "low": 9, "volume": 1_000})

    result = TechnicalIndicatorEngine().calculate(rows)

    assert result.close == rows[-1]["close"]
    assert result.ema20 is not None
    assert len(result.warnings) == 2
    assert "Skipped row" in result.warnings[0]


def test_technical_indicator_engine_handles_zero_volume_vwap():
    rows = price_rows(count=30)
    for row in rows:
        row["volume"] = 0

    result = TechnicalIndicatorEngine().calculate(rows)

    assert result.vwap is None
    assert result.average_volume_20 == 0
    assert result.relative_volume is None


def test_technical_indicator_engine_accepts_object_rows_and_sorts_dates():
    rows = [
        SimpleNamespace(date="2026-01-03", high=12, low=10, close=11, volume=300),
        SimpleNamespace(date="2026-01-01", high=10, low=8, close=9, volume=100),
        SimpleNamespace(date="2026-01-02", high=11, low=9, close=10, volume=200),
    ]

    result = TechnicalIndicatorEngine().calculate(rows, ticker="OBJ")

    assert result.ticker == "OBJ"
    assert result.date == "2026-01-03"
    assert result.close == 11
    assert result.vwap is not None


def test_technical_indicator_engine_flat_rsi_is_neutral():
    rows = price_rows(count=20, start=50)
    for row in rows:
        row["open"] = 50
        row["high"] = 51
        row["low"] = 49
        row["close"] = 50

    result = TechnicalIndicatorEngine().calculate(rows)

    assert result.rsi14 == 50.0
