"""Customer profitability: FreshBooks revenue minus Skimmer-fed real cost.

Joins the two sides on the internal account (unified by customer matching):
  revenue  = sum of FreshBooks BillingDocument totals for the account
  cost     = labor (visit minutes x true $/hour) + chemicals (qty x latest cost)
             from the Skimmer-fed ServiceVisit actuals at the account's properties
  profit   = revenue - cost

This is the "where's the profit" lens at the customer grain. Route-level rollup
is the next step once visits are grouped by route.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from sqlmodel import Session, select

from app.models.ops_tables import ActualChemicalFact, ActualLaborFact, BillingDocument, ServiceVisit
from app.models.tables import Account, ChemicalProduct, Property
from app.services.cost_of_business import compute_cost_of_business
from app.services.expenses import latest_unit_cost


def in_range(d: date | None, start: date | None, end: date | None) -> bool:
    """Whether date d falls in [start, end] (inclusive). No bounds -> always true.
    A missing date is excluded whenever any bound is set (can't place it)."""
    if start is None and end is None:
        return True
    if d is None:
        return False
    if start and d < start:
        return False
    if end and d > end:
        return False
    return True


@dataclass
class AccountPnL:
    account_id: int
    name: str
    revenue: float
    labor_cost: float
    chemical_cost: float
    total_cost: float
    profit: float
    margin_pct: float
    visits: int


@dataclass
class ProfitabilitySummary:
    cost_per_hour: float
    total_revenue: float
    total_cost: float
    total_profit: float
    accounts: list = field(default_factory=list)   # list[AccountPnL], most profitable first
    losers: list = field(default_factory=list)      # accounts running at a loss


def _price_map(session: Session) -> dict[int, float]:
    prices: dict[int, float] = {}
    for product in session.exec(select(ChemicalProduct)).all():
        prices[product.id] = latest_unit_cost(session, product)
    return prices


def account_profitability(session: Session, start: date | None = None, end: date | None = None) -> ProfitabilitySummary:
    """Customer P&L, optionally scoped to invoices issued and visits performed in
    [start, end] (inclusive). No bounds = all-time."""
    cost_per_hour = compute_cost_of_business(session).true_cost_per_hour
    prices = _price_map(session)

    property_account = {p.id: p.account_id for p in session.exec(select(Property)).all()}
    account_name = {a.id: a.name for a in session.exec(select(Account)).all()}

    # Revenue by account (FreshBooks invoices issued in the period).
    revenue: dict[int, float] = {}
    for doc in session.exec(select(BillingDocument).where(BillingDocument.source_slug == 'freshbooks')).all():
        if doc.account_id and in_range(doc.issued_on, start, end):
            revenue[doc.account_id] = revenue.get(doc.account_id, 0.0) + doc.total_amount

    # Cost by account from Skimmer-fed visit actuals (visits performed in the period).
    labor_by_visit = {l.service_visit_id: l for l in session.exec(select(ActualLaborFact)).all()}
    chem_by_visit: dict[int, list[ActualChemicalFact]] = {}
    for c in session.exec(select(ActualChemicalFact)).all():
        chem_by_visit.setdefault(c.service_visit_id, []).append(c)

    labor_cost: dict[int, float] = {}
    chem_cost: dict[int, float] = {}
    visit_count: dict[int, int] = {}
    for visit in session.exec(select(ServiceVisit)).all():
        acct = property_account.get(visit.property_id)
        if not acct:
            continue
        if not in_range(visit.occurred_at.date() if visit.occurred_at else None, start, end):
            continue
        visit_count[acct] = visit_count.get(acct, 0) + 1
        lab = labor_by_visit.get(visit.id)
        if lab:
            labor_cost[acct] = labor_cost.get(acct, 0.0) + (lab.total_minutes / 60.0) * cost_per_hour
        for chem in chem_by_visit.get(visit.id, []):
            unit_cost = prices.get(chem.chemical_product_id, 0.0) if chem.chemical_product_id else 0.0
            chem_cost[acct] = chem_cost.get(acct, 0.0) + chem.quantity * unit_cost

    account_ids = set(revenue) | set(labor_cost) | set(chem_cost) | set(visit_count)
    rows: list[AccountPnL] = []
    for aid in account_ids:
        rev = revenue.get(aid, 0.0)
        lab = labor_cost.get(aid, 0.0)
        chem = chem_cost.get(aid, 0.0)
        total_cost = lab + chem
        profit = rev - total_cost
        margin = (profit / rev * 100.0) if rev else 0.0
        rows.append(AccountPnL(
            account_id=aid, name=account_name.get(aid, f'Account {aid}'),
            revenue=rev, labor_cost=lab, chemical_cost=chem, total_cost=total_cost,
            profit=profit, margin_pct=margin, visits=visit_count.get(aid, 0),
        ))
    rows.sort(key=lambda r: r.profit, reverse=True)

    return ProfitabilitySummary(
        cost_per_hour=cost_per_hour,
        total_revenue=sum(r.revenue for r in rows),
        total_cost=sum(r.total_cost for r in rows),
        total_profit=sum(r.profit for r in rows),
        accounts=rows,
        losers=[r for r in rows if r.profit < 0],
    )


# Invoice status buckets (FreshBooks v3_status values).
_COLLECTED = {'paid', 'auto-paid', 'autopaid', 'deposit-paid'}
_RECURRING = {'auto-paid', 'autopaid'}


@dataclass
class StatusRow:
    status: str
    count: int
    amount: float
    pct: float


@dataclass
class RevenueComposition:
    invoices: int
    total: float
    collected: float
    outstanding: float
    recurring: float           # auto-paid (recurring autopay)
    one_off_collected: float   # collected minus recurring
    rows: list = field(default_factory=list)   # StatusRow, amount desc


def revenue_composition(session: Session, start: date | None = None, end: date | None = None) -> RevenueComposition:
    """Break FreshBooks invoices down by status (paid / auto-paid / sent / ...),
    scoped to [start, end]. The row table is sortable in the UI by any column."""
    by_status: dict[str, list] = {}
    total = 0.0
    for doc in session.exec(select(BillingDocument).where(BillingDocument.source_slug == 'freshbooks')).all():
        if not in_range(doc.issued_on, start, end):
            continue
        st = (doc.status or '(blank)').lower()
        bucket = by_status.setdefault(st, [0, 0.0])
        bucket[0] += 1
        bucket[1] += doc.total_amount
        total += doc.total_amount

    rows = [StatusRow(status=st, count=n, amount=amt, pct=(amt / total * 100.0) if total else 0.0)
            for st, (n, amt) in by_status.items()]
    rows.sort(key=lambda r: r.amount, reverse=True)

    collected = sum(r.amount for r in rows if r.status in _COLLECTED)
    recurring = sum(r.amount for r in rows if r.status in _RECURRING)
    return RevenueComposition(
        invoices=sum(r.count for r in rows),
        total=total,
        collected=collected,
        outstanding=total - collected,
        recurring=recurring,
        one_off_collected=collected - recurring,
        rows=rows,
    )


def revenue_by_month(session: Session, start: date | None = None, end: date | None = None) -> list[tuple[str, float]]:
    """Monthly billed revenue as [(YYYY-MM, amount), ...], chronological."""
    agg: dict[str, float] = {}
    for doc in session.exec(select(BillingDocument).where(BillingDocument.source_slug == 'freshbooks')).all():
        if not doc.issued_on or not in_range(doc.issued_on, start, end):
            continue
        key = doc.issued_on.strftime('%Y-%m')
        agg[key] = agg.get(key, 0.0) + doc.total_amount
    return sorted(agg.items())
