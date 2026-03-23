from __future__ import annotations

from dataclasses import asdict, dataclass

from sqlmodel import Session, select

from app.models.tables import ChemicalProduct, EstimateRun
from app.services.baseline import get_active_model, load_model_payload, estimate_chemical_quantities, score_to_pressure
from app.services.calibration import account_calibration_map
from app.services.expenses import latest_unit_cost, overhead_per_billable_hour
from app.utils.serialization import dumps


@dataclass
class LaborSettings:
    tech_hourly_wage: float = 22.0
    payroll_tax_burden_pct: float = 10.0
    benefits_burden_pct: float = 5.0
    billable_hours_per_tech_per_year: float = 1500.0
    number_of_route_techs: int = 4


@dataclass
class EstimateInput:
    property_id: int
    vessel_id: int | None
    model_family: str
    gallons: float
    visits_per_month: float
    minutes_on_site: float
    drive_minutes_round_trip: float
    techs_on_visit: int
    bath_score: int
    debris_score: int
    filtration_score: int
    overflow_score: int
    backwash_score: int
    target_margin_pct: float
    global_adjustment_pct: float = 0.0


@dataclass
class EstimateOutput:
    chemical_quantities: dict
    chemical_costs: dict
    service_costs: dict
    monthly_real_cost: float
    annual_real_cost: float
    monthly_sell_price: float
    annual_sell_price: float
    visit_sell_price: float


def burdened_labor_rate(settings: LaborSettings) -> float:
    return settings.tech_hourly_wage * (1 + settings.payroll_tax_burden_pct / 100.0 + settings.benefits_burden_pct / 100.0)


def service_time_multiplier(*, bath_score: int, debris_score: int, filtration_score: int, overflow_score: int, backwash_score: int) -> float:
    weighted = (
        score_to_pressure(bath_score) * 0.18
        + score_to_pressure(debris_score) * 0.27
        + score_to_pressure(filtration_score) * 0.33
        + score_to_pressure(overflow_score) * 0.10
        + score_to_pressure(backwash_score) * 0.12
    )
    return max(0.50, 1.0 + weighted)


def calculate_estimate(session: Session, estimate_input: EstimateInput, labor_settings: LaborSettings | None = None) -> EstimateOutput:
    labor_settings = labor_settings or LaborSettings()
    baseline_model = get_active_model(session, estimate_input.model_family)
    model_payload = load_model_payload(baseline_model)
    calibration = account_calibration_map(session, estimate_input.property_id)

    chemical_quantities = estimate_chemical_quantities(
        gallons=estimate_input.gallons,
        model_payload=model_payload,
        bath_score=estimate_input.bath_score,
        debris_score=estimate_input.debris_score,
        filtration_score=estimate_input.filtration_score,
        overflow_score=estimate_input.overflow_score,
        backwash_score=estimate_input.backwash_score,
        global_adjustment_pct=estimate_input.global_adjustment_pct,
        calibration=calibration,
    )

    products = {product.sku.lower().replace("-", "_"): product for product in session.exec(select(ChemicalProduct).where(ChemicalProduct.is_active == True)).all()}
    alias_map = {
        "liquid_chlorine_12pct_gal": "liq_cl_12",
        "muriatic_acid_gal": "muri_acid",
        "sodium_bicarbonate_lb": "sod_bicarb",
        "cyanuric_acid_lb": "cya_gran",
        "calcium_chloride_lb": "cal_chl",
        "algaecide_oz": "algae_poly",
        "phosphate_remover_oz": "phos_rem",
    }

    chemical_costs = {}
    monthly_chemical_cost = 0.0
    annual_chemical_cost = 0.0
    for chemical_name, values in chemical_quantities.items():
        lookup_key = alias_map.get(chemical_name, chemical_name)
        product = products.get(lookup_key)
        unit_cost = latest_unit_cost(session, product) if product else 0.0
        unit = product.unit if product else ""
        annual_cost = values["annual_quantity"] * unit_cost
        monthly_cost = annual_cost / 12.0
        monthly_chemical_cost += monthly_cost
        annual_chemical_cost += annual_cost
        chemical_costs[chemical_name] = {
            "unit_cost": unit_cost,
            "unit": unit,
            "annual_cost": annual_cost,
            "monthly_cost": monthly_cost,
        }

    multiplier = service_time_multiplier(
        bath_score=estimate_input.bath_score,
        debris_score=estimate_input.debris_score,
        filtration_score=estimate_input.filtration_score,
        overflow_score=estimate_input.overflow_score,
        backwash_score=estimate_input.backwash_score,
    )
    adjusted_site_minutes = estimate_input.minutes_on_site * multiplier
    adjusted_drive_minutes = estimate_input.drive_minutes_round_trip
    total_hours_per_visit = ((adjusted_site_minutes + adjusted_drive_minutes) / 60.0) * estimate_input.techs_on_visit
    direct_labor_rate = burdened_labor_rate(labor_settings)
    overhead_rate = overhead_per_billable_hour(
        session,
        billable_hours_per_year=labor_settings.billable_hours_per_tech_per_year,
        number_of_route_techs=labor_settings.number_of_route_techs,
    )
    direct_labor_cost_per_visit = total_hours_per_visit * direct_labor_rate
    overhead_cost_per_visit = total_hours_per_visit * overhead_rate
    service_costs = {
        "adjusted_site_minutes": adjusted_site_minutes,
        "adjusted_drive_minutes": adjusted_drive_minutes,
        "hours_per_visit": total_hours_per_visit,
        "direct_labor_rate": direct_labor_rate,
        "overhead_rate": overhead_rate,
        "direct_labor_cost_per_visit": direct_labor_cost_per_visit,
        "overhead_cost_per_visit": overhead_cost_per_visit,
        "monthly_service_cost": (direct_labor_cost_per_visit + overhead_cost_per_visit) * estimate_input.visits_per_month,
        "annual_service_cost": (direct_labor_cost_per_visit + overhead_cost_per_visit) * estimate_input.visits_per_month * 12.0,
    }

    monthly_real_cost = monthly_chemical_cost + service_costs["monthly_service_cost"]
    annual_real_cost = annual_chemical_cost + service_costs["annual_service_cost"]
    monthly_sell_price = monthly_real_cost / max(0.01, 1.0 - estimate_input.target_margin_pct / 100.0)
    annual_sell_price = monthly_sell_price * 12.0
    visit_sell_price = monthly_sell_price / max(1.0, estimate_input.visits_per_month)

    return EstimateOutput(
        chemical_quantities=chemical_quantities,
        chemical_costs=chemical_costs,
        service_costs=service_costs,
        monthly_real_cost=monthly_real_cost,
        annual_real_cost=annual_real_cost,
        monthly_sell_price=monthly_sell_price,
        annual_sell_price=annual_sell_price,
        visit_sell_price=visit_sell_price,
    )


def save_estimate_run(session: Session, scenario_id: int, estimate_input: EstimateInput, estimate_output: EstimateOutput) -> EstimateRun:
    record = EstimateRun(
        scenario_id=scenario_id,
        property_id=estimate_input.property_id,
        vessel_id=estimate_input.vessel_id,
        input_snapshot_json=dumps(asdict(estimate_input)),
        output_snapshot_json=dumps(asdict(estimate_output)),
        monthly_real_cost=estimate_output.monthly_real_cost,
        monthly_sell_price=estimate_output.monthly_sell_price,
        annual_real_cost=estimate_output.annual_real_cost,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record
