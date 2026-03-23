from app.services.baseline import build_condition_multiplier, score_to_pressure


def test_score_to_pressure():
    assert score_to_pressure(5) == 0
    assert score_to_pressure(1) > 0
    assert score_to_pressure(10) < 0


def test_condition_multiplier_positive():
    weights = {"bath": 0.4, "debris": 0.2, "filtration": 0.3, "overflow": 0.05, "backwash": 0.05}
    result = build_condition_multiplier(weights, bath_score=1, debris_score=1, filtration_score=1, overflow_score=5, backwash_score=5)
    assert result > 1.0
