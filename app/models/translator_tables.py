"""Universal-translator no-loss substrate + accounting backbone (Tier 0).

These tables sit one grain below the existing connector spine
(``connector_tables.py``): where ``RawSourceRecord`` stores a clean inbound
*dict*, a file-based source (QuickBooks IIF/CSV/XLSX exports) needs
**file -> row -> cell**, positional and byte-addressed, so that not one line or
word is ever discarded. QuickBooks is the first source on this substrate; any
later file source (bank feeds, payroll processors) reuses it.

Design of record: ``docs/QUICKBOOKS_TRANSLATOR_DESIGN.md``. The invariants these
tables exist to make enforceable:
  I1 verbatim-first  (SourceArtifact bytes + RawSourceRow.raw_line_text + offsets)
  I2 no silent path  (every RawSourceRow.status is explicit, incl. quarantine)
  I3 understand by TYPE  (LedgerAccount.account_type + normal_balance)
  I5 count once  (CostSourceElection elects one source per account/period/basis)

Status/role values are plain strings (matching the existing connector tables);
the allowed sets are documented inline and centralized as constants in the
translator service layer rather than DB-level enums.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


# --------------------------------------------------------------------------
# No-loss substrate: file -> row -> cell, verbatim and byte-addressed
# --------------------------------------------------------------------------

class SourceArtifact(SQLModel, table=True):
    """One uploaded export file, bytes stored untouched. The integrity anchor.

    ``status`` in: pending | parsed | reconciled | live | quarantined_artifact
    ``artifact_type`` in: iif | report_gl | report_pnl_detail | report_txn_detail
        | report_coa | report_vendor_list | report_item_list | report_payroll_summary
    ``basis`` in: accrual | cash | unknown   (first-class; stamped onto derived facts)
    ``date_locale`` in: MDY | DMY | ambiguous
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    source_slug: str = Field(index=True)
    artifact_type: str = Field(default='unknown', index=True)
    original_filename: str = ''
    file_path: str = ''                      # bytes stored untouched under UPLOAD_DIR
    file_sha256: str = Field(default='', index=True)   # I1 anchor + identical-reupload idempotency
    byte_size: int = 0
    encoding_detected: str = ''              # e.g. windows-1252 (QB exports are usually CP-1252)
    encoding_confidence: float = 0.0
    basis: str = Field(default='unknown', index=True)
    date_locale: str = 'ambiguous'
    report_meta_json: str = '{}'             # captured title-block rows / IIF !HDR (preserved, not discarded)
    connector_run_id: Optional[int] = Field(default=None, index=True)
    imported_by: str = 'system'
    status: str = Field(default='pending', index=True)
    quarantine_reason: str = ''              # e.g. encoding_failure (set when status=quarantined_artifact)
    imported_at: datetime = Field(default_factory=datetime.utcnow)


class RawSourceRow(SQLModel, table=True):
    """One physical/logical record, verbatim. The canonical no-loss unit (I1/I2).

    ``record_type`` in: data | header | subtotal | total | title | blank | control
        (QB reports interleave subtotal/total/grouping rows with data rows).
    ``status`` in: raw | classified | interpreted | excluded | superseded
        | quarantined_parse   (every row terminates in exactly one of these; I2).
    ``band`` names the section the row belongs to (an account group, or an IIF
        record type like !ACCNT / !TRNS / !SPL) so banded exports stay addressable.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    artifact_id: int = Field(index=True)
    connector_run_id: Optional[int] = Field(default=None, index=True)
    source_slug: str = Field(index=True)
    row_index: int = Field(index=True)       # 0-based position; the permanent address of this row
    raw_line_text: str = ''                  # verbatim text of the record
    byte_offset_start: int = 0               # slice back to the ORIGINAL file bytes
    byte_offset_end: int = 0
    band: str = Field(default='', index=True)
    record_type: str = Field(default='data', index=True)
    status: str = Field(default='raw', index=True)
    quarantine_reason: str = ''
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RawSourceCell(SQLModel, table=True):
    """One positional cell of a row, verbatim. Re-serialized cells must reconstruct
    ``RawSourceRow.raw_line_text`` (proves segmentation, not just bytes).

    Sensitive cells (SSN/TaxID) keep no-loss without leaking PII: the plaintext
    lives only in ``cipher_value`` (encrypted-at-rest); ``value_hash`` gives a
    round-trip check; ``raw_value`` is left blank when ``is_sensitive``.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    raw_row_id: int = Field(index=True)
    artifact_id: int = Field(index=True)
    col_index: int = 0
    header_name: str = Field(default='', index=True)
    raw_value: str = ''                      # verbatim (blank when is_sensitive)
    is_sensitive: bool = False
    cipher_value: str = ''                   # encrypted plaintext when is_sensitive
    value_hash: str = ''                     # hash for round-trip verification
    created_at: datetime = Field(default_factory=datetime.utcnow)


# --------------------------------------------------------------------------
# Accounting backbone: understand by TYPE (I3) + count once (I5)
# --------------------------------------------------------------------------

class LedgerAccount(SQLModel, table=True):
    """Chart-of-accounts entry. A dollar's meaning comes from ``account_type`` +
    ``normal_balance`` + role, never column position or display name (I3).

    ``account_type`` mirrors QuickBooks types: Income | CostOfGoodsSold | Expense
        | OtherExpense | OtherIncome | FixedAsset | Bank | AccountsPayable
        | AccountsReceivable | Equity | OtherCurrentAsset | OtherCurrentLiability
        | LongTermLiability | OtherAsset | NonPosting.
    ``normal_balance`` in: debit | credit.
    ``account_role`` (the elected cost role) in: overhead | cogs | labor
        | depreciation | revenue | capital | movement | excluded | uncategorized.
    ``is_labor_account`` / ``is_depreciation_account`` are owner-confirmed at Tier 0
        and are what keep labor and depreciation from being double-counted later.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    source_slug: str = Field(default='quickbooks', index=True)
    name: str = Field(index=True)
    account_code: str = Field(default='', index=True)   # account number, if any
    full_path: str = Field(default='', index=True)      # colon-delimited parent path
    parent_id: Optional[int] = Field(default=None, index=True)   # self-reference; no phantom parents
    account_type: str = Field(default='', index=True)
    normal_balance: str = Field(default='', index=True)
    account_role: str = Field(default='uncategorized', index=True)
    is_labor_account: bool = False
    is_depreciation_account: bool = False
    is_active: bool = True
    artifact_id: Optional[int] = Field(default=None, index=True)   # provenance
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ExpenseActual(SQLModel, table=True):
    """A cost fact at (account, period, basis) grain, landed from a QuickBooks
    source. The auditable landing spot BEFORE anything is applied to the live
    cost-of-business spine (ExpenseItem). ``amount_raw`` is the verbatim cell so
    exact-Decimal tie-outs never depend on float storage.

    ``role`` in: overhead | cogs | labor | depreciation.
    ``provenance`` in: report_provisional | iif_authoritative  (IIF line detail
        supersedes a report-provisional row for the same cell; see CostSourceElection).
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: Optional[int] = Field(default=None, index=True)
    account_code: str = Field(default='', index=True)
    account_name: str = Field(default='', index=True)
    period: str = Field(default='', index=True)
    basis: str = Field(default='accrual', index=True)
    role: str = Field(default='overhead', index=True)
    amount: float = 0.0                                # convenience/display
    amount_raw: str = ''                              # verbatim; Decimal math parses this
    provenance: str = Field(default='report_provisional', index=True)
    is_superseded: bool = Field(default=False, index=True)
    superseded_reason: str = ''
    artifact_id: Optional[int] = Field(default=None, index=True)
    source_row_id: Optional[int] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CostSourceElection(SQLModel, table=True):
    """Elects the single authoritative cost source for one (account, period, basis)
    cell (I5). Cost aggregation reads at most one non-superseded source per cell,
    so a dollar can never be counted twice (e.g. report total vs IIF line detail).

    ``elected_source`` in: report_provisional | iif_authoritative | payroll.
    ``period`` is a period key (e.g. 'YYYY-MM', 'YYYY', or a trailing-12 label).
    ``basis`` in: accrual | cash.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(index=True)
    period: str = Field(default='', index=True)
    basis: str = Field(default='accrual', index=True)
    elected_source: str = Field(default='report_provisional', index=True)
    superseded: bool = Field(default=False, index=True)
    superseded_reason: str = ''
    notes: str = ''
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
