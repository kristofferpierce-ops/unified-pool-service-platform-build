"""Expected-vs-actual labor variance."""
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

import app.models  # noqa: F401
from app.services.bootstrap import seed_defaults
from app.connectors.skimmer.client import SkimmerClient
from app.services.skimmer_sync import sync_skimmer
from app.services.variance import chemical_variance, labor_variance


def _session() -> Session:
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    seed_defaults(session)
    return session


def test_labor_variance_flags_overruns():
    # Fixture vessels default to 25 priced minutes. Actuals: 34, 28 (property 1),
    # 75 (property 2) -> both properties overrun.
    with _session() as s:
        sync_skimmer(s, client=SkimmerClient(use_fixtures=True))
        summary = labor_variance(s)

    assert summary.cost_per_hour > 0
    assert summary.visits_analyzed == 3
    # Total variance minutes = (34-25)+(28-25)+(75-25) = 9+3+50 = 62.
    assert round(summary.total_variance_minutes, 1) == 62.0
    assert summary.total_variance_cost > 0

    # Property 2 (single 75-min visit vs 25 priced) is the worst overrun.
    worst = summary.properties[0]
    assert worst.visits == 1
    assert round(worst.total_variance_minutes, 1) == 50.0
    assert worst.overrun

    # Both properties overrun on this fixture data.
    assert len(summary.overruns) == 2


def test_no_actuals_means_no_variance():
    with _session() as s:
        summary = labor_variance(s)   # nothing synced
    assert summary.visits_analyzed == 0
    assert summary.total_variance_minutes == 0
    assert summary.properties == []


def test_chemical_variance_expected_vs_actual():
    with _session() as s:
        sync_skimmer(s, client=SkimmerClient(use_fixtures=True))
        summary = chemical_variance(s)

    # 3 fixture visits carry chemical logs.
    assert summary.visits_analyzed == 3
    assert summary.total_actual > 0
    assert summary.total_expected > 0
    # Bookkeeping identity holds.
    assert round(summary.total_variance_cost, 4) == round(summary.total_actual - summary.total_expected, 4)
    # Every visit has an expected + actual chemical cost.
    assert all(v.expected_cost >= 0 and v.actual_cost > 0 for v in summary.visit_rows)


def test_labor_variance_period_filter():
    from datetime import date
    with _session() as s:
        sync_skimmer(s, client=SkimmerClient(use_fixtures=True))
        alltime = labor_variance(s)
        # Fixture visits are 2026-06-08/09/15; on/after 06-10 keeps only wo-5002 (06-15).
        scoped = labor_variance(s, start=date(2026, 6, 10))
    assert alltime.visits_analyzed == 3
    assert scoped.visits_analyzed == 1


def test_chemical_variance_captures_per_property_usage():
    with _session() as s:
        sync_skimmer(s, client=SkimmerClient(use_fixtures=True))
        summary = chemical_variance(s)
    sunset = next(p for p in summary.properties if 'Sunset' in p.name)
    alvarez = next(p for p in summary.properties if 'Alvarez' in p.name)
    # Sunset (6 gal chlorine + 8 lb bicarb on a big commercial pool) uses far more
    # chemical per visit than the small residential pool.
    assert sunset.avg_actual > alvarez.avg_actual
    # Signed variance identity holds per property.
    for p in summary.properties:
        assert round(p.total_variance_cost, 4) == round((p.avg_actual - p.avg_expected) * p.visits, 4)
