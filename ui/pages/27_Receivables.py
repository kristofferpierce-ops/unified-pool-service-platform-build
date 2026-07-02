from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import streamlit as st

from ui._shared import configure_page, db_session, page_header, section
from app.services.accounts_receivable import accounts_receivable

configure_page('Receivables', icon='💰')
page_header(
    'Accounts Receivable',
    'What customers owe you, aged by how long the invoice has been outstanding. Freshly-issued recurring '
    'bills sit in the 0-30 (current) bucket and usually auto-pay within days — focus collections on 31+.',
    icon='💰',
)

with db_session() as session:
    ar = accounts_receivable(session)

m1, m2, m3, m4 = st.columns(4)
m1.metric('Total outstanding', f'${ar.total_outstanding:,.2f}', help=f'{ar.invoice_count} unpaid invoices.')
m2.metric('Current (0–30 days)', f'${ar.current:,.2f}', help='Includes fresh recurring bills that typically auto-pay soon.')
m3.metric('Aged (31+ days)', f'${ar.aged:,.2f}', help='The real collections focus.')
m4.metric('% aged', f'{(ar.aged/ar.total_outstanding*100 if ar.total_outstanding else 0):.0f}%')

if ar.total_outstanding == 0:
    st.success('Nothing outstanding — everything is collected.')
else:
    section('Aging', 'Outstanding balance by age. The 0-30 bucket is mostly recurring bills mid-cycle.')
    st.dataframe(pd.DataFrame([
        {'Bucket': b, 'Invoices': n, 'Amount': round(amt, 2),
         '% of A/R': round(amt / ar.total_outstanding * 100, 1)}
        for (b, n, amt) in ar.buckets
    ]), width='stretch', hide_index=True)

    section('Who owes you', 'Sortable by any column. Click "Amount" or "Oldest days" to prioritize your calls.')
    only_aged = st.checkbox('Show only customers with aged (31+ day) balances', value=False)
    rows = []
    for c in ar.customers:
        if only_aged and c.oldest_days <= 30:
            continue
        rows.append({
            'Customer': c.name,
            'Outstanding': round(c.amount, 2),
            'Invoices': c.invoices,
            'Oldest (days)': c.oldest_days,
        })
    if rows:
        st.dataframe(pd.DataFrame(rows), width='stretch', hide_index=True)
    else:
        st.caption('No customers match the filter.')

    st.caption('Aged by invoice issue date (FreshBooks due dates not stored yet). Partial-payment balances '
               'show the full invoice total. If today is the 1st, expect the current bucket to be large — '
               'that is this month\'s recurring batch, not a collections problem.')
