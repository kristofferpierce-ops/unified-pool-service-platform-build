"""Route apply + route-level P&L with allocated revenue."""
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

import app.models  # noqa: F401
from app.models.route_tables import RouteRecord, RouteVisit
from app.services.bootstrap import seed_defaults
from app.connectors.skimmer.client import SkimmerClient
from app.services.freshbooks_revenue import FIXTURE_INVOICES, sync_freshbooks_invoices
from app.services.route_pnl import route_pnl
from app.services.skimmer_sync import sync_skimmer


def _session() -> Session:
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    seed_defaults(session)
    return session


def test_skimmer_applies_routes_and_links():
    with _session() as s:
        result = sync_skimmer(s, client=SkimmerClient(use_fixtures=True))
        assert result.routes_created == 2          # route-70, route-71
        assert result.route_links_created == 2     # each route references one work order
        assert len(list(s.exec(select(RouteRecord)).all())) == 2
        assert len(list(s.exec(select(RouteVisit)).all())) == 2


def test_route_pnl_rolls_up_cost_and_allocated_revenue():
    with _session() as s:
        sync_skimmer(s, client=SkimmerClient(use_fixtures=True))
        sync_freshbooks_invoices(s, invoices=FIXTURE_INVOICES)
        summary = route_pnl(s)

    assert summary.cost_per_hour > 0
    assert len(summary.routes) == 2

    # route-70 carries wo-5001 (Mateo). Mateo has 2 visits + $180 invoice ->
    # $90 allocated to this route's single visit. Cost is positive.
    r70 = next(r for r in summary.routes if 'Monday' in r.name)
    assert r70.visits == 1
    assert round(r70.revenue, 2) == 90.0
    assert r70.cost > 0
    assert round(r70.profit, 2) == round(r70.revenue - r70.cost, 2)

    # Technician rollup present.
    assert any(t.technician == 'Dana R.' for t in summary.technicians)


def test_route_apply_is_idempotent():
    with _session() as s:
        client = SkimmerClient(use_fixtures=True)
        sync_skimmer(s, client=client)
        second = sync_skimmer(s, client=client)
        assert second.routes_created == 0
        assert second.route_links_created == 0
        assert len(list(s.exec(select(RouteVisit)).all())) == 2
