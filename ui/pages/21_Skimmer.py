from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import streamlit as st
from sqlmodel import select

from ui._shared import configure_page, db_session, page_header, section
from app.connectors.skimmer.client import get_skimmer_client, skimmer_connection_status
from app.models.connector_tables import ConnectorRun
from app.models.ops_tables import ActualChemicalFact, ActualLaborFact, ServiceVisit, TechnicianAssignment
from app.models.tables import Property
from app.services.skimmer_sync import sync_skimmer

configure_page('Skimmer', icon='🌊')
page_header(
    'Skimmer Sync',
    'Pulls Skimmer field-ops data (customers, service locations, pools, work orders, routes) through the '
    'connector pipeline and lands work orders as service visits with labor + chemical actuals.',
    icon='🌊',
)

status = skimmer_connection_status()

# --------------------------------------------------------------------------
# Connection status
# --------------------------------------------------------------------------
c1, c2 = st.columns([2, 3])
with c1:
    if status['has_api_key']:
        st.success('Live mode — SKIMMER_API_KEY is configured.')
    else:
        st.info('Fixture mode — no SKIMMER_API_KEY set. Sync uses bundled sample data so you can '
                'exercise the pipeline now. Set the env var to go live.')
with c2:
    st.caption(f"Mode: **{status['mode']}** · Base URL: `{status['base_url']}`")

# --------------------------------------------------------------------------
# Run sync
# --------------------------------------------------------------------------
run_col, note_col = st.columns([1, 3])
with run_col:
    do_apply = st.checkbox('Apply to ops tables', value=True,
                           help='Create/update properties, vessels, and service visits. Uncheck to only fill the raw/normalized ledger.')
    if st.button('Run Skimmer sync', type='primary'):
        with db_session() as session:
            result = sync_skimmer(session, client=get_skimmer_client(), apply=do_apply)
        st.session_state['skimmer_last_result'] = result.__dict__
        st.rerun()
with note_col:
    st.caption('Re-syncing is safe: already-ingested records are skipped and nothing is duplicated.')

last = st.session_state.get('skimmer_last_result')
if last:
    st.success(
        f"Sync complete ({last['mode']}): "
        f"{last['raw_records_new']} new raw · {last['properties_created']} properties · "
        f"{last['vessels_created']} vessels · {last['service_visits_created']} service visits · "
        f"{last['chemical_facts_created']} chemical actuals · {last['unmatched_work_orders']} unmatched."
    )

# --------------------------------------------------------------------------
# What's landed
# --------------------------------------------------------------------------
with db_session() as session:
    visits = list(session.exec(select(ServiceVisit).where(ServiceVisit.source_slug == 'skimmer')).all())
    prop_names = {p.id: p.name for p in session.exec(select(Property)).all()}
    labor = {l.service_visit_id: l for l in session.exec(select(ActualLaborFact)).all()}
    techs: dict[int, str] = {}
    for t in session.exec(select(TechnicianAssignment)).all():
        techs.setdefault(t.service_visit_id, t.technician_name)
    chem_counts: dict[int, int] = {}
    for c in session.exec(select(ActualChemicalFact)).all():
        chem_counts[c.service_visit_id] = chem_counts.get(c.service_visit_id, 0) + 1

m1, m2, m3 = st.columns(3)
m1.metric('Skimmer service visits', len(visits))
m2.metric('With labor actuals', sum(1 for v in visits if v.id in labor))
m3.metric('With chemical actuals', sum(1 for v in visits if v.id in chem_counts))

if visits:
    section('Imported service visits')
    rows = []
    for v in sorted(visits, key=lambda x: x.occurred_at, reverse=True):
        lab = labor.get(v.id)
        rows.append({
            'Date': v.occurred_at.date().isoformat(),
            'Property': prop_names.get(v.property_id, f'#{v.property_id}'),
            'Technician': techs.get(v.id, '—'),
            'Labor min': round(lab.total_minutes, 0) if lab else 0,
            'Chemicals': chem_counts.get(v.id, 0),
            'Work': v.notes,
            'WO#': v.external_id,
        })
    st.dataframe(pd.DataFrame(rows), width='stretch', hide_index=True)
else:
    st.caption('No Skimmer service visits imported yet. Run a sync above.')

# --------------------------------------------------------------------------
# Recent connector runs
# --------------------------------------------------------------------------
with db_session() as session:
    runs = list(session.exec(select(ConnectorRun).where(ConnectorRun.source_slug == 'skimmer')).all())
if runs:
    section('Recent syncs')
    st.dataframe(pd.DataFrame([{
        'Run': r.id,
        'Status': r.status,
        'Raw': r.raw_record_count,
        'Normalized': r.normalized_record_count,
        'Applied': r.applied_count,
        'Started': r.started_at.strftime('%Y-%m-%d %H:%M'),
        'Notes': r.notes,
    } for r in sorted(runs, key=lambda x: x.id, reverse=True)[:10]]), width='stretch', hide_index=True)
