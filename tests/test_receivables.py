"""A/R aging: exclude collected, bucket outstanding by age, roll up by customer."""
from datetime import date, timedelta

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

import app.models  # noqa: F401
from app.models.ops_tables import BillingDocument
from app.models.tables import Account
from app.services.accounts_receivable import accounts_receivable


def _session() -> Session:
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _doc(s, account_id, status, days_ago, amount, today):
    s.add(BillingDocument(
        source_slug='freshbooks', external_id=f'i-{status}-{days_ago}-{amount}',
        account_id=account_id, status=status,
        issued_on=today - timedelta(days=days_ago), total_amount=amount,
    ))


def test_ar_aging_excludes_collected_and_buckets():
    today = date(2026, 7, 1)
    with _session() as s:
        a = Account(account_type='residential', name='Acme')
        s.add(a); s.commit(); s.refresh(a)
        _doc(s, a.id, 'paid', 40, 500.0, today)       # collected -> excluded
        _doc(s, a.id, 'auto-paid', 2, 90.0, today)    # collected -> excluded (fresh autopay)
        _doc(s, a.id, 'sent', 5, 100.0, today)        # current 0-30
        _doc(s, a.id, 'sent', 45, 200.0, today)       # 31-60
        _doc(s, a.id, 'overdue', 100, 300.0, today)   # 90+
        s.commit()
        ar = accounts_receivable(s, today=today)

    assert round(ar.total_outstanding, 2) == 600.0    # 100 + 200 + 300; collected excluded
    assert ar.invoice_count == 3
    assert round(ar.current, 2) == 100.0              # only the 5-day 'sent'
    assert round(ar.aged, 2) == 500.0                 # 200 + 300

    buckets = {b: (n, round(amt, 2)) for (b, n, amt) in ar.buckets}
    assert buckets['0-30 (current)'] == (1, 100.0)
    assert buckets['31-60'] == (1, 200.0)
    assert buckets['61-90'] == (0, 0.0)
    assert buckets['90+'] == (1, 300.0)

    assert len(ar.customers) == 1
    assert round(ar.customers[0].amount, 2) == 600.0
    assert ar.customers[0].oldest_days == 100
