"""Translator framework driver: verbatim-first (I1) + no-silent-path (I2)."""
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

import app.models  # noqa: F401
from app.connectors.base import (
    BaseTranslator,
    ClassifyResult,
    InterpretResult,
    TokenizedCell,
    TokenizedRow,
    TranslatorRegistry,
    run_translation,
)
from app.models.translator_tables import RawSourceCell, RawSourceRow, SourceArtifact


def _session() -> Session:
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    return Session(engine)


class _DummyTranslator(BaseTranslator):
    """3 rows: one data (interpreted), one subtotal (skipped -> excluded),
    one 'poison' data row whose interpret raises (must quarantine, not drop)."""
    source_slug = 'quickbooks'
    artifact_types = ('report_coa',)

    def tokenize(self, raw_bytes, artifact):
        lines = raw_bytes.decode('utf-8').split('\n')
        rows, offset = [], 0
        for i, line in enumerate(lines):
            b = line.encode('utf-8')
            rows.append(TokenizedRow(
                row_index=i, raw_line_text=line,
                byte_offset_start=offset, byte_offset_end=offset + len(b),
                cells=[TokenizedCell(col_index=j, raw_value=v) for j, v in enumerate(line.split('\t'))],
            ))
            offset += len(b) + 1  # +1 for the '\n'
        return rows

    def classify(self, row, cells):
        if row.raw_line_text.startswith('Total'):
            return ClassifyResult(record_type='subtotal', skip_interpret=True, reason='control_row')
        return ClassifyResult(record_type='data')

    def interpret(self, session, row, cells):
        if 'POISON' in row.raw_line_text:
            raise ValueError('intentional parse failure')
        return InterpretResult(status='interpreted')


def test_verbatim_rows_and_cells_persist_before_interpret():
    raw = b'Chlorine\tExpense\t100.00\nTotal Chemicals\t\t100.00'
    with _session() as s:
        art = SourceArtifact(source_slug='quickbooks', artifact_type='report_coa')
        s.add(art); s.commit(); s.refresh(art)
        summary = run_translation(s, art, raw, _DummyTranslator())

        rows = s.exec(select(RawSourceRow).where(RawSourceRow.artifact_id == art.id)
                      .order_by(RawSourceRow.row_index)).all()
        assert len(rows) == 2
        # byte offsets slice back to the ORIGINAL bytes verbatim (I1)
        for r in rows:
            assert raw[r.byte_offset_start:r.byte_offset_end].decode('utf-8') == r.raw_line_text
        # cells were stored for every row
        assert s.exec(select(RawSourceCell)).all()
        assert summary['rows'] == 2


def test_exception_quarantines_row_never_drops_it():
    # The poison row must NOT vanish; it must land in quarantined_parse (I2).
    raw = b'GoodAcct\tExpense\t10\nPOISON\tExpense\t20\nGoodAcct2\tExpense\t30'
    with _session() as s:
        art = SourceArtifact(source_slug='quickbooks', artifact_type='report_coa')
        s.add(art); s.commit(); s.refresh(art)
        summary = run_translation(s, art, raw, _DummyTranslator())

        rows = s.exec(select(RawSourceRow).where(RawSourceRow.artifact_id == art.id)).all()
        assert len(rows) == 3                      # no row dropped
        by_status = {}
        for r in rows:
            by_status.setdefault(r.status, []).append(r)
        assert summary['interpreted'] == 2
        assert summary['quarantined_parse'] == 1
        poison = by_status['quarantined_parse'][0]
        assert 'POISON' in poison.raw_line_text    # the exact offending line is preserved
        assert 'ValueError' in poison.quarantine_reason


def test_control_row_excluded_not_interpreted_not_lost():
    raw = b'Chlorine\tExpense\t100\nTotal Chemicals\t\t100'
    with _session() as s:
        art = SourceArtifact(source_slug='quickbooks', artifact_type='report_coa')
        s.add(art); s.commit(); s.refresh(art)
        summary = run_translation(s, art, raw, _DummyTranslator())
        assert summary['interpreted'] == 1
        assert summary['excluded'] == 1           # the Total row: retained, reason-coded, not applied
        total_row = s.exec(select(RawSourceRow).where(RawSourceRow.record_type == 'subtotal')).first()
        assert total_row.status == 'excluded'
        assert total_row.quarantine_reason == 'control_row'


def test_every_row_reaches_terminal_status():
    raw = b'a\tExpense\t1\nTotal\t\t1\nPOISON\tExpense\t2\nb\tExpense\t3'
    with _session() as s:
        art = SourceArtifact(source_slug='quickbooks', artifact_type='report_coa')
        s.add(art); s.commit(); s.refresh(art)
        summary = run_translation(s, art, raw, _DummyTranslator())
        rows = s.exec(select(RawSourceRow).where(RawSourceRow.artifact_id == art.id)).all()
        # post-condition already asserted inside run_translation; re-check here
        assert all(r.status in {'interpreted', 'excluded', 'superseded', 'quarantined_parse'} for r in rows)
        assert summary['rows'] == 4


def test_registry_resolves_by_source_and_artifact_type():
    reg = TranslatorRegistry()
    t = _DummyTranslator()
    reg.register(t)
    assert reg.resolve('quickbooks', 'report_coa') is t
    assert reg.resolve('quickbooks', 'report_gl') is None
    assert reg.resolve('other', 'report_coa') is None
