"""Monthly billed revenue: group FreshBooks invoices by issued year-month."""
from datetime import date

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

import app.models  # noqa: F401
from app.models.ops_tables import BillingDocument
from app.services.profitability import revenue_by_month


def _session() -> Session:
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _doc(s, ext, issued_on, amount):
    s.add(BillingDocument(
        source_slug='freshbooks', external_id=ext, status='paid',
        issued_on=issued_on, total_amount=amount,
    ))


def test_revenue_by_month_groups_and_sorts():
    with _session() as s:
        _doc(s, 'a', date(2026, 1, 5), 100.0)
        _doc(s, 'b', date(2026, 1, 20), 50.0)     # same month -> sums
        _doc(s, 'c', date(2026, 3, 2), 200.0)
        _doc(s, 'd', date(2025, 12, 31), 40.0)    # prior year, sorts first
        _doc(s, 'e', None, 999.0)                 # undated -> excluded
        s.commit()
        rows = revenue_by_month(s)

    assert rows == [('2025-12', 40.0), ('2026-01', 150.0), ('2026-03', 200.0)]


def test_revenue_by_month_respects_range():
    with _session() as s:
        _doc(s, 'a', date(2026, 1, 5), 100.0)
        _doc(s, 'b', date(2026, 6, 5), 300.0)
        s.commit()
        rows = revenue_by_month(s, start=date(2026, 2, 1))

    assert rows == [('2026-06', 300.0)]
