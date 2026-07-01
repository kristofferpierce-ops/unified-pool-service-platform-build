"""Expected-vs-actual variance engine (labor-time dimension).

The core forensic loop: what we EXPECTED a visit to take (the vessel's priced
minutes_on_site) vs what it ACTUALLY took (Skimmer's logged minutes). Overruns
are silent margin erosion -- a visit priced at 25 minutes that always takes 50
is unprofitable even at a "good" bill rate.

Rolls variance up per property (and flags chronic overruns), valued at the true
$/hour so minutes become dollars. Chemical- and margin-variance are the next
dimensions; this establishes the pattern.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlmodel import Session, select

from datetime import date

from app.models.ops_tables import ActualChemicalFact, ActualLaborFact, ServiceVisit
from app.models.tables import Account, ChemicalProduct, PoolVessel, Property
from app.services.cost_of_business import compute_cost_of_business
from app.services.estimator import EstimateInput, calculate_estimate
from app.services.expenses import latest_unit_cost
from app.services.profitability import in_range

OVERRUN_MINUTES = 5.0    # average labor overrun beyond this flags a property
CHEM_OVERRUN_PCT = 20.0  # average chemical cost this % over expected flags a property


@dataclass
class VisitVariance:
    visit_id: int
    date: str
    property_id: int
    property_name: str
    expected_minutes: float
    actual_minutes: float
    variance_minutes: float
    variance_cost: float


@dataclass
class PropertyVariance:
    property_id: int
    name: str
    visits: int
    avg_expected: float
    avg_actual: float
    total_variance_minutes: float
    total_variance_cost: float
    overrun: bool


@dataclass
class VarianceSummary:
    cost_per_hour: float
    visits_analyzed: int
    total_variance_minutes: float
    total_variance_cost: float
    properties: list = field(default_factory=list)   # list[PropertyVariance], worst overruns first
    overruns: list = field(default_factory=list)
    visit_rows: list = field(default_factory=list)    # list[VisitVariance]


def _primary_vessel_minutes(session: Session) -> dict[int, float]:
    """property_id -> priced minutes_on_site of its first vessel."""
    out: dict[int, float] = {}
    for v in session.exec(select(PoolVessel)).all():
        out.setdefault(v.property_id, v.minutes_on_site)
    return out


def labor_variance(session: Session, start: date | None = None, end: date | None = None) -> VarianceSummary:
    cost_per_hour = compute_cost_of_business(session).true_cost_per_hour
    expected_minutes = _primary_vessel_minutes(session)
    property_name = {p.id: p.name for p in session.exec(select(Property)).all()}
    labor = {l.service_visit_id: l for l in session.exec(select(ActualLaborFact)).all()}

    visit_rows: list[VisitVariance] = []
    per_prop: dict[int, dict] = {}
    for visit in session.exec(select(ServiceVisit)).all():
        if not in_range(visit.occurred_at.date() if visit.occurred_at else None, start, end):
            continue
        lab = labor.get(visit.id)
        if lab is None or visit.property_id not in expected_minutes:
            continue
        exp = expected_minutes[visit.property_id]
        act = lab.total_minutes
        var_min = act - exp
        var_cost = (var_min / 60.0) * cost_per_hour
        visit_rows.append(VisitVariance(
            visit_id=visit.id, date=visit.occurred_at.date().isoformat(),
            property_id=visit.property_id, property_name=property_name.get(visit.property_id, f'#{visit.property_id}'),
            expected_minutes=exp, actual_minutes=act, variance_minutes=var_min, variance_cost=var_cost,
        ))
        d = per_prop.setdefault(visit.property_id, {'exp': 0.0, 'act': 0.0, 'n': 0, 'var_min': 0.0, 'var_cost': 0.0})
        d['exp'] += exp
        d['act'] += act
        d['n'] += 1
        d['var_min'] += var_min
        d['var_cost'] += var_cost

    properties: list[PropertyVariance] = []
    for pid, d in per_prop.items():
        n = d['n']
        avg_exp = d['exp'] / n
        avg_act = d['act'] / n
        properties.append(PropertyVariance(
            property_id=pid, name=property_name.get(pid, f'#{pid}'), visits=n,
            avg_expected=avg_exp, avg_actual=avg_act,
            total_variance_minutes=d['var_min'], total_variance_cost=d['var_cost'],
            overrun=(avg_act - avg_exp) >= OVERRUN_MINUTES,
        ))
    properties.sort(key=lambda p: p.total_variance_cost, reverse=True)

    return VarianceSummary(
        cost_per_hour=cost_per_hour,
        visits_analyzed=len(visit_rows),
        total_variance_minutes=sum(v.variance_minutes for v in visit_rows),
        total_variance_cost=sum(v.variance_cost for v in visit_rows),
        properties=properties,
        overruns=[p for p in properties if p.overrun],
        visit_rows=sorted(visit_rows, key=lambda v: v.variance_cost, reverse=True),
    )


# ==========================================================================
# Chemical variance: expected chemical cost per visit (deterministic model)
# vs actual chemical cost logged on Skimmer visits.
# ==========================================================================
@dataclass
class ChemVisitVariance:
    visit_id: int
    date: str
    property_id: int
    property_name: str
    expected_cost: float
    actual_cost: float
    variance_cost: float


@dataclass
class ChemPropertyVariance:
    property_id: int
    name: str
    visits: int
    avg_expected: float
    avg_actual: float
    total_variance_cost: float
    overrun: bool


@dataclass
class ChemVarianceSummary:
    visits_analyzed: int
    total_expected: float
    total_actual: float
    total_variance_cost: float
    properties: list = field(default_factory=list)
    overruns: list = field(default_factory=list)
    visit_rows: list = field(default_factory=list)


def _primary_vessel(session: Session) -> dict[int, PoolVessel]:
    out: dict[int, PoolVessel] = {}
    for v in session.exec(select(PoolVessel)).all():
        out.setdefault(v.property_id, v)
    return out


def _expected_chem_cost_per_visit(session: Session, prop: Property, vessel: PoolVessel) -> float | None:
    """Run the deterministic estimator for this vessel and return expected
    chemical cost per visit, or None if it can't be modeled."""
    model_family = prop.account_type if prop.account_type in ('residential', 'commercial') else 'residential'
    visits_per_month = max(1.0, vessel.service_frequency_per_month)
    estimate_input = EstimateInput(
        property_id=prop.id, vessel_id=vessel.id, model_family=model_family,
        gallons=vessel.gallons, visits_per_month=visits_per_month,
        minutes_on_site=vessel.minutes_on_site, drive_minutes_round_trip=prop.drive_minutes_round_trip,
        techs_on_visit=1, bath_score=vessel.bathing_score, debris_score=vessel.debris_score,
        filtration_score=vessel.filtration_score, overflow_score=vessel.overflow_score,
        backwash_score=vessel.backwash_score, target_margin_pct=35.0, global_adjustment_pct=0.0,
    )
    try:
        output = calculate_estimate(session, estimate_input)
    except Exception:
        return None
    return output.monthly_chemical_real_cost / visits_per_month


def chemical_variance(session: Session, start: date | None = None, end: date | None = None) -> ChemVarianceSummary:
    prices = {p.id: latest_unit_cost(session, p) for p in session.exec(select(ChemicalProduct)).all()}
    property_name = {p.id: p.name for p in session.exec(select(Property)).all()}
    properties = {p.id: p for p in session.exec(select(Property)).all()}
    vessels = _primary_vessel(session)

    chem_by_visit: dict[int, list] = {}
    for c in session.exec(select(ActualChemicalFact)).all():
        chem_by_visit.setdefault(c.service_visit_id, []).append(c)

    expected_cache: dict[int, float | None] = {}
    visit_rows: list[ChemVisitVariance] = []
    per_prop: dict[int, dict] = {}
    for visit in session.exec(select(ServiceVisit)).all():
        if not in_range(visit.occurred_at.date() if visit.occurred_at else None, start, end):
            continue
        facts = chem_by_visit.get(visit.id)
        if not facts or visit.property_id not in vessels:
            continue
        if visit.property_id not in expected_cache:
            expected_cache[visit.property_id] = _expected_chem_cost_per_visit(
                session, properties[visit.property_id], vessels[visit.property_id])
        expected = expected_cache[visit.property_id]
        if expected is None:
            continue
        actual = sum(f.quantity * (prices.get(f.chemical_product_id, 0.0) if f.chemical_product_id else 0.0) for f in facts)
        var = actual - expected
        visit_rows.append(ChemVisitVariance(
            visit_id=visit.id, date=visit.occurred_at.date().isoformat(),
            property_id=visit.property_id, property_name=property_name.get(visit.property_id, f'#{visit.property_id}'),
            expected_cost=expected, actual_cost=actual, variance_cost=var,
        ))
        d = per_prop.setdefault(visit.property_id, {'exp': 0.0, 'act': 0.0, 'n': 0, 'var': 0.0})
        d['exp'] += expected
        d['act'] += actual
        d['n'] += 1
        d['var'] += var

    prop_rows: list[ChemPropertyVariance] = []
    for pid, d in per_prop.items():
        n = d['n']
        avg_exp = d['exp'] / n
        avg_act = d['act'] / n
        overrun = avg_exp > 0 and avg_act > avg_exp * (1 + CHEM_OVERRUN_PCT / 100.0)
        prop_rows.append(ChemPropertyVariance(
            property_id=pid, name=property_name.get(pid, f'#{pid}'), visits=n,
            avg_expected=avg_exp, avg_actual=avg_act, total_variance_cost=d['var'], overrun=overrun,
        ))
    prop_rows.sort(key=lambda p: p.total_variance_cost, reverse=True)

    return ChemVarianceSummary(
        visits_analyzed=len(visit_rows),
        total_expected=sum(v.expected_cost for v in visit_rows),
        total_actual=sum(v.actual_cost for v in visit_rows),
        total_variance_cost=sum(v.variance_cost for v in visit_rows),
        properties=prop_rows,
        overruns=[p for p in prop_rows if p.overrun],
        visit_rows=sorted(visit_rows, key=lambda v: v.variance_cost, reverse=True),
    )
