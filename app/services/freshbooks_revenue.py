"""FreshBooks invoice (revenue) pull.

Brings customer invoices INTO the platform as revenue (the existing FreshBooks
integration only pushes estimates out). Each invoice resolves its client through
the customer-matching engine to an internal account, then lands in the
BillingDocument / BillingLine tables so profitability can join it to the
Skimmer-fed cost on the same account.

Fixture-first, like the Skimmer connector: works today against bundled sample
invoices; swap the fixture source for the live FreshBooks client when the token
is wired.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from sqlmodel import Session, select

from app.models.ops_tables import BillingDocument, BillingLine
from app.services.customer_matching import resolve_customer

SOURCE = 'freshbooks'

# Sample invoices; client emails intentionally overlap the Skimmer fixture
# customers so the identity match auto-links (and one FreshBooks-only client
# creates a revenue-only account).
FIXTURE_INVOICES: list[dict] = [
    {
        'id': 'inv-9001', 'invoice_number': '0001', 'client_id': 'fbc-1',
        'client_name': 'Mateo Alvarez', 'client_email': 'mateo@example.com', 'client_phone': '+13055551201',
        'amount': 180.0, 'issue_date': '2026-06-28', 'status': 'paid',
        'lines': [{'description': 'Monthly pool service', 'quantity': 2, 'unit_price': 90.0, 'amount': 180.0}],
    },
    {
        'id': 'inv-9002', 'invoice_number': '0002', 'client_id': 'fbc-2',
        'client_name': 'Sunset Resort HOA', 'client_email': 'ops@sunsetresort.example', 'client_phone': '+13055551302',
        'amount': 240.0, 'issue_date': '2026-06-29', 'status': 'sent',
        'lines': [{'description': 'Commercial pool service', 'quantity': 1, 'unit_price': 240.0, 'amount': 240.0}],
    },
    {
        'id': 'inv-9003', 'invoice_number': '0003', 'client_id': 'fbc-3',
        'client_name': 'Marina Cafe', 'client_email': 'accounts@marinacafe.example', 'client_phone': '',
        'amount': 120.0, 'issue_date': '2026-06-25', 'status': 'paid',
        'lines': [{'description': 'One-time green-to-clean', 'quantity': 1, 'unit_price': 120.0, 'amount': 120.0}],
    },
]


@dataclass
class RevenueSyncResult:
    invoices_seen: int = 0
    documents_created: int = 0
    total_revenue: float = 0.0
    matched: int = 0
    unmatched: int = 0


def _parse_date(text: str) -> date | None:
    text = (text or '').strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace('Z', '+00:00')).date()
    except ValueError:
        try:
            return datetime.strptime(text[:10], '%Y-%m-%d').date()
        except ValueError:
            return None


def sync_freshbooks_invoices(session: Session, invoices: list[dict] | None = None, apply: bool = True) -> RevenueSyncResult:
    invoices = invoices if invoices is not None else FIXTURE_INVOICES
    result = RevenueSyncResult()

    for inv in invoices:
        result.invoices_seen += 1
        result.total_revenue += float(inv.get('amount', 0.0) or 0.0)

        account_id = None
        if apply:
            res = resolve_customer(
                session, source=SOURCE, external_id=inv['client_id'],
                name=inv.get('client_name', ''), email=inv.get('client_email', ''),
                phone=inv.get('client_phone', ''),
            )
            account_id = res.account_id
        if account_id:
            result.matched += 1
        else:
            result.unmatched += 1

        existing = session.exec(
            select(BillingDocument)
            .where(BillingDocument.source_slug == SOURCE)
            .where(BillingDocument.external_id == inv['id'])
        ).first()
        if existing:
            # Keep the account link fresh (a later manual match may have resolved it).
            if account_id and existing.account_id != account_id:
                existing.account_id = account_id
                session.commit()
            continue

        doc = BillingDocument(
            source_slug=SOURCE, external_id=inv['id'], account_id=account_id,
            issued_on=_parse_date(inv.get('issue_date', '')),
            total_amount=float(inv.get('amount', 0.0) or 0.0),
            status=inv.get('status', 'draft'),
        )
        session.add(doc)
        session.commit()
        session.refresh(doc)
        result.documents_created += 1
        for line in inv.get('lines', []):
            session.add(BillingLine(
                billing_document_id=doc.id, description=line.get('description', ''),
                quantity=float(line.get('quantity', 0.0) or 0.0),
                unit_price=float(line.get('unit_price', 0.0) or 0.0),
                amount=float(line.get('amount', 0.0) or 0.0),
            ))
        session.commit()

    return result
