from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import streamlit as st

from ui._shared import configure_page, db_session, page_header, section
from app.connectors.freshbooks.client import FreshBooksAPIError, get_freshbooks_connection_status
from app.services.freshbooks_revenue import sync_freshbooks_invoices
from app.services.profitability import account_profitability

configure_page('Profitability', icon='📈')
page_header(
    'Customer Profitability',
    'Where the profit is: FreshBooks revenue minus the real cost of serving each customer '
    '(labor at true $/hour + chemicals used), joined on the matched account.',
    icon='📈',
)

# --------------------------------------------------------------------------
# Pull revenue
# --------------------------------------------------------------------------
_fb_status = get_freshbooks_connection_status()
_is_live = _fb_status.get('configured')

pull_col, note_col = st.columns([1, 3])
with pull_col:
    if st.button('Pull FreshBooks invoices', type='primary'):
        try:
            with db_session() as session:
                res = sync_freshbooks_invoices(session)
            st.session_state['fb_pull'] = res.__dict__
            st.rerun()
        except FreshBooksAPIError as exc:
            st.error(f'FreshBooks pull failed: {exc}')
with note_col:
    if _is_live:
        st.caption('🟢 **Live** — FreshBooks token + account configured. Pulls real customer invoices, resolves '
                   'each client to an account via customer matching, and lands them as revenue. Idempotent.')
    else:
        st.caption('⚪ **Fixtures** — no FreshBooks token configured yet. Pulls bundled sample invoices so the '
                   'pipeline runs. Set FRESHBOOKS_ACCESS_TOKEN + FRESHBOOKS_ACCOUNT_ID to go live.')

pull = st.session_state.get('fb_pull')
if pull:
    st.success(f"Pulled {pull['invoices_seen']} invoices ({pull.get('mode', 'fixtures')}) · "
               f"${pull['total_revenue']:,.2f} revenue · {pull['matched']} matched · {pull['documents_created']} new.")

# --------------------------------------------------------------------------
# P&L
# --------------------------------------------------------------------------
with db_session() as session:
    summary = account_profitability(session)

m1, m2, m3, m4 = st.columns(4)
m1.metric('Total revenue', f'${summary.total_revenue:,.2f}')
m2.metric('Total real cost', f'${summary.total_cost:,.2f}',
          help='Labor at true $/hour + chemical cost across all service visits.')
m3.metric('Total profit', f'${summary.total_profit:,.2f}')
m4.metric('True cost / hour', f'${summary.cost_per_hour:,.2f}',
          help='From the Cost of Doing Business engine; drives labor cost per visit.')

if not summary.accounts:
    st.info('No profitability yet. Run a Skimmer sync (cost) and pull FreshBooks invoices (revenue) — then '
            'matched accounts show their P&L here.')
else:
    section('Profit by customer', 'Sorted most to least profitable. Negative profit is flagged.')
    rows = []
    for a in summary.accounts:
        rows.append({
            'Customer': a.name,
            'Revenue': round(a.revenue, 2),
            'Labor cost': round(a.labor_cost, 2),
            'Chemical cost': round(a.chemical_cost, 2),
            'Total cost': round(a.total_cost, 2),
            'Profit': round(a.profit, 2),
            'Margin %': round(a.margin_pct, 1),
            'Visits': a.visits,
        })
    df = pd.DataFrame(rows)

    def _flag(val):
        return 'color: #b00020; font-weight: 600' if isinstance(val, (int, float)) and val < 0 else ''

    st.dataframe(df.style.map(_flag, subset=['Profit']), width='stretch', hide_index=True)

    if summary.losers:
        section('Running at a loss')
        for a in summary.losers:
            st.markdown(f'🔻 **{a.name}** — revenue ${a.revenue:,.2f}, cost ${a.total_cost:,.2f}, '
                        f'**loss ${abs(a.profit):,.2f}** across {a.visits} visits. '
                        f'{"Billed but no logged service." if a.revenue and a.visits == 0 else "Cost is outrunning what we bill."}')
    else:
        st.success('No customers are running at a loss on the data recorded so far.')

    st.caption('Note: revenue-only customers (billed, no Skimmer visits yet) show as pure profit; '
               'cost-only customers (serviced, not yet invoiced) show as a loss until revenue is pulled. '
               'As both sides fill in, the picture sharpens.')
