"""Locks the Skimmer connector: normalizer, fixture sync, apply, idempotency."""
from datetime import date

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

import app.models  # noqa: F401  -- registers tables
from app.connectors.skimmer.client import SkimmerClient, get_skimmer_client
from app.connectors.skimmer.normalizer import normalize_work_order, parse_date
from app.models.ops_tables import ActualChemicalFact, ActualLaborFact, ServiceVisit
from app.models.tables import ChemicalProduct, PoolVessel, Property
from app.services.skimmer_sync import sync_skimmer


def _session() -> Session:
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _seed_products(session: Session) -> None:
    for sku, name, unit, cost, aliases in [
        ('LIQ-CL-12', 'Liquid Chlorine 12%', 'gal', 4.25, 'chlorine, sodium hypochlorite'),
        ('MURI-ACID', 'Muriatic Acid', 'gal', 8.0, 'hydrochloric acid, muriatic'),
        ('SOD-BICARB', 'Sodium Bicarbonate', 'lb', 0.75, 'bicarb'),
    ]:
        session.add(ChemicalProduct(sku=sku, name=name, unit=unit, default_unit_cost=cost, aliases_csv=aliases))
    session.commit()


def test_parse_date_and_work_order_normalizer():
    assert parse_date('2026-06-08T00:00:00Z') == date(2026, 6, 8)
    wo = normalize_work_order({
        'id': 'wo-1', 'serviceLocationId': 'sl-1', 'serviceDate': '2026-06-08T00:00:00Z',
        'estimatedMinutes': 30, 'actualMinutes': 34, 'laborCost': 22.5, 'price': 90.0,
        'technician': 'Dana', 'workNeeded': 'Service',
        'chemicalsUsed': [{'name': 'Liquid Chlorine 12%', 'quantity': 1.5, 'unit': 'gal'}],
    })
    assert wo['external_id'] == 'wo-1'
    assert wo['actual_minutes'] == 34          # prefers actual over estimated
    assert wo['service_date'] == date(2026, 6, 8)
    assert len(wo['chemicals']) == 1 and wo['chemicals'][0]['quantity'] == 1.5


def test_client_defaults_to_fixture_mode_without_key():
    client = get_skimmer_client(api_key='')
    assert client.mode == 'fixtures'
    assert len(client.work_orders()) == 3


def test_sync_applies_fixtures_into_ops_tables():
    with _session() as s:
        _seed_products(s)
        result = sync_skimmer(s, client=SkimmerClient(use_fixtures=True))

        assert result.mode == 'fixtures'
        assert result.properties_created == 2
        assert result.vessels_created == 2
        assert result.service_visits_created == 3
        assert result.unmatched_work_orders == 0

        # Properties + vessels created from Skimmer service locations / bodies of water.
        assert len(list(s.exec(select(Property)).all())) == 2
        assert len(list(s.exec(select(PoolVessel)).all())) == 2

        # Service visits carry the Skimmer external id and are linked to a property.
        visits = list(s.exec(select(ServiceVisit)).all())
        assert len(visits) == 3
        assert all(v.source_slug == 'skimmer' and v.property_id for v in visits)

        # Labor + chemical actuals recorded.
        assert len(list(s.exec(select(ActualLaborFact)).all())) == 3
        chem_facts = list(s.exec(select(ActualChemicalFact)).all())
        assert len(chem_facts) == 5  # 2 + 1 + 2 across the three work orders
        # Chemicals matched to seeded products by name/alias.
        matched = [c for c in chem_facts if c.chemical_product_id is not None]
        assert len(matched) >= 4


def test_sync_is_idempotent():
    with _session() as s:
        _seed_products(s)
        client = SkimmerClient(use_fixtures=True)
        sync_skimmer(s, client=client)
        second = sync_skimmer(s, client=client)

        # Second run creates nothing new.
        assert second.properties_created == 0
        assert second.vessels_created == 0
        assert second.service_visits_created == 0
        assert second.raw_records_new == 0

        # And there are no duplicates.
        assert len(list(s.exec(select(ServiceVisit)).all())) == 3
        assert len(list(s.exec(select(Property)).all())) == 2
