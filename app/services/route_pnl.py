"""Route-level profitability: which routes make money, which cost more.

Cost per route is exact (sum of its visits' labor + chemical cost). Revenue is
allocated: each customer's FreshBooks revenue is split evenly across that
customer's service visits, and a visit's share flows to whatever route it's on.
Rolls up by route and by technician.

Revenue allocation is an explicit modeling choice (even split per visit) -- it's
the honest default when invoices are per-customer, not per-visit.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from datetime import date

from sqlmodel import Session, select

from app.models.ops_tables import ActualChemicalFact, ActualLaborFact, BillingDocument, ServiceVisit
from app.models.route_tables import RouteRecord, RouteVisit
from app.models.tables import ChemicalProduct, Property
from app.services.cost_of_business import compute_cost_of_business
from app.services.expenses import latest_unit_cost
from app.services.profitability import in_range


@dataclass
class RoutePnL:
    route_id: int
    name: str
    route_date: str
    technician: str
    visits: int
    revenue: float
    cost: float
    profit: float
    margin_pct: float


@dataclass
class TechPnL:
    technician: str
    routes: int
    visits: int
    revenue: float
    cost: float
    profit: float
    margin_pct: float


@dataclass
class RoutePnLSummary:
    cost_per_hour: float
    routes: list = field(default_factory=list)
    technicians: list = field(default_factory=list)
    unrouted_visits: int = 0
    total_revenue: float = 0.0
    total_cost: float = 0.0
    total_profit: float = 0.0


def _price_map(session: Session) -> dict[int, float]:
    return {p.id: latest_unit_cost(session, p) for p in session.exec(select(ChemicalProduct)).all()}


def _visit_cost_and_account(session: Session, cost_per_hour: float, prices: dict[int, float],
                            start: date | None = None, end: date | None = None):
    """Return {visit_id: (cost, account_id)} for visits performed in [start, end]."""
    property_account = {p.id: p.account_id for p in session.exec(select(Property)).all()}
    labor = {l.service_visit_id: l for l in session.exec(select(ActualLaborFact)).all()}
    chem: dict[int, list] = {}
    for c in session.exec(select(ActualChemicalFact)).all():
        chem.setdefault(c.service_visit_id, []).append(c)

    out: dict[int, tuple[float, int | None]] = {}
    for v in session.exec(select(ServiceVisit)).all():
        if not in_range(v.occurred_at.date() if v.occurred_at else None, start, end):
            continue
        cost = 0.0
        lab = labor.get(v.id)
        if lab:
            cost += (lab.total_minutes / 60.0) * cost_per_hour
        for cf in chem.get(v.id, []):
            unit = prices.get(cf.chemical_product_id, 0.0) if cf.chemical_product_id else 0.0
            cost += cf.quantity * unit
        out[v.id] = (cost, property_account.get(v.property_id))
    return out


def route_pnl(session: Session, start: date | None = None, end: date | None = None) -> RoutePnLSummary:
    """Route + technician P&L, optionally scoped to [start, end] (inclusive)."""
    cost_per_hour = compute_cost_of_business(session).true_cost_per_hour
    prices = _price_map(session)
    visit_info = _visit_cost_and_account(session, cost_per_hour, prices, start, end)

    # Revenue per account (invoices issued in the period), and each account's
    # in-period visit count (for even allocation).
    revenue: dict[int, float] = {}
    for doc in session.exec(select(BillingDocument).where(BillingDocument.source_slug == 'freshbooks')).all():
        if doc.account_id and in_range(doc.issued_on, start, end):
            revenue[doc.account_id] = revenue.get(doc.account_id, 0.0) + doc.total_amount
    acct_visits: dict[int, int] = {}
    for _vid, (_cost, acct) in visit_info.items():
        if acct:
            acct_visits[acct] = acct_visits.get(acct, 0) + 1

    def allocated_revenue(visit_id: int) -> float:
        _cost, acct = visit_info.get(visit_id, (0.0, None))
        if not acct or acct_visits.get(acct, 0) == 0:
            return 0.0
        return revenue.get(acct, 0.0) / acct_visits[acct]

    # Route rollup.
    links: dict[int, list[int]] = {}
    routed_visit_ids: set[int] = set()
    for rv in session.exec(select(RouteVisit)).all():
        links.setdefault(rv.route_id, []).append(rv.service_visit_id)
        routed_visit_ids.add(rv.service_visit_id)

    routes: list[RoutePnL] = []
    tech_acc: dict[str, dict] = {}
    for route in session.exec(select(RouteRecord)).all():
        if not in_range(route.route_date, start, end):
            continue
        visit_ids = links.get(route.id, [])
        cost = sum(visit_info.get(vid, (0.0, None))[0] for vid in visit_ids)
        rev = sum(allocated_revenue(vid) for vid in visit_ids)
        profit = rev - cost
        margin = (profit / rev * 100.0) if rev else 0.0
        routes.append(RoutePnL(
            route_id=route.id, name=route.name or route.external_id,
            route_date=route.route_date.isoformat() if route.route_date else '—',
            technician=route.technician or '—', visits=len(visit_ids),
            revenue=rev, cost=cost, profit=profit, margin_pct=margin,
        ))
        t = tech_acc.setdefault(route.technician or '—', {'routes': 0, 'visits': 0, 'rev': 0.0, 'cost': 0.0})
        t['routes'] += 1
        t['visits'] += len(visit_ids)
        t['rev'] += rev
        t['cost'] += cost

    routes.sort(key=lambda r: r.profit, reverse=True)

    technicians = []
    for tech, d in tech_acc.items():
        profit = d['rev'] - d['cost']
        technicians.append(TechPnL(
            technician=tech, routes=d['routes'], visits=d['visits'],
            revenue=d['rev'], cost=d['cost'], profit=profit,
            margin_pct=(profit / d['rev'] * 100.0) if d['rev'] else 0.0,
        ))
    technicians.sort(key=lambda t: t.profit, reverse=True)

    unrouted = sum(1 for vid in visit_info if vid not in routed_visit_ids)
    return RoutePnLSummary(
        cost_per_hour=cost_per_hour, routes=routes, technicians=technicians,
        unrouted_visits=unrouted,
        total_revenue=sum(r.revenue for r in routes),
        total_cost=sum(r.cost for r in routes),
        total_profit=sum(r.profit for r in routes),
    )
