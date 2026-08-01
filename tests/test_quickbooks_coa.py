"""QuickBooks Chart-of-Accounts translator (Tier 0): IIF !ACCNT -> LedgerAccount.

Fixture mirrors real QuickBooks IIF: CRLF line endings, the full 14-column
!ACCNT header, mixed account types, a VEND band, and a deliberately broken
account (missing ACCNTTYPE) to prove it quarantines instead of dropping.
"""
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

import app.models  # noqa: F401
from app.connectors.base import run_translation
from app.connectors.quickbooks.coa import ChartOfAccountsTranslator
from app.models.translator_tables import LedgerAccount, RawSourceRow, SourceArtifact

_ACCNT_HDR = ('!ACCNT\tNAME\tREFNUM\tTIMESTAMP\tACCNTTYPE\tOBAMOUNT\tDESC\t'
              'ACCNUM\tSCD\tBANKNUM\tEXTRA\tHIDDEN\tDELCOUNT\tUSEID')


def _accnt(name, accnttype, accnum='', hidden=''):
    # index: 0 ACCNT,1 NAME,2 REFNUM,3 TIMESTAMP,4 ACCNTTYPE,5 OBAMOUNT,6 DESC,
    #        7 ACCNUM,8 SCD,9 BANKNUM,10 EXTRA,11 HIDDEN,12 DELCOUNT,13 USEID
    cols = ['ACCNT', name, '1', '0', accnttype, '0.00', '', accnum, '', '', '', hidden, '0', 'N']
    return '\t'.join(cols)


def _iif_bytes() -> bytes:
    lines = [
        '!HDR\tPROD\tVER\tREL\tIIFVER\tDATE\tTIME\tACCNTNT\tACCNTNTSPLIT',
        'HDR\tQuickBooks\tDesktop\t2021\t1\t08/01/2026\t12:00\tN\tN',
        _ACCNT_HDR,
        _accnt('General Checking', 'BANK'),
        _accnt('Service Revenue', 'INC', '4000'),
        _accnt('Pool Chemicals and Supplies', 'COGS', '5000'),
        _accnt('Payroll Expenses', 'EXP', '6000'),
        _accnt('Depreciation Expense', 'EXP', '6100'),
        _accnt('Rent Expense', 'EXP', '6200'),
        _accnt('Chemicals:Chlorine Tabs', 'EXP', '5100'),   # sub-account (colon path)
        _accnt('BrokenAcct', '', '9999'),                    # missing ACCNTTYPE -> quarantine
        '!VEND\tNAME\tREFNUM\tTIMESTAMP',
        'VEND\tPoolCorp\t2\t0',
        '',                                                  # trailing blank
    ]
    return ('\r\n'.join(lines)).encode('cp1252')


def _run():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    s = Session(engine)
    art = SourceArtifact(source_slug='quickbooks', artifact_type='iif')
    s.add(art); s.commit(); s.refresh(art)
    raw = _iif_bytes()
    summary = run_translation(s, art, raw, ChartOfAccountsTranslator())
    return s, art, raw, summary


def test_byte_anchored_round_trip_holds_with_crlf():
    s, art, raw, _ = _run()
    rows = s.exec(select(RawSourceRow).where(RawSourceRow.artifact_id == art.id)).all()
    for r in rows:
        # slice the ORIGINAL bytes; must decode back to the stored verbatim line (I1)
        assert raw[r.byte_offset_start:r.byte_offset_end].decode('cp1252') == r.raw_line_text


def test_accounts_get_type_and_normal_balance():
    s, art, raw, summary = _run()
    accts = {a.full_path: a for a in s.exec(select(LedgerAccount)).all()}
    assert len(accts) == 7                       # 7 valid ACCNT rows; BrokenAcct excluded
    assert accts['General Checking'].account_type == 'Bank'
    assert accts['General Checking'].normal_balance == 'debit'
    assert accts['General Checking'].account_role == 'excluded'      # asset, not a cost
    assert accts['Service Revenue'].account_type == 'Income'
    assert accts['Service Revenue'].account_role == 'revenue'         # FreshBooks owns revenue
    assert accts['Pool Chemicals and Supplies'].account_role == 'cogs'
    # every account has BOTH a type and a normal balance (the Tier 0 guarantee)
    for a in accts.values():
        assert a.account_type and a.normal_balance


def test_labor_and_depreciation_flags_proposed():
    s, art, raw, _ = _run()
    accts = {a.full_path: a for a in s.exec(select(LedgerAccount)).all()}
    assert accts['Payroll Expenses'].is_labor_account is True
    assert accts['Payroll Expenses'].account_role == 'labor'
    assert accts['Depreciation Expense'].is_depreciation_account is True
    assert accts['Depreciation Expense'].account_role == 'depreciation'
    assert accts['Rent Expense'].account_role == 'overhead'


def test_subaccount_full_path_and_leaf():
    s, art, raw, _ = _run()
    sub = s.exec(select(LedgerAccount).where(LedgerAccount.full_path == 'Chemicals:Chlorine Tabs')).first()
    assert sub is not None
    assert sub.name == 'Chlorine Tabs'           # leaf name
    assert sub.account_type == 'Expense'


def test_broken_account_quarantined_not_dropped():
    s, art, raw, summary = _run()
    broken = s.exec(select(RawSourceRow).where(RawSourceRow.raw_line_text.contains('BrokenAcct'))).first()
    assert broken.status == 'quarantined_parse'
    assert 'ACCNTTYPE' in broken.quarantine_reason
    assert summary['quarantined_parse'] == 1
    # and no LedgerAccount was created for it
    assert s.exec(select(LedgerAccount).where(LedgerAccount.name == 'BrokenAcct')).first() is None


def test_vendor_and_headers_retained_but_excluded():
    s, art, raw, _ = _run()
    vend = s.exec(select(RawSourceRow).where(RawSourceRow.band == 'VEND',
                                             RawSourceRow.record_type == 'data')).first()
    assert vend.status == 'excluded'
    assert vend.quarantine_reason == 'deferred_to_tier2_vendors'
    headers = s.exec(select(RawSourceRow).where(RawSourceRow.record_type == 'header')).all()
    assert headers and all(h.status == 'excluded' and h.quarantine_reason == 'iif_header' for h in headers)


def test_every_row_reaches_terminal_status():
    s, art, raw, summary = _run()
    rows = s.exec(select(RawSourceRow).where(RawSourceRow.artifact_id == art.id)).all()
    assert all(r.status in {'interpreted', 'excluded', 'superseded', 'quarantined_parse'} for r in rows)
    assert summary['interpreted'] == 7
