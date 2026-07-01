from analysis.position_size import PositionSizeCalculator
from analysis.score_result import ScoreResult


def base_metrics():
    return {
        "account_size": 100000.0,
        "risk_percent": 1.0,
        "entry_price": 100.0,
        "stop_price": 95.0,
    }


def calculate(metrics):
    return PositionSizeCalculator().calculate(metrics)


def test_standard_calculation():
    result = calculate(base_metrics())

    assert result.shares == 200
    assert result.risk_amount == 1000.0
    assert result.risk_per_share == 5.0
    assert result.position_value == 20000.0
    assert result.capital_used == 20000.0
    assert result.position_percent == 20.0
    assert result.remaining_capital == 80000.0
    assert result.is_valid is True
    assert result.warnings == []


def test_stop_above_entry():
    metrics = base_metrics()
    metrics["stop_price"] = 105.0

    result = calculate(metrics)

    assert result.shares == 0
    assert result.risk_per_share == 0.0
    assert result.is_valid is False
    assert "Stop above entry" in result.warnings


def test_zero_risk():
    metrics = base_metrics()
    metrics["risk_percent"] = 0.0

    result = calculate(metrics)

    assert result.shares == 0
    assert result.is_valid is False
    assert "Risk too small" in result.warnings


def test_account_too_small():
    metrics = base_metrics()
    metrics["account_size"] = 50.0

    result = calculate(metrics)

    assert result.shares == 0
    assert result.is_valid is False
    assert "Risk too small" in result.warnings


def test_maximum_position_percent_limit():
    metrics = base_metrics()
    metrics["maximum_position_percent"] = 10.0

    result = calculate(metrics)

    assert result.shares == 100
    assert result.position_value == 10000.0
    assert result.position_percent == 10.0
    assert "Position limited by maximum position percent" in result.warnings


def test_large_account():
    metrics = base_metrics()
    metrics["account_size"] = 1000000.0

    result = calculate(metrics)

    assert result.shares == 2000
    assert result.position_value == 200000.0
    assert result.remaining_capital == 800000.0
    assert result.is_valid is True


def test_invalid_inputs():
    result = calculate(
        {
            "account_size": None,
            "risk_percent": None,
            "entry_price": -1,
            "stop_price": 0,
        }
    )

    assert result.shares == 0
    assert result.is_valid is False
    assert "Missing inputs" in result.warnings
    assert "Invalid prices" in result.warnings
    assert "Insufficient account size" in result.warnings


def test_deterministic_output():
    metrics = base_metrics()
    metrics["risk_percent"] = ScoreResult("risk_percent", 1.0)

    first = calculate(metrics)
    second = calculate(dict(reversed(list(metrics.items()))))

    assert first == second


def test_warning_generation_for_large_risk_and_account_cap():
    metrics = base_metrics()
    metrics["risk_percent"] = 10.0
    metrics["entry_price"] = 500.0
    metrics["stop_price"] = 490.0

    result = calculate(metrics)

    assert result.shares == 200
    assert result.position_value == 100000.0
    assert "Risk too large" in result.warnings
    assert "Position exceeds account" in result.warnings
