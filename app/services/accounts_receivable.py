"""Accounts-receivable aging: what's owed, how old, by whom.

Outstanding = every FreshBooks invoice not in a collected status
(paid / auto-paid / deposit-paid). Each is aged by days since it was issued and
bucketed 0-30 (current) / 31-60 / 61-90 / 90+. The 0-30 bucket is where
freshly-issued recurring bills sit -- they typically auto-pay within days, so
collections attention belongs on 31+.

Note: we age by issue date (FreshBooks due dates aren't stored yet) and treat an
unpaid invoice's outstanding balance as its total (partial-payment balances
aren't stored, so 'partial' invoices are approximate -- they're rare).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from sqlmodel import Session, select

from app.models.ops_tables import BillingDocument
from app.models.tables import Account

COLLECTED = {'paid', 'auto-paid', 'autopaid', 'deposit-paid'}
CURRENT_DAYS = 30  # 0..CURRENT_DAYS = "current"; beyond = aged/overdue


@dataclass
class ARCustomer:
    account_id: int
    name: str
    amount: float
    invoices: int
    oldest_days: int


@dataclass
class ARSummary:
    total_outstanding: float = 0.0
    invoice_count: int = 0
    current: float = 0.0            # 0-30 days (incl. fresh recurring bills)
    aged: float = 0.0              # 31+ days -- the collections focus
    buckets: list = field(default_factory=list)     # [(label, count, amount)]
    customers: list = field(default_factory=list)    # ARCustomer, amount desc


def _bucket(days: int) -> str:
    if days <= CURRENT_DAYS:
        return '0-30 (current)'
    if days <= 60:
        return '31-60'
    if days <= 90:
        return '61-90'
    return '90+'


_BUCKET_ORDER = ['0-30 (current)', '31-60', '61-90', '90+']


def accounts_receivable(session: Session, today: date | None = None) -> ARSummary:
    today = today or date.today()
    account_name = {a.id: a.name for a in session.exec(select(Account)).all()}

    bucket_agg: dict[str, list] = {b: [0, 0.0] for b in _BUCKET_ORDER}
    cust_agg: dict[int, dict] = {}
    total = 0.0
    count = 0

    for doc in session.exec(select(BillingDocument).where(BillingDocument.source_slug == 'freshbooks')).all():
        if (doc.status or '').lower() in COLLECTED:
            continue
        amt = doc.total_amount
        days = max(0, (today - doc.issued_on).days) if doc.issued_on else 0
        total += amt
        count += 1
        b = _bucket(days)
        bucket_agg[b][0] += 1
        bucket_agg[b][1] += amt
        if doc.account_id:
            c = cust_agg.setdefault(doc.account_id, {'amt': 0.0, 'n': 0, 'oldest': 0})
            c['amt'] += amt
            c['n'] += 1
            c['oldest'] = max(c['oldest'], days)

    current = bucket_agg['0-30 (current)'][1]
    aged = total - current

    customers = [
        ARCustomer(account_id=aid, name=account_name.get(aid, f'Account {aid}'),
                   amount=c['amt'], invoices=c['n'], oldest_days=c['oldest'])
        for aid, c in cust_agg.items()
    ]
    customers.sort(key=lambda x: x.amount, reverse=True)

    return ARSummary(
        total_outstanding=total,
        invoice_count=count,
        current=current,
        aged=aged,
        buckets=[(b, bucket_agg[b][0], bucket_agg[b][1]) for b in _BUCKET_ORDER],
        customers=customers,
    )
