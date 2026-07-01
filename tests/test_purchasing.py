"""Locks purchasing-intelligence logic: price book, best source, anomalies."""
from datetime import date

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

import app.models  # noqa: F401  -- registers tables
from app.models.tables import ChemicalProduct, ProductPriceHistory
from app.services.purchasing import (
    best_source_for_product,
    detect_price_anomalies,
    purchasing_summary,
)


def _session() -> Session:
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _product(session, sku='LIQ-CL-12', name='Liquid Chlorine 12%', unit='gal', default=4.25):
    p = ChemicalProduct(sku=sku, name=name, unit=unit, default_unit_cost=default)
    session.add(p)
    session.commit()
    session.refresh(p)
    return p


def _obs(session, product_id, vendor, cost, day, pack='1 gal'):
    session.add(ProductPriceHistory(
        product_id=product_id, vendor_name=vendor, unit_cost=cost,
        effective_date=date(2026, 6, day), pack_size=pack, confidence=1.0, approved_by='test',
    ))
    session.commit()


def test_best_source_picks_cheapest_current_vendor():
    with _session() as s:
        p = _product(s)
        _obs(s, p.id, 'Heritage', 4.50, 1)
        _obs(s, p.id, 'PoolCorp', 4.10, 2)
        _obs(s, p.id, 'Heritage', 4.40, 10)   # Heritage's latest is 4.40
        _obs(s, p.id, 'PoolCorp', 4.20, 11)   # PoolCorp's latest is 4.20 -> cheapest
        bs = best_source_for_product(s, p)
    assert bs is not None
    assert bs.best_vendor == 'PoolCorp'
    assert round(bs.best_unit_cost, 2) == 4.20
    assert round(bs.worst_unit_cost, 2) == 4.40
    assert round(bs.spread_abs, 2) == 0.20
    assert round(bs.spread_pct, 2) == round(0.20 / 4.20 * 100, 2)
    # Cheapest listed first.
    assert bs.vendors[0].vendor == 'PoolCorp'


def test_no_history_returns_none():
    with _session() as s:
        p = _product(s)
        assert best_source_for_product(s, p) is None


def test_anomaly_flagged_only_above_threshold():
    with _session() as s:
        p = _product(s)
        _obs(s, p.id, 'Heritage', 4.00, 1)
        _obs(s, p.id, 'Heritage', 4.20, 5)    # +5% -> below 15% threshold
        _obs(s, p.id, 'Heritage', 5.20, 9)    # +23.8% vs prior 4.20 -> flagged
        anomalies = detect_price_anomalies(s, threshold_pct=15.0)
    assert len(anomalies) == 1
    a = anomalies[0]
    assert a.vendor == 'Heritage'
    assert a.direction == 'up'
    assert round(a.previous_cost, 2) == 4.20
    assert round(a.latest_cost, 2) == 5.20
    assert round(a.change_pct, 1) == round((5.20 - 4.20) / 4.20 * 100, 1)


def test_summary_counts():
    with _session() as s:
        p1 = _product(s, sku='A', name='Acid')
        p2 = _product(s, sku='B', name='Bicarb')
        _obs(s, p1.id, 'Heritage', 8.0, 1)
        _obs(s, p1.id, 'PoolCorp', 7.5, 2)     # p1 multi-supplier
        _obs(s, p2.id, 'Heritage', 0.75, 1)    # p2 single supplier, no anomaly
        summary = purchasing_summary(s)
    assert summary.products_tracked == 2
    assert summary.suppliers_seen == 2          # Heritage, PoolCorp
    assert summary.multi_supplier_products == 1  # only p1
    assert summary.anomalies == 0
    assert round(summary.total_spread_per_unit, 2) == 0.50  # p1 spread 0.50, p2 spread 0
