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

from sqlmodel import Session, select

from app.models.ops_tables import ActualChemicalFact, ActualLaborFact, BillingDocument, ServiceVisit
from app.models.tables import Account, ChemicalProduct, Property
from app.services.cost_of_business import compute_cost_of_business
from app.services.expenses import latest_unit_cost


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


def account_profitability(session: Session) -> ProfitabilitySummary:
    cost_per_hour = compute_cost_of_business(session).true_cost_per_hour
    prices = _price_map(session)

    property_account = {p.id: p.account_id for p in session.exec(select(Property)).all()}
    account_name = {a.id: a.name for a in session.exec(select(Account)).all()}

    # Revenue by account (FreshBooks invoices).
    revenue: dict[int, float] = {}
    for doc in session.exec(select(BillingDocument).where(BillingDocument.source_slug == 'freshbooks')).all():
        if doc.account_id:
            revenue[doc.account_id] = revenue.get(doc.account_id, 0.0) + doc.total_amount

    # Cost by account from Skimmer-fed visit actuals.
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
