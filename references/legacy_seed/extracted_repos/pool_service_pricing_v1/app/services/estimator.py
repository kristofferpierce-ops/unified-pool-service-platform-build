from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from sqlmodel import Session, select

from app.models.tables import (
    BaselineModelVersion,
    ChemicalCatalog,
    CompanyExpense,
    EstimateRun,
    Property,
    SystemSetting,
)
from app.services.repositories import get_model_coefficients, get_model_weights


@dataclass
class EstimateInputs:
    property_id: int
    model_version_id: int
    scenario_name: str
    pool_gallons: float
    visits_per_month: float
    minutes_on_site: float
    drive_minutes_round_trip: float
    techs_on_visit: int
    bath_score: int
    debris_score: int
    filtration_score: int
    overflow_score: int
    annual_backwash_gallons: float
    global_adjustment_pct: float
    target_margin_pct: float
    notes: str = ""


def score_to_pressure(score: int) -> float:
    score = max(1, min(10, int(score)))
    return (5 - score) / 5.0


def liquid_event_factor(annual_backwash_gallons: float, pool_gallons: float) -> float:
    if pool_gallons <= 0:
        return 0.0
    turnover_fraction = annual_backwash_gallons / pool_gallons
    return min(1.5, turnover_fraction)


def build_chemical_multiplier(
    weights: dict[str, float],
    bath_score: int,
    debris_score: int,
    filtration_score: int,
    overflow_score: int,
    annual_backwash_gallons: float,
    pool_gallons: float,
) -> float:
    bath_pressure = score_to_pressure(bath_score)
    debris_pressure = score_to_pressure(debris_score)
    filtration_pressure = score_to_pressure(filtration_score)
    overflow_pressure = score_to_pressure(overflow_score)
    backwash_pressure = liquid_event_factor(annual_backwash_gallons, pool_gallons)

    weighted_effect = (
        bath_pressure * weights.get("bath", 0.0)
        + debris_pressure * weights.get("debris", 0.0)
        + filtration_pressure * weights.get("filtration", 0.0)
        + overflow_pressure * weights.get("overflow", 0.0)
        + backwash_pressure * weights.get("backwash", 0.0)
    )
    return max(0.30, 1.0 + weighted_effect)


def get_system_settings(session: Session) -> dict[str, float]:
    rows = session.exec(select(SystemSetting)).all()
    return {row.key: float(row.value) for row in rows}


def get_company_expenses_total(session: Session) -> float:
    rows = session.exec(select(CompanyExpense)).all()
    return float(sum(row.annual_cost for row in rows))


def get_chemical_unit_costs(session: Session) -> dict[str, dict[str, Any]]:
    rows = session.exec(select(ChemicalCatalog).where(ChemicalCatalog.active == True)).all()  # noqa: E712
    return {
        row.key: {"display_name": row.display_name, "unit_name": row.unit_name, "unit_cost": row.default_unit_cost}
        for row in rows
    }


def calculate_burdened_labor_rate(settings: dict[str, float]) -> float:
    return settings["tech_hourly_wage"] * (
        1.0 + settings["payroll_tax_burden_pct"] / 100.0 + settings["benefits_burden_pct"] / 100.0
    )


def calculate_overhead_per_hour(settings: dict[str, float], annual_overhead: float) -> float:
    total_billable_hours = max(1.0, settings["billable_hours_per_tech_per_year"] * settings["number_of_route_techs"])
    return annual_overhead / total_billable_hours


def service_time_multiplier(bath_score: int, debris_score: int, filtration_score: int) -> float:
    weighted = (
        score_to_pressure(bath_score) * 0.20
        + score_to_pressure(debris_score) * 0.35
        + score_to_pressure(filtration_score) * 0.45
    )
    return max(0.55, 1.0 + weighted)


def run_estimate(session: Session, inputs: EstimateInputs) -> dict[str, Any]:
    settings = get_system_settings(session)
    annual_overhead = get_company_expenses_total(session)
    burdened_labor_rate = calculate_burdened_labor_rate(settings)
    overhead_per_hour = calculate_overhead_per_hour(settings, annual_overhead)
    coefficients = get_model_coefficients(session, inputs.model_version_id)
    weights = get_model_weights(session, inputs.model_version_id)
    chemical_costs = get_chemical_unit_costs(session)

    global_factor = 1.0 + inputs.global_adjustment_pct / 100.0
    chemical_results: list[dict[str, Any]] = []

    for chemical_key, base_coeff in coefficients.items():
        chem_weights = weights.get(chemical_key, {})
        multiplier = build_chemical_multiplier(
            weights=chem_weights,
            bath_score=inputs.bath_score,
            debris_score=inputs.debris_score,
            filtration_score=inputs.filtration_score,
            overflow_score=inputs.overflow_score,
            annual_backwash_gallons=inputs.annual_backwash_gallons,
            pool_gallons=inputs.pool_gallons,
        )
        annual_qty = inputs.pool_gallons * base_coeff * multiplier * global_factor
        monthly_qty = annual_qty / 12.0
        cost_meta = chemical_costs.get(chemical_key, {"display_name": chemical_key, "unit_name": "unit", "unit_cost": 0.0})
        annual_cost = annual_qty * float(cost_meta["unit_cost"])
        monthly_cost = annual_cost / 12.0
        chemical_results.append(
            {
                "chemical_key": chemical_key,
                "display_name": cost_meta["display_name"],
                "unit_name": cost_meta["unit_name"],
                "base_coefficient": base_coeff,
                "condition_multiplier": multiplier,
                "annual_quantity": annual_qty,
                "monthly_quantity": monthly_qty,
                "effective_coefficient": annual_qty / inputs.pool_gallons if inputs.pool_gallons else 0.0,
                "unit_cost": float(cost_meta["unit_cost"]),
                "annual_cost": annual_cost,
                "monthly_cost": monthly_cost,
            }
        )

    chemistry_annual_cost = sum(item["annual_cost"] for item in chemical_results)
    chemistry_monthly_cost = chemistry_annual_cost / 12.0

    time_mult = service_time_multiplier(inputs.bath_score, inputs.debris_score, inputs.filtration_score)
    adjusted_site_minutes = inputs.minutes_on_site * time_mult
    total_minutes_per_visit = adjusted_site_minutes + inputs.drive_minutes_round_trip
    hours_per_visit = (total_minutes_per_visit / 60.0) * inputs.techs_on_visit

    direct_labor_cost_per_visit = hours_per_visit * burdened_labor_rate
    overhead_cost_per_visit = hours_per_visit * overhead_per_hour
    service_cost_per_visit = direct_labor_cost_per_visit + overhead_cost_per_visit
    monthly_service_cost = service_cost_per_visit * inputs.visits_per_month
    annual_service_cost = monthly_service_cost * 12.0

    monthly_real_cost = chemistry_monthly_cost + monthly_service_cost
    annual_real_cost = monthly_real_cost * 12.0
    monthly_sell_price = monthly_real_cost / max(0.01, 1.0 - inputs.target_margin_pct / 100.0)
    annual_sell_price = monthly_sell_price * 12.0
    visit_sell_price = monthly_sell_price / max(1.0, inputs.visits_per_month)

    output = {
        "summary": {
            "chemistry_monthly_cost": chemistry_monthly_cost,
            "chemistry_annual_cost": chemistry_annual_cost,
            "monthly_service_cost": monthly_service_cost,
            "annual_service_cost": annual_service_cost,
            "monthly_real_cost": monthly_real_cost,
            "annual_real_cost": annual_real_cost,
            "monthly_sell_price": monthly_sell_price,
            "annual_sell_price": annual_sell_price,
            "visit_sell_price": visit_sell_price,
            "adjusted_site_minutes": adjusted_site_minutes,
            "hours_per_visit": hours_per_visit,
            "burdened_labor_rate": burdened_labor_rate,
            "overhead_per_hour": overhead_per_hour,
        },
        "chemicals": chemical_results,
        "calculation_inputs": inputs.__dict__,
    }
    return output


def save_estimate_run(session: Session, inputs: EstimateInputs, output: dict[str, Any]) -> EstimateRun:
    row = EstimateRun(
        property_id=inputs.property_id,
        model_version_id=inputs.model_version_id,
        scenario_name=inputs.scenario_name,
        input_snapshot=inputs.__dict__,
        output_snapshot=output,
        notes=inputs.notes,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row
