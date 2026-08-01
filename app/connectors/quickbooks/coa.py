"""Chart-of-Accounts translator: IIF !ACCNT rows -> LedgerAccount.

Tier 0. This builds the account dictionary every later tier reads: type +
normal-balance (I3) and the proposed cost role, including the labor/depreciation
flags that keep those dollars from being double-counted later.

IMPORTANT: ``account_type`` and ``normal_balance`` are DETERMINISTIC from the
QuickBooks ACCNTTYPE code (high confidence). ``account_role`` /
``is_labor_account`` / ``is_depreciation_account`` are PROPOSED by keyword and
must be OWNER-CONFIRMED before any Tier 1 cost applies (that gate is downstream).
"""
from __future__ import annotations

from sqlmodel import Session

from app.connectors.base import BaseTranslator, ClassifyResult, InterpretResult
from app.connectors.quickbooks.iif import tokenize_iif
from app.models.translator_tables import LedgerAccount, SourceArtifact

# QuickBooks ACCNTTYPE code -> (platform account_type, normal_balance).
# Deterministic; normal balance follows standard accounting (assets/expenses/COGS
# are debit-normal; liabilities/equity/income are credit-normal).
ACCNTTYPE_MAP: dict = {
    'BANK':    ('Bank', 'debit'),
    'AR':      ('AccountsReceivable', 'debit'),
    'OCASSET': ('OtherCurrentAsset', 'debit'),
    'OASSET':  ('OtherAsset', 'debit'),
    'FIXASSET': ('FixedAsset', 'debit'),
    'AP':      ('AccountsPayable', 'credit'),
    'CCARD':   ('CreditCard', 'credit'),
    'OCLIAB':  ('OtherCurrentLiability', 'credit'),
    'LTLIAB':  ('LongTermLiability', 'credit'),
    'EQUITY':  ('Equity', 'credit'),
    'INC':     ('Income', 'credit'),
    'EXINC':   ('OtherIncome', 'credit'),
    'COGS':    ('CostOfGoodsSold', 'debit'),
    'EXP':     ('Expense', 'debit'),
    'EXEXP':   ('OtherExpense', 'debit'),
    'NONPOSTING': ('NonPosting', ''),
}

def _unquote(value: str) -> str:
    """Strip a matching pair of surrounding double-quotes and unescape doubled
    quotes. QuickBooks IIF quotes fields that contain commas (e.g. the account
    "Licenses, Permits,Other Taxes"); the CSV reports unquote them, so the chart
    must too or the names won't match across sources."""
    v = value.rstrip('\r').strip()
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        v = v[1:-1].replace('""', '"')
    return v


_DEPRECIATION_KW = ('depreciation', 'amortization', 'depr', 'amort')
_LABOR_KW = ('payroll', 'wage', 'salary', 'labor', 'bonus', 'commission')
_COST_TYPES = {'Expense', 'OtherExpense', 'CostOfGoodsSold'}
_REVENUE_TYPES = {'Income', 'OtherIncome'}


def propose_role(account_type: str, name: str) -> tuple[str, bool, bool]:
    """Return (account_role, is_labor_account, is_depreciation_account) PROPOSAL.

    Revenue is excluded from cost (FreshBooks owns revenue). Only cost-type
    accounts get labor/depreciation proposals; everything else (assets,
    liabilities, equity, bank, A/R, A/P) is 'excluded' from cost.
    """
    n = name.lower()
    if account_type in _REVENUE_TYPES:
        return 'revenue', False, False
    if account_type in _COST_TYPES:
        if any(k in n for k in _DEPRECIATION_KW):
            return 'depreciation', False, True
        if any(k in n for k in _LABOR_KW):
            return 'labor', True, False
        return ('cogs' if account_type == 'CostOfGoodsSold' else 'overhead'), False, False
    return 'excluded', False, False


# Owner-confirmed role corrections (2026-08-01), applied on top of the keyword
# proposal. Keyed by leaf account name. This is the human-confirmation step the
# design requires before any Tier 1 cost applies; it will move into the review UI.
CONFIRMED_ROLE_OVERRIDES: dict = {
    # (account_role, is_labor_account, is_depreciation_account)
    'Payroll Processing': ('overhead', False, False),   # a Paychex fee, not wages
    'Ask My Accountant': ('excluded', False, False),     # suspense/holding account
}


def apply_confirmed_account_roles(session: Session, overrides: dict | None = None) -> int:
    """Apply owner-confirmed role corrections to already-ingested LedgerAccounts.
    Returns the number of accounts changed."""
    from app.models.translator_tables import LedgerAccount as _LA  # local import avoids cycle
    from sqlmodel import select as _select
    overrides = CONFIRMED_ROLE_OVERRIDES if overrides is None else overrides
    changed = 0
    for acct in session.exec(_select(_LA)).all():
        ov = overrides.get(acct.name)
        if not ov:
            continue
        role, is_labor, is_dep = ov
        if (acct.account_role, acct.is_labor_account, acct.is_depreciation_account) != (role, is_labor, is_dep):
            acct.account_role = role
            acct.is_labor_account = is_labor
            acct.is_depreciation_account = is_dep
            session.add(acct)
            changed += 1
    if changed:
        session.commit()
    return changed


class ChartOfAccountsTranslator(BaseTranslator):
    source_slug = 'quickbooks'
    artifact_types = ('iif', 'report_coa')

    def tokenize(self, raw_bytes: bytes, artifact: SourceArtifact) -> list:
        rows, encoding = tokenize_iif(raw_bytes)
        artifact.encoding_detected = encoding
        return rows

    def classify(self, row, cells) -> ClassifyResult:
        # Only !ACCNT DATA rows become accounts. Every other band/row is retained
        # but not interpreted here, with an explicit reason (no row is dropped).
        if row.band == 'ACCNT' and row.record_type == 'data':
            return ClassifyResult(record_type='data', band='ACCNT')
        if row.record_type == 'header':
            return ClassifyResult(skip_interpret=True, reason='iif_header')
        if row.record_type == 'blank':
            return ClassifyResult(skip_interpret=True, reason='blank')
        if row.band == 'VEND':
            return ClassifyResult(skip_interpret=True, reason='deferred_to_tier2_vendors')
        if row.band == 'HDR':
            return ClassifyResult(skip_interpret=True, reason='iif_file_meta')
        return ClassifyResult(skip_interpret=True, reason=f'not_chart_of_accounts:{row.band or "unknown"}')

    def interpret(self, session: Session, row, cells) -> InterpretResult:
        d = {c.header_name: _unquote(c.raw_value) for c in cells if c.header_name}
        name = d.get('NAME', '').strip()
        type_code = d.get('ACCNTTYPE', '').strip()
        if not name:
            raise ValueError('ACCNT row missing NAME')
        if not type_code:
            raise ValueError(f'account "{name}" missing ACCNTTYPE')
        mapped = ACCNTTYPE_MAP.get(type_code)
        if not mapped:
            raise ValueError(f'unknown ACCNTTYPE "{type_code}" for account "{name}"')
        account_type, normal_balance = mapped

        full_path = name                    # IIF NAME is the full colon-delimited path
        leaf = name.split(':')[-1].strip()
        role, is_labor, is_dep = propose_role(account_type, leaf)
        hidden = d.get('HIDDEN', '').strip().upper() == 'Y'

        session.add(LedgerAccount(
            source_slug='quickbooks',
            name=leaf,
            full_path=full_path,
            account_code=d.get('ACCNUM', '').strip(),
            account_type=account_type,
            normal_balance=normal_balance,
            account_role=role,
            is_labor_account=is_labor,
            is_depreciation_account=is_dep,
            is_active=not hidden,
            artifact_id=row.artifact_id,
        ))
        return InterpretResult(status='interpreted')
