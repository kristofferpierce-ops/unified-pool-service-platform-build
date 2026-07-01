"""Locks the asset lifecycle: create -> receive -> install -> retire + rollups."""
from datetime import date, timedelta

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

import app.models  # noqa: F401  -- registers tables
from app.services.assets import (
    asset_summary,
    create_asset,
    install_asset,
    list_assets,
    receive_asset,
    retire_asset,
)


def _session() -> Session:
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def test_lifecycle_transitions_stamp_status_and_dates():
    with _session() as s:
        a = create_asset(s, name='IntelliFlo VSF', category='pump', manufacturer='Pentair',
                         model_number='011056', serial_number='SN-1', purchase_cost=1200.0)
        assert a.status == 'ordered'

        a = receive_asset(s, a.id, received_date=date(2026, 6, 1))
        assert a.status == 'received' and a.received_date == date(2026, 6, 1)

        a = install_asset(s, a.id, property_id=7, vessel_id=3, install_date=date(2026, 6, 5),
                          warranty_until=date(2027, 6, 5))
        assert a.status == 'installed'
        assert a.property_id == 7 and a.vessel_id == 3
        assert a.install_date == date(2026, 6, 5) and a.warranty_until == date(2027, 6, 5)

        a = retire_asset(s, a.id, retirement_date=date(2030, 1, 1), reason='motor failure')
        assert a.status == 'retired' and a.retirement_date == date(2030, 1, 1)
        assert 'motor failure' in a.notes


def test_list_filters_by_status_and_property():
    with _session() as s:
        p1 = create_asset(s, name='Pump A', category='pump')
        install_asset(s, p1.id, property_id=1)
        create_asset(s, name='Heater B', category='heater')  # stays ordered
        h = create_asset(s, name='Filter C', category='filter')
        install_asset(s, h.id, property_id=2)

        assert len(list_assets(s)) == 3
        assert len(list_assets(s, status='installed')) == 2
        assert len(list_assets(s, status='ordered')) == 1
        assert len(list_assets(s, property_id=1)) == 1
        assert len(list_assets(s, category='filter')) == 1


def test_summary_installed_base_and_warranty():
    today = date(2026, 6, 30)
    with _session() as s:
        a = create_asset(s, name='Pump', category='pump', purchase_cost=1000.0)
        install_asset(s, a.id, property_id=1, warranty_until=today + timedelta(days=30))  # expiring soon
        b = create_asset(s, name='Heater', category='heater', purchase_cost=3000.0)
        install_asset(s, b.id, property_id=1, warranty_until=today + timedelta(days=400))  # in warranty, not soon
        c = create_asset(s, name='Old filter', category='filter', purchase_cost=500.0)
        install_asset(s, c.id, property_id=2, warranty_until=today - timedelta(days=10))  # expired
        create_asset(s, name='Spare', category='pump', purchase_cost=900.0)  # ordered, not installed

        summ = asset_summary(s, soon_days=60, today=today)
    assert summ.total == 4
    assert summ.installed_count == 3
    assert summ.installed_base_value == 4500.0   # 1000 + 3000 + 500 (spare not installed)
    assert summ.in_warranty == 2                 # pump + heater (filter expired)
    assert summ.warranty_expiring_soon == 1      # only the pump (30 days)
    assert summ.by_status['ordered'] == 1
    assert summ.by_status['installed'] == 3
