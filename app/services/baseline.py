from __future__ import annotations

from typing import Any

from sqlmodel import Session, select

from app.models.tables import BaselineModelVersion
from app.utils.serialization import loads


def score_to_pressure(score: int) -> float:
    score = max(1, min(10, int(score)))
    return (5 - score) / 5.0


def get_active_model(session: Session, model_family: str) -> BaselineModelVersion:
    model = session.exec(
        select(BaselineModelVersion)
        .where(BaselineModelVersion.model_family == model_family, BaselineModelVersion.is_active == True)
        .order_by(BaselineModelVersion.id.desc())
    ).first()
    if not model:
        raise ValueError(f"No active baseline model found for {model_family}")
    return model


def load_model_payload(model: BaselineModelVersion) -> dict[str, Any]:
    return {
        "coefficients": loads(model.coefficients_json, {}),
        "weights": loads(model.weights_json, {}),
    }


def build_condition_multiplier(weights: dict[str, float], *, bath_score: int, debris_score: int,
                               filtration_score: int, overflow_score: int, backwash_score: int) -> float:
    pressures = {
        "bath": score_to_pressure(bath_score),
        "debris": score_to_pressure(debris_score),
        "filtration": score_to_pressure(filtration_score),
        "overflow": score_to_pressure(overflow_score),
        "backwash": score_to_pressure(backwash_score),
    }
    weighted = sum(pressures[key] * weights.get(key, 0.0) for key in pressures)
    return max(0.30, 1.0 + weighted)


def estimate_chemical_quantities(*, gallons: float, model_payload: dict[str, Any], bath_score: int, debris_score: int,
                                 filtration_score: int, overflow_score: int, backwash_score: int,
                                 global_adjustment_pct: float, calibration: dict[str, float] | None = None) -> dict[str, dict[str, float]]:
    coefficients = model_payload["coefficients"]
    weights = model_payload["weights"]
    calibration = calibration or {}
    global_factor = 1.0 + (global_adjustment_pct / 100.0)
    output: dict[str, dict[str, float]] = {}
    for chemical, coefficient in coefficients.items():
        chemical_weights = weights.get(chemical, {})
        multiplier = build_condition_multiplier(
            chemical_weights,
            bath_score=bath_score,
            debris_score=debris_score,
            filtration_score=filtration_score,
            overflow_score=overflow_score,
            backwash_score=backwash_score,
        )
        calibration_factor = calibration.get(chemical, 1.0)
        annual_quantity = gallons * coefficient * multiplier * global_factor * calibration_factor
        output[chemical] = {
            "base_coefficient": coefficient,
            "condition_multiplier": multiplier,
            "calibration_factor": calibration_factor,
            "annual_quantity": annual_quantity,
            "monthly_quantity": annual_quantity / 12.0,
            "effective_coefficient": annual_quantity / gallons if gallons else 0.0,
        }
    return output
