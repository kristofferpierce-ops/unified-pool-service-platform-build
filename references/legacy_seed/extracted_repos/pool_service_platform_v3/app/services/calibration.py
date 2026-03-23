from __future__ import annotations

from collections import defaultdict

from sqlmodel import Session, select

from app.models.tables import CalibrationAdjustment, ChemicalUsageLog, EstimateRun, ServiceLog
from app.utils.serialization import loads


def compare_estimate_to_actual(session: Session, property_id: int, vessel_id: int | None = None) -> dict:
    estimate = session.exec(
        select(EstimateRun).where(EstimateRun.property_id == property_id).order_by(EstimateRun.run_timestamp.desc())
    ).first()
    if not estimate:
        return {"estimate_found": False, "chemical_variance": [], "labor_variance": {}}

    output = loads(estimate.output_snapshot_json, {})
    predicted_chemicals = output.get("chemical_quantities", {})
    actual_chemicals = defaultdict(float)
    chemical_logs = session.exec(select(ChemicalUsageLog).where(ChemicalUsageLog.property_id == property_id)).all()
    for log in chemical_logs:
        actual_chemicals[log.chemical_name] += log.quantity

    rows = []
    for chemical, predicted in predicted_chemicals.items():
        predicted_annual = predicted.get("annual_quantity", 0.0)
        actual = actual_chemicals.get(chemical, 0.0)
        variance = actual - predicted_annual
        variance_pct = (variance / predicted_annual * 100.0) if predicted_annual else 0.0
        suggested_multiplier = (actual / predicted_annual) if predicted_annual and actual > 0 else 1.0
        rows.append({
            "chemical": chemical,
            "predicted_annual": predicted_annual,
            "actual_logged": actual,
            "variance": variance,
            "variance_pct": variance_pct,
            "suggested_multiplier": suggested_multiplier,
        })

    predicted_service = output.get("service_costs", {})
    predicted_minutes = predicted_service.get("adjusted_site_minutes", 0.0) + predicted_service.get("adjusted_drive_minutes", 0.0)
    service_logs = list(session.exec(select(ServiceLog).where(ServiceLog.property_id == property_id)).all())
    actual_minutes = sum(log.minutes_on_site_actual + log.drive_minutes_actual for log in service_logs)
    actual_visits = max(1, len(service_logs))
    avg_actual_minutes = actual_minutes / actual_visits if service_logs else 0.0
    labor_variance_pct = ((avg_actual_minutes - predicted_minutes) / predicted_minutes * 100.0) if predicted_minutes else 0.0

    return {
        "estimate_found": True,
        "chemical_variance": rows,
        "labor_variance": {
            "predicted_minutes_per_visit": predicted_minutes,
            "actual_avg_minutes_per_visit": avg_actual_minutes,
            "variance_pct": labor_variance_pct,
            "suggested_labor_multiplier": (avg_actual_minutes / predicted_minutes) if predicted_minutes and avg_actual_minutes else 1.0,
        },
    }


def save_suggested_calibration(session: Session, model_family: str, property_id: int | None, vessel_id: int | None,
                              chemical_name: str, chemical_multiplier: float, labor_multiplier: float = 1.0,
                              notes: str = "") -> CalibrationAdjustment:
    adjustment = CalibrationAdjustment(
        model_family=model_family,
        property_id=property_id,
        vessel_id=vessel_id,
        chemical_name=chemical_name,
        chemical_multiplier=chemical_multiplier,
        labor_multiplier=labor_multiplier,
        source="suggested",
        notes=notes,
    )
    session.add(adjustment)
    session.commit()
    session.refresh(adjustment)
    return adjustment


def account_calibration_map(session: Session, property_id: int | None) -> dict[str, float]:
    rows = list(session.exec(select(CalibrationAdjustment).where(CalibrationAdjustment.property_id == property_id)).all())
    output = {}
    for row in rows:
        if row.chemical_name:
            output[row.chemical_name] = row.chemical_multiplier
    return output
