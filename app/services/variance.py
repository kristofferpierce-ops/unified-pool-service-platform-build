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

from app.models.ops_tables import ActualLaborFact, ServiceVisit
from app.models.tables import Account, PoolVessel, Property
from app.services.cost_of_business import compute_cost_of_business

OVERRUN_MINUTES = 5.0   # average overrun beyond this flags a property


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


def labor_variance(session: Session) -> VarianceSummary:
    cost_per_hour = compute_cost_of_business(session).true_cost_per_hour
    expected_minutes = _primary_vessel_minutes(session)
    property_name = {p.id: p.name for p in session.exec(select(Property)).all()}
    labor = {l.service_visit_id: l for l in session.exec(select(ActualLaborFact)).all()}

    visit_rows: list[VisitVariance] = []
    per_prop: dict[int, dict] = {}
    for visit in session.exec(select(ServiceVisit)).all():
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
