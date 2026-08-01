"""Universal-translator framework: the reusable four-stage ingestion skeleton.

QuickBooks is the first source plugged into this; any later file source (bank
feeds, payroll processors) subclasses ``BaseTranslator`` and registers itself.

The four stages (design ``docs/QUICKBOOKS_TRANSLATOR_DESIGN.md`` S4.1):
    tokenize   bytes         -> verbatim rows + cells (source-specific parse)
    classify   RawSourceRow  -> record_type / band (data vs subtotal/total/blank)
    interpret  RawSourceRow  -> a domain fact + a verdict (interpreted/excluded)
    apply      (later tier)  -> gated write to a cost target

The driver ``run_translation`` owns the invariants so no subclass can break them:
  I1  every row is persisted verbatim with byte offsets BEFORE any interpretation.
  I2  no silent path: classify+interpret run in a per-row try/except; a thrown
      exception lands the row in ``quarantined_parse`` (never dropped), and a hard
      post-condition asserts every row reached a terminal status. This is the
      guarantee the owner mandate ("not one line discarded") rests on, and it is
      what the banned ``skimmer_sync.py:226`` ``... += 1; continue`` pattern violated.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field

from sqlmodel import Session

from app.core.secrets import encrypt, keyed_hash, norm_sensitive
from app.models.translator_tables import RawSourceCell, RawSourceRow, SourceArtifact


# A row is "done" only in one of these states. 'raw'/'classified' are NOT terminal;
# if the driver leaves a row in either, the post-condition fails loudly.
TERMINAL_ROW_STATUSES = {'interpreted', 'excluded', 'superseded', 'quarantined_parse'}


@dataclass
class TokenizedCell:
    col_index: int
    header_name: str = ''
    raw_value: str = ''
    is_sensitive: bool = False        # SSN/TaxID: plaintext must not land in raw_value


@dataclass
class TokenizedRow:
    row_index: int
    raw_line_text: str
    byte_offset_start: int
    byte_offset_end: int
    band: str = ''
    record_type: str = 'data'
    cells: list = field(default_factory=list)   # list[TokenizedCell]


@dataclass
class ClassifyResult:
    """How the driver should treat a row. Non-data rows (subtotals, totals, blanks,
    titles) are NOT interpreted, but they are NOT lost either: they get an explicit
    terminal status ('excluded') with a reason, so the row stays queryable (I2)."""
    record_type: str = ''             # refine RawSourceRow.record_type if non-empty
    band: str = ''                    # refine band if non-empty
    skip_interpret: bool = False      # True for control rows (subtotal/total/blank/title)
    terminal_status: str = 'excluded'  # status to stamp when skip_interpret
    reason: str = 'non_data_row'


@dataclass
class InterpretResult:
    """Outcome of interpreting a data row. ``status`` is terminal: 'interpreted'
    (a fact was produced) or 'excluded' (deliberately not applied, with a reason
    e.g. an income account excluded to avoid double-counting FreshBooks revenue)."""
    status: str = 'interpreted'
    reason: str = ''


class BaseTranslator(abc.ABC):
    """Contract for a source translator. Subclasses implement the source-specific
    parse (``tokenize``) and meaning (``interpret``); ``classify`` has a data-row
    default. The driver, not the subclass, enforces persistence + the no-loss
    invariants."""

    source_slug: str = ''
    artifact_types: tuple = ()        # which SourceArtifact.artifact_type values this handles

    @abc.abstractmethod
    def tokenize(self, raw_bytes: bytes, artifact: SourceArtifact) -> list:
        """bytes -> list[TokenizedRow]. Verbatim, positional, byte-addressed. No DB."""
        raise NotImplementedError

    def classify(self, row: RawSourceRow, cells: list) -> ClassifyResult:
        """Default: treat every row as data. Override to fold out subtotal/total/
        blank/title rows into explicit non-interpreted (but retained) status."""
        return ClassifyResult()

    @abc.abstractmethod
    def interpret(self, session: Session, row: RawSourceRow, cells: list) -> InterpretResult:
        """Produce a domain fact from a data row and return a terminal verdict.
        May persist domain rows (e.g. a LedgerAccount) via ``session``."""
        raise NotImplementedError


class TranslatorRegistry:
    """Maps (source_slug, artifact_type) -> translator. QuickBooks registers its
    report/IIF translators here; the ingest route resolves by artifact type."""

    def __init__(self) -> None:
        self._by_key: dict = {}

    def register(self, translator: BaseTranslator) -> None:
        for artifact_type in translator.artifact_types:
            self._by_key[(translator.source_slug, artifact_type)] = translator

    def resolve(self, source_slug: str, artifact_type: str):
        return self._by_key.get((source_slug, artifact_type))


# Process-wide registry; translators register themselves on import.
registry = TranslatorRegistry()


def run_translation(session: Session, artifact: SourceArtifact, raw_bytes: bytes, translator: BaseTranslator) -> dict:
    """Drive one artifact through the full pipeline, enforcing I1/I2.

    Persists every tokenized row + cell verbatim first (I1), then classifies and
    interprets each row inside a per-row try/except so an exception quarantines
    the offending row instead of dropping it (I2). Finishes with a hard
    post-condition that every row reached a terminal status.
    """
    # --- I1: verbatim first. Persist rows + cells before any interpretation. ---
    persisted: list = []
    for tok in translator.tokenize(raw_bytes, artifact):
        row = RawSourceRow(
            artifact_id=artifact.id,
            connector_run_id=artifact.connector_run_id,
            source_slug=artifact.source_slug,
            row_index=tok.row_index,
            raw_line_text=tok.raw_line_text,
            byte_offset_start=tok.byte_offset_start,
            byte_offset_end=tok.byte_offset_end,
            band=tok.band,
            record_type=tok.record_type,
            status='raw',
        )
        session.add(row)
        session.flush()  # assign row.id
        cells: list = []
        for c in tok.cells:
            cipher_value, value_hash = '', ''
            if c.is_sensitive and c.raw_value:
                # No-loss for PII: the plaintext is preserved ENCRYPTED at rest
                # (never in raw_value / any query surface) plus a keyed hash for
                # dedup. Before this, a sensitive cell was blanked and its value
                # was silently lost -- a real no-loss violation.
                cipher_value = encrypt(c.raw_value)
                value_hash = keyed_hash(norm_sensitive(c.raw_value))
            cell = RawSourceCell(
                raw_row_id=row.id,
                artifact_id=artifact.id,
                col_index=c.col_index,
                header_name=c.header_name,
                raw_value='' if c.is_sensitive else c.raw_value,
                is_sensitive=c.is_sensitive,
                cipher_value=cipher_value,
                value_hash=value_hash,
            )
            session.add(cell)
            cells.append(cell)
        persisted.append((row, cells))
    session.commit()

    # --- I2: no silent path. Per-row try/except; every row ends terminal. ---
    counts: dict = {s: 0 for s in TERMINAL_ROW_STATUSES}
    for row, cells in persisted:
        try:
            decision = translator.classify(row, cells)
            if decision.record_type:
                row.record_type = decision.record_type
            if decision.band:
                row.band = decision.band
            if decision.skip_interpret:
                row.status = decision.terminal_status
                row.quarantine_reason = decision.reason
            else:
                verdict = translator.interpret(session, row, cells)
                row.status = verdict.status
                row.quarantine_reason = verdict.reason
        except Exception as exc:  # noqa: BLE001 - deliberately catch-all: a row must never vanish
            row.status = 'quarantined_parse'
            row.quarantine_reason = f'{type(exc).__name__}: {exc}'[:500]
        session.add(row)
        counts[row.status] = counts.get(row.status, 0) + 1
    session.commit()

    # --- Post-condition: not one row left non-terminal (I2). ---
    total = len(persisted)
    non_terminal = [r.id for (r, _) in persisted if r.status not in TERMINAL_ROW_STATUSES]
    if non_terminal:
        raise AssertionError(f'{len(non_terminal)} row(s) left non-terminal (I2 violated): {non_terminal[:10]}')

    return {'artifact_id': artifact.id, 'rows': total, **counts}
