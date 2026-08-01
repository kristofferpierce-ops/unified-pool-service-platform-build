"""Profit & Loss translator (Tier 1): P&L account rows -> ExpenseActual.

Reads the P&L account totals and lands each COST account (overhead / cogs / labor
/ depreciation) as an ExpenseActual at the report's (period, basis). Revenue is
excluded (FreshBooks owns it); section headers, parent-account headers, and the
Total/subtotal control rows are retained but not interpreted (they are the
reconciliation targets, never summed into cost). An account not found in the
ingested chart quarantines for review rather than being dropped.

Depends on Tier 0: the chart of accounts must be ingested (and owner-confirmed
via ``apply_confirmed_account_roles``) first, so each P&L line resolves to a
LedgerAccount whose ``account_role`` decides how the dollar is treated.
"""
from __future__ import annotations

from sqlmodel import Session, select

from app.connectors.base import BaseTranslator, ClassifyResult, InterpretResult
from app.connectors.quickbooks.csv_report import looks_like_money, parse_money, tokenize_csv
from app.models.translator_tables import ExpenseActual, LedgerAccount, SourceArtifact

# Section headers carry a name and a BLANK amount cell.
SECTION_HEADERS = {
    'Ordinary Income/Expense', 'Income', 'Cost of Goods Sold', 'Expense',
    'Other Income/Expense', 'Other Income', 'Other Expense', 'Gross Profit',
}
# Non-"Total ..." control rows.
CONTROL_NAMES = {'Gross Profit', 'Net Ordinary Income', 'Net Income', 'Net Other Income'}

_COST_ROLES = {'overhead', 'cogs', 'labor', 'depreciation'}


class ProfitAndLossTranslator(BaseTranslator):
    source_slug = 'quickbooks'
    artifact_types = ('report_pnl', 'report_pnl_detail')

    def __init__(self, period: str = '', basis: str = 'accrual') -> None:
        self.period = period
        self.basis = basis
        self._accounts_by_name: dict = {}
        self._accounts_by_path: dict = {}
        self._loaded = False

    def tokenize(self, raw_bytes: bytes, artifact: SourceArtifact) -> list:
        rows, encoding = tokenize_csv(raw_bytes)
        artifact.encoding_detected = encoding
        if self.basis:
            artifact.basis = self.basis
        return rows

    def _load_accounts(self, session: Session) -> None:
        if self._loaded:
            return
        by_name: dict = {}
        by_path: dict = {}
        for acct in session.exec(select(LedgerAccount)).all():
            by_name.setdefault(acct.name, []).append(acct)
            by_path[acct.full_path] = acct
        self._accounts_by_name = by_name
        self._accounts_by_path = by_path
        self._loaded = True

    def _resolve_account(self, name: str):
        if name in self._accounts_by_path:
            return self._accounts_by_path[name]
        hits = self._accounts_by_name.get(name, [])
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            raise ValueError(f'ambiguous account name (needs full path): "{name}"')
        return None

    def classify(self, row, cells) -> ClassifyResult:
        if row.record_type == 'blank':
            return ClassifyResult(skip_interpret=True, reason='blank')
        first = cells[0].raw_value.strip() if cells else ''
        amount = cells[1].raw_value.strip() if len(cells) > 1 else ''

        if row.row_index == 0 or first == '':
            return ClassifyResult(skip_interpret=True, reason='report_period_header')
        if first in SECTION_HEADERS:
            return ClassifyResult(skip_interpret=True, reason='section_header')
        if first.startswith('Total ') or first in CONTROL_NAMES:
            return ClassifyResult(record_type='total', skip_interpret=True, reason='control_total')
        if amount == '' or not looks_like_money(amount):
            # a name with no numeric amount = a parent-account header; its children
            # (leaf rows) carry the amounts, and "Total <parent>" is the control row.
            return ClassifyResult(skip_interpret=True, reason='parent_account_header')
        return ClassifyResult(record_type='data')

    def interpret(self, session: Session, row, cells) -> InterpretResult:
        self._load_accounts(session)
        name = cells[0].raw_value.strip()
        amount_raw = cells[1].raw_value.strip()

        account = self._resolve_account(name)
        if account is None:
            raise ValueError(f'account_not_in_chart: "{name}" (ingest chart of accounts first)')

        role = account.account_role
        if role == 'revenue':
            return InterpretResult(status='excluded', reason='revenue_owned_by_freshbooks')
        if role not in _COST_ROLES:
            return InterpretResult(status='excluded', reason=f'non_cost_account:{role}')

        value = parse_money(amount_raw)   # exact Decimal; raises -> quarantine if not money
        session.add(ExpenseActual(
            account_id=account.id,
            account_code=account.account_code,
            account_name=name,
            period=self.period,
            basis=self.basis,
            role=role,
            amount=float(value),
            amount_raw=amount_raw,
            provenance='report_provisional',
            artifact_id=row.artifact_id,
            source_row_id=row.id,
        ))
        return InterpretResult(status='interpreted')
