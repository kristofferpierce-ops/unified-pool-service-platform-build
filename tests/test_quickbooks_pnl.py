"""QuickBooks P&L translator (Tier 1): account rows -> ExpenseActual, reconciled
to the report's own control totals; revenue excluded; unknown accounts quarantined.
"""
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

import app.models  # noqa: F401
from app.connectors.base import run_translation
from app.connectors.quickbooks.coa import apply_confirmed_account_roles
from app.connectors.quickbooks.pnl import ProfitAndLossTranslator
from app.connectors.quickbooks.csv_report import parse_money
from app.models.translator_tables import ExpenseActual, LedgerAccount, RawSourceRow, SourceArtifact
from app.services.quickbooks_costing import overhead_cost_preview, reconcile_pnl

# leaf name -> (account_type, normal_balance, account_role, is_labor, is_dep)
_SEED = [
    ('Service Revenue', 'Income', 'credit', 'revenue', False, False),
    ('Pool Chemicals and Supplies', 'CostOfGoodsSold', 'debit', 'cogs', False, False),
    ('Rent Expense', 'Expense', 'debit', 'overhead', False, False),
    ('Payroll Expenses', 'Expense', 'debit', 'labor', True, False),
    ('Payroll Processing', 'Expense', 'debit', 'labor', True, False),   # proposed labor -> overridden to overhead
    ('Depreciation Expense', 'Expense', 'debit', 'depreciation', False, True),
    ('Licenses, Permits,Other Taxes', 'Expense', 'debit', 'overhead', False, False),
]

_PNL = '\r\n'.join([
    ',"Aug 25 - Jul 26"',
    '"Ordinary Income/Expense",""',
    '"Income",""',
    '"Service Revenue",1000000.00',
    '"Total Income",1000000.00',
    '"Cost of Goods Sold",""',
    '"Pool Chemicals and Supplies",200000.00',
    '"Total COGS",200000.00',
    '"Gross Profit",800000.00',
    '"Expense",""',
    '"Rent Expense",120000.00',
    '"Payroll Expenses",400000.00',
    '"Payroll Processing",6000.00',
    '"Depreciation Expense",30000.00',
    '"Licenses, Permits,Other Taxes",5000.00',
    '"Total Expense",561000.00',
    '"Net Ordinary Income",239000.00',
    '"Net Income",239000.00',
])


def _session_with_chart() -> Session:
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    s = Session(engine)
    for name, atype, nb, role, is_labor, is_dep in _SEED:
        s.add(LedgerAccount(source_slug='quickbooks', name=name, full_path=name,
                            account_type=atype, normal_balance=nb, account_role=role,
                            is_labor_account=is_labor, is_depreciation_account=is_dep))
    s.commit()
    apply_confirmed_account_roles(s)   # Payroll Processing -> overhead
    return s


def _run(s: Session, text: str):
    art = SourceArtifact(source_slug='quickbooks', artifact_type='report_pnl')
    s.add(art); s.commit(); s.refresh(art)
    raw = text.encode('cp1252')
    summary = run_translation(s, art, raw, ProfitAndLossTranslator(period='2025-08..2026-07', basis='accrual'))
    return art, raw, summary


def test_confirmed_override_moves_payroll_processing_to_overhead():
    s = _session_with_chart()
    pp = s.exec(select(LedgerAccount).where(LedgerAccount.name == 'Payroll Processing')).first()
    assert pp.account_role == 'overhead' and pp.is_labor_account is False


def test_cost_accounts_land_as_expense_actuals_with_role():
    s = _session_with_chart()
    art, raw, summary = _run(s, _PNL)
    actuals = {a.account_name: a for a in s.exec(select(ExpenseActual)).all()}
    assert actuals['Rent Expense'].role == 'overhead'
    assert actuals['Payroll Expenses'].role == 'labor'
    assert actuals['Payroll Processing'].role == 'overhead'         # override respected
    assert actuals['Depreciation Expense'].role == 'depreciation'
    assert actuals['Pool Chemicals and Supplies'].role == 'cogs'
    # quoted-comma account name parsed as ONE account
    assert 'Licenses, Permits,Other Taxes' in actuals
    assert actuals['Licenses, Permits,Other Taxes'].amount == 5000.0
    # revenue excluded, no ExpenseActual
    assert 'Service Revenue' not in actuals


def test_revenue_row_excluded_reason():
    s = _session_with_chart()
    art, raw, _ = _run(s, _PNL)
    rev = s.exec(select(RawSourceRow).where(RawSourceRow.raw_line_text.contains('Service Revenue'),
                                            RawSourceRow.record_type == 'data')).first()
    assert rev.status == 'excluded'
    assert rev.quarantine_reason == 'revenue_owned_by_freshbooks'


def test_reconciliation_ties_to_control_totals():
    s = _session_with_chart()
    art, raw, _ = _run(s, _PNL)
    recon = reconcile_pnl(s, art.id)
    assert recon.all_ok is True
    by = {c.label: c for c in recon.checks}
    assert by['COGS'].imported == 200000.0 and by['COGS'].control == 200000.0
    assert by['Expense'].imported == 561000.0 and by['Expense'].control == 561000.0


def test_overhead_preview_excludes_labor_and_cogs():
    s = _session_with_chart()
    art, raw, _ = _run(s, _PNL)
    p = overhead_cost_preview(s, art.id)
    # overhead + depreciation only: 120000 + 6000 + 5000 + 30000
    assert p.overhead_annual == 161000.0
    assert p.labor_annual == 400000.0
    assert p.cogs_annual == 200000.0
    assert p.preview_true_cost_per_hour > p.burdened_wage_per_hour   # overhead lifts it above wage


def test_byte_roundtrip_and_all_rows_terminal():
    s = _session_with_chart()
    art, raw, summary = _run(s, _PNL)
    rows = s.exec(select(RawSourceRow).where(RawSourceRow.artifact_id == art.id)).all()
    for r in rows:
        assert raw[r.byte_offset_start:r.byte_offset_end].decode('cp1252') == r.raw_line_text
    assert all(r.status in {'interpreted', 'excluded', 'superseded', 'quarantined_parse'} for r in rows)


def test_unknown_account_quarantined_not_dropped():
    s = _session_with_chart()
    text = '\r\n'.join([
        ',"Aug 25 - Jul 26"',
        '"Expense",""',
        '"Rent Expense",120000.00',
        '"Mystery Account",999.00',
        '"Total Expense",120999.00',
        '"Net Income",1.00',
    ])
    art, raw, summary = _run(s, text)
    myst = s.exec(select(RawSourceRow).where(RawSourceRow.raw_line_text.contains('Mystery'))).first()
    assert myst.status == 'quarantined_parse'
    assert 'account_not_in_chart' in myst.quarantine_reason
    assert summary['quarantined_parse'] == 1
