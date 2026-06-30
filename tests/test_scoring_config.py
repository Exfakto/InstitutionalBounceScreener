import json

from analysis.composite_intelligence import CompositeIntelligenceCalculator
from analysis.composite_score import CompositeScore


def test_scoring_config_separates_legacy_and_gen2_weights():
    with open("config/scoring.json", "r", encoding="utf-8") as file:
        config = json.load(file)

    assert "legacy_weights" in config
    assert "gen2_weights" in config
    assert "weights" not in config
    assert "quality_score" in config["legacy_weights"]
    assert "institutional_momentum_score" in config["gen2_weights"]


def test_score_calculators_load_their_config_sections():
    legacy = CompositeScore()
    gen2 = CompositeIntelligenceCalculator()

    assert legacy.weights == {
        "quality_score": 0.45,
        "institutional_score": 0.35,
        "support_strength_score": 0.10,
        "bounce_validation_score": 0.10,
    }
    assert "institutional_momentum_score" in gen2.weights
