"""End-to-end: Skimmer cost + FreshBooks revenue join on the matched account."""
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

import app.models  # noqa: F401
from app.models.ops_tables import BillingDocument
from app.services.bootstrap import seed_defaults
from app.connectors.skimmer.client import SkimmerClient
from app.services.freshbooks_revenue import FIXTURE_INVOICES, sync_freshbooks_invoices
from app.services.profitability import account_profitability
from app.services.skimmer_sync import sync_skimmer


def _session() -> Session:
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    seed_defaults(session)  # products (for chemical costing) + labor settings + expenses
    return session


def test_freshbooks_pull_lands_invoices_and_matches():
    with _session() as s:
        # Skimmer first: creates the customer accounts (Mateo, Sunset Resort).
        sync_skimmer(s, client=SkimmerClient(use_fixtures=True))
        result = sync_freshbooks_invoices(s, invoices=FIXTURE_INVOICES)

    assert result.invoices_seen == 3
    assert result.documents_created == 3
    assert round(result.total_revenue, 2) == 540.0  # 180 + 240 + 120
    # Two invoices match Skimmer accounts by email; Marina Cafe is new (still matched to a fresh account).
    assert result.matched == 3
    with _session() as s2:
        pass  # (separate session sanity; not needed)


def test_profitability_joins_revenue_and_cost():
    with _session() as s:
        sync_skimmer(s, client=SkimmerClient(use_fixtures=True))
        sync_freshbooks_invoices(s, invoices=FIXTURE_INVOICES)
        summary = account_profitability(s)

    # Revenue recognized across accounts.
    assert round(summary.total_revenue, 2) == 540.0
    # Cost is positive (labor + chemicals from the 3 Skimmer visits).
    assert summary.total_cost > 0
    assert round(summary.total_profit, 2) == round(summary.total_revenue - summary.total_cost, 2)

    # Mateo Alvarez: 2 visits (wo-5001, wo-5002), invoice 180. Should appear with revenue + cost + visits.
    mateo = next((a for a in summary.accounts if 'Alvarez' in a.name or 'Mateo' in a.name), None)
    assert mateo is not None
    assert round(mateo.revenue, 2) == 180.0
    assert mateo.visits == 2
    assert mateo.labor_cost > 0
    assert mateo.chemical_cost > 0

    # Marina Cafe billed 120 but has no Skimmer visits -> revenue-only, pure profit line.
    marina = next((a for a in summary.accounts if 'Marina' in a.name), None)
    assert marina is not None
    assert round(marina.revenue, 2) == 120.0
    assert marina.visits == 0
    assert round(marina.total_cost, 2) == 0.0


def test_pull_is_idempotent():
    with _session() as s:
        sync_skimmer(s, client=SkimmerClient(use_fixtures=True))
        sync_freshbooks_invoices(s, invoices=FIXTURE_INVOICES)
        second = sync_freshbooks_invoices(s, invoices=FIXTURE_INVOICES)
        assert second.documents_created == 0
        docs = list(s.exec(select(BillingDocument)).all())
        assert len(docs) == 3


class _FakeFBClient:
    """Stands in for FreshBooksClient, returning FreshBooks-shaped invoice JSON."""
    account_id = '6BApk'

    def resolve_first_account_id(self):
        return self.account_id

    def list_invoices(self, *, page=1, per_page=100, include=None, account_id=None):
        if page > 1:
            return [], 1
        invoices = [{
            'invoiceid': 778001, 'invoice_number': '0042', 'customerid': 55,
            'organization': '', 'fname': 'Mateo', 'lname': 'Alvarez', 'email': 'mateo@example.com',
            'amount': {'amount': '180.00', 'code': 'USD'}, 'create_date': '2026-06-28',
            'v3_status': 'paid',
            'lines': [{'name': 'Service', 'description': 'Monthly pool service',
                       'qty': '2', 'unit_cost': {'amount': '90.00'}, 'amount': {'amount': '180.00'}}],
        }]
        return invoices, 1


def test_live_freshbooks_pull_normalizes_and_lands():
    from app.services.freshbooks_revenue import fetch_live_invoices, normalize_fb_invoice

    raw = {'invoiceid': 1, 'customerid': 9, 'fname': 'A', 'lname': 'B', 'email': 'A@B.com',
           'amount': {'amount': '240.00', 'code': 'USD'}, 'create_date': '2026-06-01', 'v3_status': 'sent',
           'lines': [{'description': 'x', 'qty': '1', 'unit_cost': {'amount': '240.00'}, 'amount': {'amount': '240.00'}}]}
    norm = normalize_fb_invoice(raw)
    assert norm['id'] == 'fb_inv_1'
    assert norm['amount'] == 240.0
    assert norm['client_email'] == 'A@B.com'
    assert norm['lines'][0]['unit_price'] == 240.0

    with _session() as s:
        result = sync_freshbooks_invoices(s, client=_FakeFBClient())
    assert result.mode == 'live'
    assert result.invoices_seen == 1
    assert round(result.total_revenue, 2) == 180.0
    assert result.documents_created == 1


def test_revenue_composition_by_status():
    from app.services.profitability import revenue_composition
    with _session() as s:
        sync_freshbooks_invoices(s, invoices=FIXTURE_INVOICES)
        comp = revenue_composition(s)
    # Fixtures: inv-9001 paid $180, inv-9002 sent $240, inv-9003 paid $120.
    assert comp.invoices == 3
    assert round(comp.total, 2) == 540.0
    by = {r.status: r for r in comp.rows}
    assert by['paid'].count == 2 and round(by['paid'].amount, 2) == 300.0
    assert by['sent'].count == 1 and round(by['sent'].amount, 2) == 240.0
    assert round(comp.collected, 2) == 300.0     # paid
    assert round(comp.outstanding, 2) == 240.0    # sent is unpaid
    assert round(comp.recurring, 2) == 0.0        # no auto-paid in the fixtures
    assert comp.rows[0].status == 'paid'          # sorted by amount desc


def test_profitability_period_filter():
    from datetime import date
    with _session() as s:
        sync_skimmer(s, client=SkimmerClient(use_fixtures=True))
        sync_freshbooks_invoices(s, invoices=FIXTURE_INVOICES)
        alltime = account_profitability(s)
        # Window on/after 2026-06-26 keeps inv-9001 (06-28) + inv-9002 (06-29),
        # excludes Marina inv-9003 (06-25). All Skimmer visits (06-08..15) are
        # before the window -> no cost recognized.
        scoped = account_profitability(s, start=date(2026, 6, 26))
    assert round(alltime.total_revenue, 2) == 540.0
    assert round(scoped.total_revenue, 2) == 420.0
    assert round(scoped.total_cost, 2) == 0.0
