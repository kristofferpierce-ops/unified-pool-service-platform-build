from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import streamlit as st

from ui._shared import configure_page, db_session, page_header, section
from app.services.expenses import create_price_history
from app.services.purchasing import (
    best_source_for_product,
    list_products,
    purchasing_summary,
)

configure_page('Purchasing', icon='🛒')
page_header(
    'Purchasing Intelligence',
    'Cross-references every price we have on record to tell you the cheapest current source per product, '
    'the spread you are leaving on the table, and where a vendor just changed pricing.',
    icon='🛒',
)

with db_session() as session:
    summary = purchasing_summary(session)

# --------------------------------------------------------------------------
# Headline
# --------------------------------------------------------------------------
m1, m2, m3, m4 = st.columns(4)
m1.metric('Products tracked', summary.products_tracked, help='Products with at least one price on record.')
m2.metric('Suppliers seen', summary.suppliers_seen, help='Distinct vendors across the price ledger.')
m3.metric('Multi-supplier products', summary.multi_supplier_products,
          help='Products we have bought from more than one vendor -- where best-source matters.')
m4.metric('Price anomalies', summary.anomalies,
          help='Products where a vendor\'s latest price jumped past the threshold vs its previous price.')

if summary.products_tracked == 0:
    st.info('No price history on record yet. Record a price observation below, or ingest an invoice, and the '
            'price book, best-source recommendations, and anomaly flags will populate here.')

# --------------------------------------------------------------------------
# Best-source overview
# --------------------------------------------------------------------------
if summary.overview:
    section('Best source by product', 'Cheapest current vendor per product, with the spread across suppliers.')
    rows = []
    for bs in sorted(summary.overview, key=lambda b: b.spread_abs, reverse=True):
        rows.append({
            'Product': bs.name,
            'Unit': bs.unit,
            'Best vendor': bs.best_vendor,
            'Best $/unit': round(bs.best_unit_cost, 4),
            'Vendors': len(bs.vendors),
            'Spread $/unit': round(bs.spread_abs, 4),
            'Spread %': round(bs.spread_pct, 1),
            'Baseline $/unit': round(bs.baseline_unit_cost, 4),
        })
    st.dataframe(pd.DataFrame(rows), width='stretch', hide_index=True)

    # Per-product price book drill-down.
    section('Supplier price book')
    labels = {f'{bs.name} ({bs.sku})': bs for bs in summary.overview}
    pick = st.selectbox('Product', options=list(labels.keys()))
    chosen = labels[pick]
    book = pd.DataFrame([{
        'Vendor': v.vendor,
        'Latest $/unit': round(v.unit_cost, 4),
        'Pack size': v.pack_size,
        'As of': v.effective_date,
        'Observations': v.observations,
        'vs best': f'+{round((v.unit_cost - chosen.best_unit_cost) / chosen.best_unit_cost * 100, 1)}%'
                   if chosen.best_unit_cost and v.unit_cost > chosen.best_unit_cost else 'best',
    } for v in chosen.vendors])
    st.dataframe(book, width='stretch', hide_index=True)
    if len(chosen.vendors) > 1 and chosen.spread_abs > 0:
        st.success(f'Buy **{chosen.name}** from **{chosen.best_vendor}** at '
                   f'${chosen.best_unit_cost:,.4f}/{chosen.unit} -- '
                   f'${chosen.spread_abs:,.4f}/{chosen.unit} ({chosen.spread_pct:.1f}%) cheaper than the priciest vendor on file.')

# --------------------------------------------------------------------------
# Anomalies
# --------------------------------------------------------------------------
if summary.anomaly_list:
    section('Price anomalies', 'A vendor\'s most recent price moved sharply against its own previous price.')
    for a in summary.anomaly_list:
        arrow = '🔺' if a.direction == 'up' else '🔻'
        st.markdown(f'{arrow} **{a.name}** · {a.vendor} · '
                    f'${a.previous_cost:,.4f} → ${a.latest_cost:,.4f}  '
                    f'(`{a.change_pct:+.1f}%`, as of {a.effective_date})')

# --------------------------------------------------------------------------
# Record a price observation (feeds the same ledger invoices write to)
# --------------------------------------------------------------------------
st.divider()
with st.expander('Record a price observation'):
    with db_session() as session:
        products = list_products(session)
    if not products:
        st.caption('No products defined yet. Add products on the Admin Costs page first.')
    else:
        prod_labels = {f'{p.name} ({p.sku})': p for p in products}
        with st.form('record_price_form', clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                sel = st.selectbox('Product', options=list(prod_labels.keys()))
                vendor = st.text_input('Vendor')
            with c2:
                unit_cost = st.number_input('Unit cost ($)', min_value=0.0, step=0.01, format='%.4f')
                pack = st.text_input('Pack size', value='')
            with c3:
                eff = st.date_input('Effective date', value=date.today())
                invoice_no = st.text_input('Invoice # (optional)', value='')
            if st.form_submit_button('Record price', type='primary'):
                if not vendor.strip():
                    st.error('Vendor is required.')
                elif unit_cost <= 0:
                    st.error('Unit cost must be greater than zero.')
                else:
                    product = prod_labels[sel]
                    with db_session() as session:
                        create_price_history(
                            session,
                            product_id=product.id,
                            vendor_name=vendor.strip(),
                            invoice_number=invoice_no.strip(),
                            unit_cost=float(unit_cost),
                            pack_size=pack.strip(),
                            confidence=1.0,
                            approved_by='manual entry',
                            effective_date=eff,
                        )
                    st.success(f'Recorded {vendor.strip()} @ ${unit_cost:,.4f} for {product.name}.')
                    st.rerun()
