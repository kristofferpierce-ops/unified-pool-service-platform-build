"""QuickBooks Desktop translators. Importing this package registers them.

QuickBooks is the authoritative COST base for the platform. Revenue stays owned
by FreshBooks, so QuickBooks income accounts are classified 'revenue' and
excluded from cost aggregation to prevent double-counting.
"""
from app.connectors.base import registry
from app.connectors.quickbooks.coa import ChartOfAccountsTranslator
from app.connectors.quickbooks.pnl import ProfitAndLossTranslator

registry.register(ChartOfAccountsTranslator())
registry.register(ProfitAndLossTranslator())

__all__ = ['ChartOfAccountsTranslator', 'ProfitAndLossTranslator']
