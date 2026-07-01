from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import streamlit as st
from sqlmodel import select

from ui._shared import configure_page, db_session, page_header, section
from app.models.tables import PoolVessel, Property
from app.services.assets import (
    ASSET_CATEGORIES,
    ASSET_STATUSES,
    asset_summary,
    create_asset,
    install_asset,
    list_assets,
    receive_asset,
    retire_asset,
)

configure_page('Assets', icon='🧰')
page_header(
    'Asset Registry',
    'Every physical asset tracked through its life: ordered → received → installed → retired, '
    'with serial/model numbers, purchase provenance, and the property it lives on.',
    icon='🧰',
)

STATUS_BADGE = {'ordered': '📦', 'received': '📥', 'installed': '✅', 'retired': '🗄️'}


def _property_label_map(session) -> dict:
    props = list(session.exec(select(Property).order_by(Property.name)).all())
    return {p.id: f'{p.name} — {p.address_line_1}, {p.city}'.strip(' —,') for p in props}


with db_session() as session:
    summary = asset_summary(session)
    prop_labels = _property_label_map(session)

# --------------------------------------------------------------------------
# Headline
# --------------------------------------------------------------------------
m1, m2, m3, m4 = st.columns(4)
m1.metric('Total assets', summary.total)
m2.metric('Installed', summary.installed_count, help='Assets currently installed at a property.')
m3.metric('Installed base value', f'${summary.installed_base_value:,.0f}',
          help='Sum of purchase cost across installed assets.')
m4.metric('Warranties expiring ≤60d', summary.warranty_expiring_soon,
          help=f'{summary.in_warranty} installed assets are in warranty; this many expire within 60 days.')

if summary.total == 0:
    st.info('No assets yet. Add one below to start tracking it through its lifecycle.')

# --------------------------------------------------------------------------
# Registry (filterable)
# --------------------------------------------------------------------------
section('Registry')
f1, f2 = st.columns(2)
with f1:
    status_filter = st.selectbox('Status', options=['(all)'] + ASSET_STATUSES)
with f2:
    category_filter = st.selectbox('Category', options=['(all)'] + ASSET_CATEGORIES)

with db_session() as session:
    assets = list_assets(
        session,
        status=None if status_filter == '(all)' else status_filter,
        category=None if category_filter == '(all)' else category_filter,
    )

if assets:
    rows = [{
        'ID': a.id,
        'Status': f'{STATUS_BADGE.get(a.status, "")} {a.status}',
        'Asset': a.name,
        'Category': a.category,
        'Mfr': a.manufacturer,
        'Model': a.model_number,
        'Serial': a.serial_number,
        'Location': prop_labels.get(a.property_id, '—') if a.property_id else '—',
        'Cost': round(a.purchase_cost, 2),
        'Warranty until': str(a.warranty_until) if a.warranty_until else '—',
    } for a in assets]
    st.dataframe(pd.DataFrame(rows), width='stretch', hide_index=True)
else:
    st.caption('No assets match the current filter.')

# --------------------------------------------------------------------------
# Per-property asset list
# --------------------------------------------------------------------------
if prop_labels:
    section('Assets by property', 'The asset list that lives in a property profile.')
    pid = st.selectbox('Property', options=list(prop_labels.keys()),
                       format_func=lambda i: prop_labels[i])
    with db_session() as session:
        prop_assets = list_assets(session, property_id=pid)
    if prop_assets:
        st.dataframe(pd.DataFrame([{
            'Status': f'{STATUS_BADGE.get(a.status, "")} {a.status}',
            'Asset': a.name, 'Category': a.category,
            'Model': a.model_number, 'Serial': a.serial_number,
            'Installed': str(a.install_date) if a.install_date else '—',
            'Warranty until': str(a.warranty_until) if a.warranty_until else '—',
        } for a in prop_assets]), width='stretch', hide_index=True)
    else:
        st.caption('No assets recorded at this property yet.')

# --------------------------------------------------------------------------
# Add an asset
# --------------------------------------------------------------------------
st.divider()
with st.expander('Add an asset'):
    with st.form('add_asset_form', clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            name = st.text_input('Name', placeholder='Pentair IntelliFlo VSF')
            category = st.selectbox('Category', options=ASSET_CATEGORIES)
        with c2:
            manufacturer = st.text_input('Manufacturer')
            model_number = st.text_input('Model #')
            serial_number = st.text_input('Serial #')
        with c3:
            vendor = st.text_input('Vendor')
            purchase_cost = st.number_input('Purchase cost ($)', min_value=0.0, step=10.0)
            purchase_dt = st.date_input('Purchase date', value=date.today())
        start_status = st.selectbox('Starting status', options=ASSET_STATUSES)
        if st.form_submit_button('Add asset', type='primary'):
            if not name.strip():
                st.error('Name is required.')
            else:
                with db_session() as session:
                    create_asset(session, name=name.strip(), category=category,
                                 manufacturer=manufacturer.strip(), model_number=model_number.strip(),
                                 serial_number=serial_number.strip(), vendor_name=vendor.strip(),
                                 purchase_cost=float(purchase_cost), purchase_date=purchase_dt,
                                 status=start_status)
                st.success(f'Added {name.strip()}.')
                st.rerun()

# --------------------------------------------------------------------------
# Advance an asset through its lifecycle
# --------------------------------------------------------------------------
with st.expander('Advance an asset (receive / install / retire)'):
    with db_session() as session:
        active = [a for a in list_assets(session) if a.status != 'retired']
    if not active:
        st.caption('No active assets to advance.')
    else:
        labels = {f'#{a.id} · {a.name} ({STATUS_BADGE.get(a.status, "")} {a.status})': a for a in active}
        pick = st.selectbox('Asset', options=list(labels.keys()))
        asset = labels[pick]
        action = st.radio('Action', options=['Receive', 'Install', 'Retire'], horizontal=True)

        if action == 'Receive':
            rd = st.date_input('Received date', value=date.today(), key='recv_dt')
            if st.button('Mark received', type='primary'):
                with db_session() as session:
                    receive_asset(session, asset.id, received_date=rd)
                st.success(f'{asset.name} marked received.')
                st.rerun()

        elif action == 'Install':
            if not prop_labels:
                st.caption('Add a property first (Accounts & Properties page).')
            else:
                ip = st.selectbox('Install at property', options=list(prop_labels.keys()),
                                  format_func=lambda i: prop_labels[i], key='install_prop')
                with db_session() as session:
                    vessels = list(session.exec(select(PoolVessel).where(PoolVessel.property_id == ip)).all())
                vessel_choices = {0: '(none)'} | {v.id: v.name for v in vessels}
                iv = st.selectbox('Vessel (optional)', options=list(vessel_choices.keys()),
                                  format_func=lambda i: vessel_choices[i], key='install_vessel')
                idt = st.date_input('Install date', value=date.today(), key='install_dt')
                wdt = st.date_input('Warranty until (optional)', value=date.today(), key='warranty_dt')
                use_warranty = st.checkbox('Set warranty date', value=False)
                if st.button('Mark installed', type='primary'):
                    with db_session() as session:
                        install_asset(session, asset.id, property_id=ip,
                                      vessel_id=(iv or None), install_date=idt,
                                      warranty_until=wdt if use_warranty else None)
                    st.success(f'{asset.name} installed.')
                    st.rerun()

        else:  # Retire
            rdt = st.date_input('Retirement date', value=date.today(), key='retire_dt')
            reason = st.text_input('Reason', key='retire_reason')
            if st.button('Retire asset', type='primary'):
                with db_session() as session:
                    retire_asset(session, asset.id, retirement_date=rdt, reason=reason.strip())
                st.success(f'{asset.name} retired.')
                st.rerun()
