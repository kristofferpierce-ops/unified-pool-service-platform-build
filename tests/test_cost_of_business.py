"""Locks the true cost-of-doing-business ($/hour) math against seeded defaults."""
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

import app.models  # noqa: F401  -- registers all tables on SQLModel.metadata
from app.services.bootstrap import seed_defaults
from app.services.cost_of_business import compute_cost_of_business
from app.services.estimator import LaborSettings


def _seeded_session() -> Session:
    engine = create_engine(
        'sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    seed_defaults(session)
    return session


def test_cost_stack_matches_seeded_defaults():
    # Defaults: wage 22, payroll 10%, benefits 5%, 1500 billable hrs x 4 techs.
    # Seeded expenses total 129,300/yr; workers comp is 20,000 of that.
    with _seeded_session() as session:
        cob = compute_cost_of_business(session, target_margin_pct=40.0)

    assert cob.annual_billable_capacity == 6000.0
    assert round(cob.annual_overhead_total, 2) == 129300.0
    assert round(cob.payroll_tax_per_hour, 4) == 2.2
    assert round(cob.benefits_per_hour, 4) == 1.1
    assert round(cob.burdened_wage_per_hour, 4) == 25.30   # 22 * 1.15
    assert round(cob.overhead_per_hour, 4) == 21.55        # 129300 / 6000
    assert round(cob.true_cost_per_hour, 4) == 46.85       # 25.30 + 21.55


def test_workers_comp_called_out():
    with _seeded_session() as session:
        cob = compute_cost_of_business(session)
    assert cob.workers_comp_annual == 20000.0
    assert round(cob.workers_comp_per_hour, 4) == round(20000.0 / 6000.0, 4)


def test_break_even_bill_rate_hits_target_margin():
    with _seeded_session() as session:
        cob = compute_cost_of_business(session, target_margin_pct=40.0)
    # break-even = true_cost / (1 - margin); margin realized = 1 - cost/price
    assert round(cob.break_even_bill_rate, 4) == round(46.85 / 0.6, 4)
    realized_margin = 1.0 - cob.true_cost_per_hour / cob.break_even_bill_rate
    assert round(realized_margin * 100, 4) == 40.0


def test_whatif_settings_override_stored():
    with _seeded_session() as session:
        base = compute_cost_of_business(session)
        richer = compute_cost_of_business(
            session,
            settings=LaborSettings(
                tech_hourly_wage=30.0,
                payroll_tax_burden_pct=10.0,
                benefits_burden_pct=5.0,
                billable_hours_per_tech_per_year=1500.0,
                number_of_route_techs=4,
            ),
        )
    assert richer.burdened_wage_per_hour > base.burdened_wage_per_hour
    # Overhead per hour is unchanged (same capacity + expenses), only labor moved.
    assert round(richer.overhead_per_hour, 6) == round(base.overhead_per_hour, 6)
    assert richer.true_cost_per_hour > base.true_cost_per_hour
