from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import streamlit as st
from sqlmodel import select

from ui._shared import configure_page, db_session, page_header, section
from app.models.tables import PoolVessel, Property, WaterTestLog
from app.services.chemistry import IDEAL_RANGES, water_balance_report

configure_page('Chemistry', icon='🧪')
page_header(
    'Water Balance (LSI)',
    'The Langelier Saturation Index tells you if water is corrosive, balanced, or scaling, and the engine '
    'recommends dosing to bring it into balance. The core pool-specific differentiator.',
    icon='🧪',
)

STATUS_ICON = {'ok': '🟢', 'low': '🔻', 'high': '🔺'}
CLASS_STYLE = {
    'corrosive': ('❄️ Corrosive', 'Aggressive water — etches plaster, corrodes metal and equipment.'),
    'balanced': ('✅ Balanced', 'Water is in balance. Hold these levels.'),
    'scaling': ('🔶 Scaling', 'Scale-forming — calcium deposits on surfaces and equipment.'),
}

# --------------------------------------------------------------------------
# Optional: prefill from a property's vessel + latest reading
# --------------------------------------------------------------------------
with db_session() as session:
    props = list(session.exec(select(Property).order_by(Property.name)).all())

prefill = {}
gallons_default = 15000.0
sel_property_id = None
sel_vessel_id = None
if props:
    labels = {0: '(manual entry)'} | {p.id: p.name for p in props}
    sel_property_id = st.selectbox('Load from property (optional)', options=list(labels.keys()),
                                   format_func=lambda i: labels[i])
    if sel_property_id:
        with db_session() as session:
            vessels = list(session.exec(select(PoolVessel).where(PoolVessel.property_id == sel_property_id)).all())
            latest = session.exec(
                select(WaterTestLog).where(WaterTestLog.property_id == sel_property_id)
                .order_by(WaterTestLog.logged_at.desc())
            ).first()
        if vessels:
            gallons_default = vessels[0].gallons or gallons_default
            sel_vessel_id = vessels[0].id
        if latest:
            prefill = {
                'ph': latest.ph or 7.5, 'total_alkalinity': latest.total_alkalinity_ppm or 100.0,
                'calcium_hardness': latest.calcium_hardness_ppm or 250.0,
                'cyanuric_acid': latest.cya_ppm or 40.0, 'free_chlorine': latest.free_chlorine_ppm or 3.0,
            }

# --------------------------------------------------------------------------
# Readings
# --------------------------------------------------------------------------
section('Water test')
c1, c2, c3 = st.columns(3)
with c1:
    ph = st.number_input('pH', min_value=6.0, max_value=9.0, value=float(prefill.get('ph', 7.5)), step=0.1)
    total_alkalinity = st.number_input('Total alkalinity (ppm)', min_value=0.0, value=float(prefill.get('total_alkalinity', 100.0)), step=10.0)
    calcium_hardness = st.number_input('Calcium hardness (ppm)', min_value=0.0, value=float(prefill.get('calcium_hardness', 250.0)), step=10.0)
with c2:
    cyanuric_acid = st.number_input('Cyanuric acid / CYA (ppm)', min_value=0.0, value=float(prefill.get('cyanuric_acid', 40.0)), step=5.0)
    free_chlorine = st.number_input('Free chlorine (ppm)', min_value=0.0, value=float(prefill.get('free_chlorine', 3.0)), step=0.5)
    tds = st.number_input('TDS (ppm)', min_value=0.0, value=1000.0, step=100.0)
with c3:
    temp_f = st.number_input('Water temp (°F)', min_value=32.0, max_value=110.0, value=80.0, step=1.0)
    gallons = st.number_input('Pool volume (gallons)', min_value=0.0, value=float(gallons_default), step=1000.0)

report = water_balance_report(
    ph=ph, temp_f=temp_f, calcium_hardness=calcium_hardness, total_alkalinity=total_alkalinity,
    free_chlorine=free_chlorine, cyanuric_acid=cyanuric_acid, tds=tds, gallons=gallons,
)

# --------------------------------------------------------------------------
# LSI result
# --------------------------------------------------------------------------
st.divider()
label, blurb = CLASS_STYLE[report.classification]
r1, r2 = st.columns([1, 3])
with r1:
    st.metric('LSI', f'{report.lsi:+.2f}', help='Balanced is -0.3 to +0.3.')
with r2:
    if report.classification == 'balanced':
        st.success(f'**{label}** — {blurb}')
    elif report.classification == 'corrosive':
        st.info(f'**{label}** — {blurb}')
    else:
        st.warning(f'**{label}** — {blurb}')

section('Parameter status')
st.dataframe(pd.DataFrame([{
    'Parameter': p.parameter.replace('_', ' ').title(),
    'Value': round(p.value, 1),
    'Ideal': f'{p.low:g}–{p.high:g}',
    'Status': f'{STATUS_ICON.get(p.status, "")} {p.status}',
} for p in report.parameters]), width='stretch', hide_index=True)

# --------------------------------------------------------------------------
# Dosing
# --------------------------------------------------------------------------
section('Dosing recommendations')
if not report.recommendations:
    if gallons <= 0:
        st.caption('Enter a pool volume to get dosing amounts.')
    else:
        st.success('All parameters in range — no dosing needed.')
else:
    for r in report.recommendations:
        amount_txt = f' — **~{r.amount:g} {r.unit}**' if r.amount else ''
        st.markdown(f'• **{r.product}**{amount_txt}  \n  {r.detail}')
    st.caption('Amounts are approximate industry rates per 10,000 gallons. Add gradually and retest, '
               'especially pH (buffered by alkalinity).')

# --------------------------------------------------------------------------
# Save the reading
# --------------------------------------------------------------------------
if sel_property_id:
    st.divider()
    if st.button('Save this reading to the property log', type='primary'):
        with db_session() as session:
            session.add(WaterTestLog(
                property_id=sel_property_id, vessel_id=sel_vessel_id,
                free_chlorine_ppm=free_chlorine, ph=ph, total_alkalinity_ppm=total_alkalinity,
                calcium_hardness_ppm=calcium_hardness, cya_ppm=cyanuric_acid,
                notes=f'LSI {report.lsi:+.2f} ({report.classification})',
            ))
            session.commit()
        st.success('Reading saved to the property water-test log.')
