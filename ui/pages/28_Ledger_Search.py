from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from ui._shared import configure_page, db_session, page_header
from app.services.ledger_search import search_ledger

configure_page('Ledger Search', icon='🔎')
page_header(
    'Cross-Vendor Ledger Search',
    'Search an item, part number, or invoice number and see it across every vendor '
    '- price, vendor, date, and invoice all in one place.',
    icon='🔎',
)

query = st.text_input('Search', placeholder='e.g.  FloPro   ·   022056   ·   0026667528')

if query.strip():
    with db_session() as session:
        results = search_ledger(session, query)
    products, invoices = results['products'], results['invoices']
    st.caption(f"{len(products)} product match(es) · {len(invoices)} invoice match(es)")

    if products:
        st.subheader('Products')
    for hit in products:
        with st.container(border=True):
            st.markdown(f"**{hit.name}**")
            st.caption(f"MFG # `{hit.mfg_no or '—'}` · SKU `{hit.sku}` · {hit.product_family}")
            if len(hit.vendors) > 1:
                st.success(
                    f"Cheapest: **{hit.best_vendor}** at ${hit.best_cost:,.2f} · "
                    f"{hit.spread_pct:.0f}% spread across {len(hit.vendors)} vendors"
                )
            elif hit.vendors:
                st.caption(f"Only vendor so far: {hit.vendors[0]}")
            st.dataframe(
                pd.DataFrame([{
                    'Vendor': p.vendor, 'Cost': p.unit_cost, 'Pack': p.pack_size,
                    'Date': p.effective_date, 'Invoice': p.invoice_no,
                } for p in hit.points]),
                hide_index=True, width='stretch',
                column_config={'Cost': st.column_config.NumberColumn(format='$%.3f')},
            )

    if invoices:
        st.subheader('Invoices')
    for inv in invoices:
        with st.container(border=True):
            st.markdown(f"**Invoice {inv.invoice_no}** · {inv.vendor} · {inv.line_count} line(s)")
            st.dataframe(
                pd.DataFrame([{'Item': name, 'Cost': cost, 'Pack': pack} for (name, cost, pack) in inv.lines]),
                hide_index=True, width='stretch',
                column_config={'Cost': st.column_config.NumberColumn(format='$%.2f')},
            )

    if not products and not invoices:
        st.info('No matches. Try a product name, a manufacturer part number, or an invoice number.')
