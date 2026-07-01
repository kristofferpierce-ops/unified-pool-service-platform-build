"""True cost-of-doing-business ($/hour) engine.

Answers a single operational question: what does one billable field hour
actually cost us, fully loaded? This is the foundation every downstream margin
calculation stands on (job P&L, route profitability, break-even bill rates).

It composes the already-verified building blocks rather than reinventing them:
  - burdened_labor_rate()          (app.services.estimator)  wage + payroll + benefits
  - overhead_per_billable_hour()   (app.services.expenses)   annual overhead / capacity
  - ExpenseItem rows               (the Admin Costs editor)  the overhead spine

The cost stack it produces:
    direct wage
      + payroll tax burden
      + benefits burden
      = burdened wage
      + overhead per billable hour   (all ExpenseItem annual costs / annual capacity)
      = TRUE cost per billable hour
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from sqlmodel import Session

from app.services.estimator import LaborSettings, burdened_labor_rate
from app.services.expenses import annual_overhead_total, list_expenses, overhead_per_billable_hour
from app.services.system_settings import get_setting


def load_labor_settings(session: Session) -> LaborSettings:
    """Stored admin labor settings, falling back to defaults for any missing key."""
    payload = get_setting(session, 'labor_settings', None) or {}
    return LaborSettings(**{**asdict(LaborSettings()), **payload})


def workers_comp_annual(session: Session) -> float:
    """Annual workers-comp cost, called out from the expense list when present."""
    total = 0.0
    for item in list_expenses(session):
        name = (item.name or '').lower().replace(' ', '_')
        if 'workers_comp' in name or 'workers_compensation' in name:
            total += item.annual_cost
    return total


@dataclass
class CostOfBusiness:
    """Fully-loaded cost of one billable field hour, with its breakdown."""

    # Inputs echoed back
    tech_hourly_wage: float
    payroll_tax_burden_pct: float
    benefits_burden_pct: float
    billable_hours_per_tech_per_year: float
    number_of_route_techs: int

    # Per-billable-hour cost stack
    payroll_tax_per_hour: float
    benefits_per_hour: float
    burdened_wage_per_hour: float
    overhead_per_hour: float
    true_cost_per_hour: float

    # Annual context
    annual_billable_capacity: float
    annual_overhead_total: float
    workers_comp_annual: float
    workers_comp_per_hour: float

    # Optional target-margin outputs (populated when a margin is supplied)
    target_margin_pct: float = 0.0
    break_even_bill_rate: float = 0.0

    stack: list = field(default_factory=list)  # ordered [(label, per_hour_$), ...] for display


def compute_cost_of_business(
    session: Session,
    settings: LaborSettings | None = None,
    target_margin_pct: float = 0.0,
) -> CostOfBusiness:
    """Compute the fully-loaded $/billable-hour from labor settings + expenses.

    Pass ``settings`` to model what-if inputs; otherwise the stored admin
    labor settings are used. ``target_margin_pct`` (margin as a % of the sell
    price) yields the break-even bill rate needed to hit that margin.
    """
    settings = settings or load_labor_settings(session)

    wage = settings.tech_hourly_wage
    payroll_tax_per_hour = wage * settings.payroll_tax_burden_pct / 100.0
    benefits_per_hour = wage * settings.benefits_burden_pct / 100.0
    burdened_wage = burdened_labor_rate(settings)  # wage * (1 + payroll% + benefits%)

    overhead_per_hour = overhead_per_billable_hour(
        session,
        billable_hours_per_year=settings.billable_hours_per_tech_per_year,
        number_of_route_techs=settings.number_of_route_techs,
    )
    true_cost = burdened_wage + overhead_per_hour

    capacity = max(1.0, settings.billable_hours_per_tech_per_year * settings.number_of_route_techs)
    wc_annual = workers_comp_annual(session)
    wc_per_hour = wc_annual / capacity

    break_even = 0.0
    if target_margin_pct and target_margin_pct < 100.0:
        break_even = true_cost / (1.0 - target_margin_pct / 100.0)

    stack = [
        ('Direct wage', wage),
        ('Payroll tax burden', payroll_tax_per_hour),
        ('Benefits burden', benefits_per_hour),
        ('Overhead (all expenses)', overhead_per_hour),
    ]

    return CostOfBusiness(
        tech_hourly_wage=wage,
        payroll_tax_burden_pct=settings.payroll_tax_burden_pct,
        benefits_burden_pct=settings.benefits_burden_pct,
        billable_hours_per_tech_per_year=settings.billable_hours_per_tech_per_year,
        number_of_route_techs=settings.number_of_route_techs,
        payroll_tax_per_hour=payroll_tax_per_hour,
        benefits_per_hour=benefits_per_hour,
        burdened_wage_per_hour=burdened_wage,
        overhead_per_hour=overhead_per_hour,
        true_cost_per_hour=true_cost,
        annual_billable_capacity=capacity,
        annual_overhead_total=annual_overhead_total(session),
        workers_comp_annual=wc_annual,
        workers_comp_per_hour=wc_per_hour,
        target_margin_pct=target_margin_pct,
        break_even_bill_rate=break_even,
        stack=stack,
    )
