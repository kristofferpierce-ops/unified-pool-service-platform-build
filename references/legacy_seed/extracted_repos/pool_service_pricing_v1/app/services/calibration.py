from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.models.tables import EstimateRun, FieldObservation


def compare_estimate_to_observations(estimate_run: EstimateRun, observations: list[FieldObservation]) -> dict[str, Any]:
    estimated = estimate_run.output_snapshot or {}
    estimated_chemicals = {item["chemical_key"]: item for item in estimated.get("chemicals", [])}
    estimate_inputs = estimate_run.input_snapshot or {}

    actual_chem_totals: dict[str, float] = defaultdict(float)
    actual_site_minutes = 0.0
    actual_drive_minutes = 0.0

    for obs in observations:
        actual_site_minutes += float(obs.actual_site_minutes or 0.0)
        actual_drive_minutes += float(obs.actual_drive_minutes_round_trip or 0.0)
        for key, value in (obs.actual_chemical_usage or {}).items():
            actual_chem_totals[key] += float(value or 0.0)

    chemical_comparison = []
    for chem_key, item in estimated_chemicals.items():
        estimated_monthly = float(item.get("monthly_quantity", 0.0))
        actual_total = float(actual_chem_totals.get(chem_key, 0.0))
        variance = actual_total - estimated_monthly
        variance_pct = (variance / estimated_monthly * 100.0) if estimated_monthly else 0.0
        chemical_comparison.append(
            {
                "chemical_key": chem_key,
                "display_name": item.get("display_name", chem_key),
                "estimated_monthly_quantity": estimated_monthly,
                "actual_logged_quantity": actual_total,
                "variance_quantity": variance,
                "variance_pct": variance_pct,
            }
        )

    estimated_site_minutes_per_visit = float(estimated.get("summary", {}).get("adjusted_site_minutes", 0.0))
    estimated_drive_minutes_per_visit = float(estimate_inputs.get("drive_minutes_round_trip", 0.0))

    return {
        "chemical_comparison": chemical_comparison,
        "labor_comparison": {
            "estimated_site_minutes_per_visit": estimated_site_minutes_per_visit,
            "estimated_drive_minutes_per_visit": estimated_drive_minutes_per_visit,
            "actual_logged_site_minutes_total": actual_site_minutes,
            "actual_logged_drive_minutes_total": actual_drive_minutes,
            "observation_count": len(observations),
        },
    }
