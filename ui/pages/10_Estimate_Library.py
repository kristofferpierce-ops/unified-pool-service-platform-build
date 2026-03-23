from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from sqlmodel import Session

from app.core.database import engine
from app.services.estimate_reporting import render_estimate_html, render_estimate_json, render_estimate_pdf
from app.services.estimate_workspace import delete_saved_run, get_saved_estimate_bundle, list_saved_estimate_runs

PREFILL_KEY = 'commercial_estimator_prefill'
LIBRARY_KEY = 'estimate_library_selected_run_id'


def _money(value: float) -> str:
    return f'${float(value):,.2f}'


st.title('Estimate Library')
st.caption('Review saved estimates, compare runs, export reports, or load a past estimate back into Commercial Estimator as a draft.')

with Session(engine) as session:
    rows = list_saved_estimate_runs(session, limit=500)
    if not rows:
        st.info('No saved estimates found yet. Save a commercial estimate first.')
        st.stop()

    account_types = ['All'] + sorted({row['account_type'] for row in rows if row['account_type']})
    properties = ['All'] + sorted({row['property_name'] for row in rows if row['property_name']})
    vessels = ['All'] + sorted({row['vessel_name'] for row in rows if row['vessel_name']})

    c1, c2, c3, c4 = st.columns(4)
    account_type_filter = c1.selectbox('Account type', account_types)
    property_filter = c2.selectbox('Property', properties)
    vessel_filter = c3.selectbox('Vessel', vessels)
    search_text = c4.text_input('Search scenario or account')

    filtered = []
    for row in rows:
        if account_type_filter != 'All' and row['account_type'] != account_type_filter:
            continue
        if property_filter != 'All' and row['property_name'] != property_filter:
            continue
        if vessel_filter != 'All' and row['vessel_name'] != vessel_filter:
            continue
        haystack = ' '.join([row['account_name'], row['property_name'], row['vessel_name'], row['scenario_name']]).lower()
        if search_text and search_text.lower() not in haystack:
            continue
        filtered.append(row)

    if not filtered:
        st.warning('No saved estimates match the current filters.')
        st.stop()

    table_df = pd.DataFrame([{'Run ID': row['run_id'], 'Saved At': row['saved_at'].replace('T', ' ')[:16], 'Account': row['account_name'], 'Property': row['property_name'], 'Vessel': row['vessel_name'], 'Scenario': row['scenario_name'], 'Monthly Sell': row['monthly_sell_price'], 'Annual Sell': row['annual_sell_price'], 'Monthly Real': row['monthly_real_cost']} for row in filtered])
    st.subheader('Saved estimate runs')
    st.dataframe(table_df, use_container_width=True, hide_index=True)

    default_run_id = st.session_state.get(LIBRARY_KEY)
    run_options = {f"#{row['run_id']} | {row['property_name']} | {row['vessel_name']} | {_money(row['monthly_sell_price'])}/mo": row['run_id'] for row in filtered}
    run_labels = list(run_options.keys())
    default_index = 0
    if default_run_id:
        for idx, label in enumerate(run_labels):
            if run_options[label] == default_run_id:
                default_index = idx
                break
    selected_label = st.selectbox('Primary saved run', run_labels, index=default_index)
    selected_run_id = run_options[selected_label]
    bundle = get_saved_estimate_bundle(session, selected_run_id)
    if not bundle or not bundle['context']:
        st.error('The selected estimate could not be loaded.')
        st.stop()

    compare_candidates = {'Do not compare': None}
    for row in filtered:
        if row['run_id'] != selected_run_id:
            compare_candidates[f"#{row['run_id']} | {row['property_name']} | {row['vessel_name']} | {_money(row['monthly_sell_price'])}/mo"] = row['run_id']
    compare_label = st.selectbox('Compare against another saved run', list(compare_candidates.keys()))
    compare_run_id = compare_candidates[compare_label]
    compare_bundle = get_saved_estimate_bundle(session, compare_run_id) if compare_run_id else None

    action_cols = st.columns(3)
    if action_cols[0].button('Load into Commercial Estimator'):
        input_snapshot = dict(bundle['input_snapshot'])
        input_snapshot['property_id'] = bundle['property'].id if bundle['property'] else input_snapshot.get('property_id')
        input_snapshot['vessel_id'] = bundle['vessel'].id if bundle['vessel'] else input_snapshot.get('vessel_id')
        input_snapshot['scenario_name'] = bundle['row']['scenario_name']
        input_snapshot['training_weeks'] = int(input_snapshot.get('training_weeks', bundle['context']['inputs']['training_weeks']))
        input_snapshot['separate_chemical_pricing'] = bool(bundle['context'].get('separate_chemical_pricing'))
        st.session_state[PREFILL_KEY] = input_snapshot
        st.success('Saved run loaded into Commercial Estimator as a draft. Open the Commercial Estimator page to use it.')
    confirm_delete = action_cols[1].checkbox('Confirm delete selected run')
    if action_cols[2].button('Delete selected run'):
        if not confirm_delete:
            st.warning('Check Confirm delete selected run first.')
        else:
            deleted_id = selected_run_id
            delete_saved_run(session, selected_run_id)
            if st.session_state.get(LIBRARY_KEY) == deleted_id:
                st.session_state.pop(LIBRARY_KEY, None)
            st.success(f'Saved run #{deleted_id} deleted.')
            st.rerun()

    context = bundle['context']
    totals = context['totals']
    st.subheader('Selected estimate summary')
    m1, m2, m3, m4 = st.columns(4)
    m1.metric('Monthly real cost', _money(totals['monthly_real_cost']))
    m2.metric('Monthly sell price', _money(totals['monthly_sell_price']))
    m3.metric('Annual real cost', _money(totals['annual_real_cost']))
    m4.metric('Annual sell price', _money(totals['annual_sell_price']))

    breakdown_rows = [
        {'Line Item': 'Service', 'Monthly Real Cost': totals['monthly_service_real_cost'], 'Monthly Sell Price': totals['monthly_service_sell_price'], 'Annual Real Cost': totals['annual_service_real_cost'], 'Annual Sell Price': totals['annual_service_sell_price']},
        {'Line Item': 'Chemicals', 'Monthly Real Cost': totals['monthly_chemical_real_cost'], 'Monthly Sell Price': totals['monthly_chemical_sell_price'], 'Annual Real Cost': totals['annual_chemical_real_cost'], 'Annual Sell Price': totals['annual_chemical_sell_price']},
        {'Line Item': 'Combined Total', 'Monthly Real Cost': totals['monthly_real_cost'], 'Monthly Sell Price': totals['monthly_sell_price'], 'Annual Real Cost': totals['annual_real_cost'], 'Annual Sell Price': totals['annual_sell_price']},
    ]
    st.dataframe(pd.DataFrame(breakdown_rows), use_container_width=True, hide_index=True)

    html_report = render_estimate_html(context, include_print_button=True)
    pdf_report = render_estimate_pdf(context)
    json_report = render_estimate_json(context)
    file_base = context['file_name_base']

    export_cols = st.columns(3)
    export_cols[0].download_button('Export PDF', data=pdf_report, file_name=f'{file_base}.pdf', mime='application/pdf')
    export_cols[1].download_button('Download HTML', data=html_report.encode('utf-8'), file_name=f'{file_base}.html', mime='text/html')
    export_cols[2].download_button('Download JSON', data=json_report, file_name=f'{file_base}.json', mime='application/json')

    st.subheader('Estimate preview')
    components.html(html_report, height=900, scrolling=True)

    st.subheader('Chemical schedule')
    chemical_df = pd.DataFrame([{'Chemical': row['chemical'], 'Monthly Qty': row['monthly_qty'], 'Annual Qty': row['annual_qty'], 'Monthly Real Cost': row['monthly_real_cost'], 'Monthly Sell Price': row['monthly_sell_price'], 'Annual Real Cost': row['annual_real_cost'], 'Annual Sell Price': row['annual_sell_price']} for row in context['chemicals']])
    st.dataframe(chemical_df, use_container_width=True, hide_index=True)

    with st.expander('Show stored estimate input snapshot'):
        st.json(bundle['input_snapshot'])
    with st.expander('Show stored estimate output snapshot'):
        st.json(bundle['output_snapshot'])

    if compare_bundle and compare_bundle.get('context'):
        compare_context = compare_bundle['context']
        compare_totals = compare_context['totals']
        st.subheader('Run comparison')
        compare_df = pd.DataFrame([
            {'Metric': 'Monthly sell price', 'Selected run': totals['monthly_sell_price'], 'Compared run': compare_totals['monthly_sell_price'], 'Difference': totals['monthly_sell_price'] - compare_totals['monthly_sell_price']},
            {'Metric': 'Annual sell price', 'Selected run': totals['annual_sell_price'], 'Compared run': compare_totals['annual_sell_price'], 'Difference': totals['annual_sell_price'] - compare_totals['annual_sell_price']},
            {'Metric': 'Monthly real cost', 'Selected run': totals['monthly_real_cost'], 'Compared run': compare_totals['monthly_real_cost'], 'Difference': totals['monthly_real_cost'] - compare_totals['monthly_real_cost']},
            {'Metric': 'Monthly chemical sell price', 'Selected run': totals['monthly_chemical_sell_price'], 'Compared run': compare_totals['monthly_chemical_sell_price'], 'Difference': totals['monthly_chemical_sell_price'] - compare_totals['monthly_chemical_sell_price']},
            {'Metric': 'Monthly service sell price', 'Selected run': totals['monthly_service_sell_price'], 'Compared run': compare_totals['monthly_service_sell_price'], 'Difference': totals['monthly_service_sell_price'] - compare_totals['monthly_service_sell_price']},
        ])
        st.dataframe(compare_df, use_container_width=True, hide_index=True)
