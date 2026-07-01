"""End-to-end: Skimmer cost + FreshBooks revenue join on the matched account."""
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

import app.models  # noqa: F401
from app.models.ops_tables import BillingDocument
from app.services.bootstrap import seed_defaults
from app.connectors.skimmer.client import SkimmerClient
from app.services.freshbooks_revenue import sync_freshbooks_invoices
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
        result = sync_freshbooks_invoices(s)

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
        sync_freshbooks_invoices(s)
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
        sync_freshbooks_invoices(s)
        second = sync_freshbooks_invoices(s)
        assert second.documents_created == 0
        docs = list(s.exec(select(BillingDocument)).all())
        assert len(docs) == 3
