"""Tier 0 no-loss substrate: tables register and enforce the verbatim spine.

These are model-layer smoke tests. Behavior (tokenize/classify/interpret,
byte-anchored round-trip, cross-foot, election) is tested with the translator.
"""
from datetime import date

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

import app.models  # noqa: F401  (registers every table, incl. translator_tables)
from app.models.translator_tables import (
    CostSourceElection,
    LedgerAccount,
    RawSourceCell,
    RawSourceRow,
    SourceArtifact,
)


def _session() -> Session:
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def test_substrate_tables_all_register():
    # If any new model failed to register, its table would be missing here.
    names = set(SQLModel.metadata.tables)
    for t in ('sourceartifact', 'rawsourcerow', 'rawsourcecell', 'ledgeraccount', 'costsourceelection'):
        assert t in names, f'missing table: {t}'


def test_verbatim_row_stores_bytes_and_offsets():
    with _session() as s:
        art = SourceArtifact(source_slug='quickbooks', artifact_type='report_coa',
                             file_sha256='abc', byte_size=42, basis='accrual')
        s.add(art); s.commit(); s.refresh(art)

        line = 'Chemicals:Chlorine\tExpense\t100.00'
        row = RawSourceRow(artifact_id=art.id, source_slug='quickbooks', row_index=0,
                           raw_line_text=line, byte_offset_start=0, byte_offset_end=len(line.encode('utf-8')),
                           band='!ACCNT', record_type='data', status='raw')
        s.add(row); s.commit(); s.refresh(row)

        # Cells re-serialize to reconstruct the verbatim line (segmentation proof).
        parts = line.split('\t')
        for i, val in enumerate(parts):
            s.add(RawSourceCell(raw_row_id=row.id, artifact_id=art.id, col_index=i, raw_value=val))
        s.commit()

        cells = s.exec(select(RawSourceCell).where(RawSourceCell.raw_row_id == row.id)
                       .order_by(RawSourceCell.col_index)).all()
        assert '\t'.join(c.raw_value for c in cells) == row.raw_line_text
        # byte offsets address back into the original bytes
        assert row.byte_offset_end - row.byte_offset_start == len(line.encode('utf-8'))


def test_row_status_defaults_are_explicit():
    # I2: every row has an explicit, queryable status; default is 'raw', never null.
    with _session() as s:
        art = SourceArtifact(source_slug='quickbooks'); s.add(art); s.commit(); s.refresh(art)
        row = RawSourceRow(artifact_id=art.id, source_slug='quickbooks', row_index=0)
        s.add(row); s.commit(); s.refresh(row)
        assert row.status == 'raw'
        assert row.quarantine_reason == ''


def test_ledger_account_carries_type_and_flags():
    # I3 + count-once backbone: type, normal balance, labor/depreciation flags.
    with _session() as s:
        acct = LedgerAccount(name='Payroll Wages', account_code='6000', account_type='Expense',
                             normal_balance='debit', is_labor_account=True, account_role='labor')
        s.add(acct); s.commit(); s.refresh(acct)
        assert acct.is_labor_account is True
        assert acct.is_depreciation_account is False
        assert acct.normal_balance == 'debit'
        assert acct.account_role == 'labor'


def test_cost_source_election_defaults_to_provisional_not_superseded():
    # I5: one elected source per (account, period, basis).
    with _session() as s:
        acct = LedgerAccount(name='Office Rent', account_type='Expense', normal_balance='debit')
        s.add(acct); s.commit(); s.refresh(acct)
        el = CostSourceElection(account_id=acct.id, period='2026-01', basis='accrual')
        s.add(el); s.commit(); s.refresh(el)
        assert el.elected_source == 'report_provisional'
        assert el.superseded is False
