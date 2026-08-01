"""Tier 1 costing: reconcile imported P&L cost to the report's own totals, and
preview the cost-per-hour it would produce -- WITHOUT applying to the live
ExpenseItem spine (that apply is gated on the clean-period file + owner sign-off).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from sqlmodel import Session, select

from app.connectors.quickbooks.csv_report import parse_money
from app.models.connector_tables import ApplyEvent
from app.models.tables import ExpenseItem
from app.models.translator_tables import ExpenseActual, RawSourceCell, RawSourceRow
from app.services.cost_of_business import compute_cost_of_business, load_labor_settings
from app.services.estimator import burdened_labor_rate
from app.services.system_settings import set_setting
from app.utils.serialization import dumps

_EXPENSE_SECTION_ROLES = {'overhead', 'labor', 'depreciation'}   # QB "Expense" section
_OVERHEAD_ROLES = {'overhead', 'depreciation'}                    # what feeds overhead-per-hour


@dataclass
class ReconCheck:
    label: str
    imported: float
    control: float
    diff: float
    ok: bool


@dataclass
class ReconResult:
    checks: list = field(default_factory=list)   # list[ReconCheck]
    all_ok: bool = True


def _control_totals(session: Session, artifact_id: int) -> dict:
    """Read the P&L Total/subtotal control rows (retained, reason=control_total)."""
    rows = session.exec(
        select(RawSourceRow).where(
            RawSourceRow.artifact_id == artifact_id,
            RawSourceRow.quarantine_reason == 'control_total',
        )
    ).all()
    totals: dict = {}
    for r in rows:
        cells = session.exec(
            select(RawSourceCell).where(RawSourceCell.raw_row_id == r.id).order_by(RawSourceCell.col_index)
        ).all()
        if len(cells) < 2:
            continue
        name = cells[0].raw_value.strip()
        try:
            totals[name] = parse_money(cells[1].raw_value)
        except ValueError:
            continue
    return totals


def _sum_actuals(session: Session, artifact_id: int, roles: set) -> Decimal:
    total = Decimal('0')
    rows = session.exec(
        select(ExpenseActual).where(
            ExpenseActual.artifact_id == artifact_id,
            ExpenseActual.is_superseded == False,  # noqa: E712
        )
    ).all()
    for ea in rows:
        if ea.role in roles:
            total += parse_money(ea.amount_raw)
    return total


def reconcile_pnl(session: Session, artifact_id: int, tol_per_line: Decimal = Decimal('0.01')) -> ReconResult:
    """Prove nothing was lost: imported cost per section == the P&L's own control
    totals, in exact Decimal. Any breach fails the check (routes to review)."""
    controls = _control_totals(session, artifact_id)
    n = session.exec(
        select(ExpenseActual).where(ExpenseActual.artifact_id == artifact_id)
    ).all()
    tol = tol_per_line * max(1, len(n))

    result = ReconResult()
    pairs = [
        ('COGS', {'cogs'}, 'Total COGS'),
        ('Expense', _EXPENSE_SECTION_ROLES, 'Total Expense'),
    ]
    for label, roles, control_key in pairs:
        if control_key not in controls:
            continue
        imported = _sum_actuals(session, artifact_id, roles)
        control = controls[control_key]
        diff = imported - control
        ok = abs(diff) <= tol
        result.checks.append(ReconCheck(label, float(imported), float(control), float(diff), ok))
        if not ok:
            result.all_ok = False
    return result


@dataclass
class CostPreview:
    overhead_annual: float
    labor_annual: float
    cogs_annual: float
    annual_capacity: float
    burdened_wage_per_hour: float
    overhead_per_hour: float
    preview_true_cost_per_hour: float
    current_seeded_true_cost_per_hour: float


def overhead_cost_preview(session: Session, artifact_id: int) -> CostPreview:
    """Preview the cost-per-hour the imported overhead would produce, beside the
    current seeded number -- for owner sign-off. Does NOT write ExpenseItem."""
    overhead_annual = float(_sum_actuals(session, artifact_id, _OVERHEAD_ROLES))
    labor_annual = float(_sum_actuals(session, artifact_id, {'labor'}))
    cogs_annual = float(_sum_actuals(session, artifact_id, {'cogs'}))

    settings = load_labor_settings(session)
    capacity = max(1.0, settings.billable_hours_per_tech_per_year * settings.number_of_route_techs)
    burdened_wage = burdened_labor_rate(settings)
    overhead_per_hour = overhead_annual / capacity
    preview = burdened_wage + overhead_per_hour
    current = compute_cost_of_business(session).true_cost_per_hour

    return CostPreview(
        overhead_annual=overhead_annual,
        labor_annual=labor_annual,
        cogs_annual=cogs_annual,
        annual_capacity=capacity,
        burdened_wage_per_hour=burdened_wage,
        overhead_per_hour=overhead_per_hour,
        preview_true_cost_per_hour=preview,
        current_seeded_true_cost_per_hour=current,
    )


@dataclass
class ApplyResult:
    before_true_cost_per_hour: float
    after_true_cost_per_hour: float
    overhead_annual: float
    labor_annual: float
    labor_per_hour: float
    overhead_per_hour: float
    billable_hours_per_year: float
    number_of_techs: int
    overhead_items_written: int
    apply_event_id: int


def apply_quickbooks_costing(
    session: Session,
    *,
    artifact_id: int,
    billable_hours_per_year: float,
    number_of_techs: int,
    period_label: str = 'FY',
    applied_by: str = 'owner',
) -> ApplyResult:
    """Apply the reconciled QuickBooks cost base to the live cost-of-business engine.

    This is the GATED apply (owner sign-off is the gate). It:
      1. replaces the ExpenseItem overhead spine with the real QB overhead +
         depreciation accounts (QB is the authoritative cost base),
      2. sets LaborSettings from QB labor (already fully burdened -> 0 extra burden)
         and the owner-supplied billable-hours capacity (provisional until Skimmer),
      3. records an ApplyEvent for audit + reversibility.

    COGS/materials are deliberately NOT loaded here -- they attribute per-job (Tier
    2/3), not per billable hour. Re-running supersedes cleanly (delete-then-write).
    """
    before = compute_cost_of_business(session).true_cost_per_hour

    actuals = session.exec(
        select(ExpenseActual).where(
            ExpenseActual.artifact_id == artifact_id,
            ExpenseActual.is_superseded == False,  # noqa: E712
        )
    ).all()
    overhead_items = [ea for ea in actuals if ea.role in _OVERHEAD_ROLES]
    overhead_annual = float(sum(parse_money(ea.amount_raw) for ea in overhead_items))
    labor_annual = float(sum(parse_money(ea.amount_raw) for ea in actuals if ea.role == 'labor'))

    # 1. Replace the overhead spine with QB actuals (authoritative, complete).
    for item in session.exec(select(ExpenseItem)).all():
        session.delete(item)
    category = f'QuickBooks {period_label}'
    for ea in overhead_items:
        session.add(ExpenseItem(
            category=category,
            name=ea.account_name,
            annual_cost=float(parse_money(ea.amount_raw)),
            notes=f'QB {period_label} accrual; provisional (provenance {ea.provenance})',
        ))

    # 2. Labor + capacity into LaborSettings. QB labor is already fully burdened
    #    (wages + payroll taxes + bonus), so burden %s are 0 and the "wage" is the
    #    loaded labor cost per billable hour.
    bhpy = max(1.0, float(billable_hours_per_year))
    hrs_per_tech = bhpy / max(1, number_of_techs)
    labor_per_hour = labor_annual / bhpy
    set_setting(session, 'labor_settings', {
        'tech_hourly_wage': round(labor_per_hour, 4),
        'payroll_tax_burden_pct': 0.0,
        'benefits_burden_pct': 0.0,
        'billable_hours_per_tech_per_year': round(hrs_per_tech, 2),
        'number_of_route_techs': number_of_techs,
    }, description=f'QuickBooks {period_label} derived; billable hours provisional (pending Skimmer)')
    session.commit()

    after = compute_cost_of_business(session)

    # 3. Gated-apply audit record.
    details = {
        'source': 'quickbooks', 'period': period_label, 'applied_by': applied_by,
        'overhead_annual': overhead_annual, 'labor_annual': labor_annual,
        'billable_hours_per_year': bhpy, 'number_of_techs': number_of_techs,
        'before_true_cost_per_hour': before, 'after_true_cost_per_hour': after.true_cost_per_hour,
        'billable_hours_basis': 'owner-estimate (provisional, pending Skimmer visit durations)',
    }
    event = ApplyEvent(
        normalized_record_id=0, target_type='cost_of_business', target_ref=period_label,
        outcome='applied', details_json=dumps(details),
    )
    session.add(event)
    session.commit()
    session.refresh(event)

    return ApplyResult(
        before_true_cost_per_hour=before,
        after_true_cost_per_hour=after.true_cost_per_hour,
        overhead_annual=overhead_annual,
        labor_annual=labor_annual,
        labor_per_hour=labor_per_hour,
        overhead_per_hour=after.overhead_per_hour,
        billable_hours_per_year=bhpy,
        number_of_techs=number_of_techs,
        overhead_items_written=len(overhead_items),
        apply_event_id=event.id,
    )
