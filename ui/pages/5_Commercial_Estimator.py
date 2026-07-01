from __future__ import annotations

import json
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from sqlmodel import Session, select

from app.core.database import engine
from app.models.tables import Account, EquipmentAsset, EstimateRun, EstimateScenario, PoolVessel, Property
from app.services.baseline import get_active_model
from app.services.estimator import EstimateInput, EstimateOutput, calculate_estimate, commercial_breakout_dict, save_estimate_run
from app.services.estimate_reporting import build_commercial_estimate_context, render_estimate_html, render_estimate_json, render_estimate_pdf
from ui._shared import configure_page, page_header

REPORT_KEY = 'commercial_estimate_report_context'
INPUT_KEY = 'commercial_estimate_input'
OUTPUT_KEY = 'commercial_estimate_output'
SAVE_KEY = 'commercial_estimate_saved_run_id'
PREFILL_KEY = 'commercial_estimator_prefill'
LIBRARY_KEY = 'estimate_library_selected_run_id'


def _money(value: float) -> str:
    return f'${float(value):,.2f}'


def _current_assets_payload(assets: list[EquipmentAsset]) -> list[dict]:
    return [asset.model_dump() for asset in assets]


def _history_rows(session: Session, property_id: int, vessel_id: int) -> list[dict]:
    runs = list(session.exec(select(EstimateRun).where(EstimateRun.property_id == property_id, EstimateRun.vessel_id == vessel_id).order_by(EstimateRun.run_timestamp.desc())).all())
    if not runs:
        return []
    scenario_map = {scenario.id: scenario for scenario in session.exec(select(EstimateScenario).where(EstimateScenario.property_id == property_id, EstimateScenario.vessel_id == vessel_id)).all()}
    rows = []
    for run in runs[:20]:
        scenario = scenario_map.get(run.scenario_id)
        output_snapshot = json.loads(run.output_snapshot_json or '{}') if run.output_snapshot_json else {}
        output_snapshot.update(commercial_breakout_dict(output_snapshot, output_snapshot.get('target_margin_pct', 35.0)))
        rows.append({
            'Run ID': run.id,
            'Saved At': run.run_timestamp.strftime('%Y-%m-%d %H:%M'),
            'Scenario': scenario.scenario_name if scenario else '',
            'Monthly Sell Price': float(output_snapshot.get('monthly_sell_price', run.monthly_sell_price or 0.0)),
            'Annual Sell Price': float(output_snapshot.get('annual_sell_price', 0.0)),
            'Monthly Real Cost': float(output_snapshot.get('monthly_real_cost', run.monthly_real_cost or 0.0)),
            'Annual Real Cost': float(output_snapshot.get('annual_real_cost', run.annual_real_cost or 0.0)),
        })
    return rows


def _save_current_estimate(session: Session, prop: Property, vessel: PoolVessel, scenario_name: str, target_margin: float, global_adj: float) -> int | None:
    context = st.session_state.get(REPORT_KEY)
    input_data = st.session_state.get(INPUT_KEY)
    output_data = st.session_state.get(OUTPUT_KEY)
    if not context or not input_data or not output_data:
        return None
    if st.session_state.get(SAVE_KEY):
        return st.session_state[SAVE_KEY]

    model = get_active_model(session, 'commercial')
    scenario = EstimateScenario(
        property_id=prop.id,
        vessel_id=vessel.id,
        scenario_name=scenario_name,
        model_family='commercial',
        baseline_model_version_id=model.id,
        target_margin_pct=target_margin,
        global_adjustment_pct=global_adj,
        notes=f"Peak weeks: {context['inputs']['training_weeks']}",
    )
    session.add(scenario)
    session.commit()
    session.refresh(scenario)

    estimate_input = EstimateInput(**input_data)
    output_fields = set(getattr(EstimateOutput, '__annotations__', {}).keys())
    filtered_output = {k: v for k, v in output_data.items() if k in output_fields}
    estimate_output = EstimateOutput(**filtered_output)
    run = save_estimate_run(session, scenario.id, estimate_input, estimate_output)
    st.session_state[SAVE_KEY] = run.id
    st.session_state[LIBRARY_KEY] = run.id
    context['saved_run_id'] = run.id
    context['saved_at'] = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    st.session_state[REPORT_KEY] = context
    return run.id


def _prefill_value(prefill: dict, key: str, fallback):
    value = prefill.get(key)
    return fallback if value is None else value


configure_page('Commercial Estimator', icon='🏢')
page_header('Commercial Estimator', 'Commercial scenario building and pricing from baseline models + burdened labor.', icon='🏢')
prefill = st.session_state.get(PREFILL_KEY, {}) or {}
if prefill:
    st.info('A saved estimate was loaded as a draft. Adjust anything you want, then generate a fresh estimate from it.')
    if st.button('Clear loaded draft'):
        st.session_state.pop(PREFILL_KEY, None)
        st.rerun()

with Session(engine) as session:
    properties = list(session.exec(select(Property).where(Property.account_type == 'commercial')).all())
    if not properties:
        st.info('Create a commercial property first on the Accounts & Properties page.')
        st.stop()

    prop_labels = [f'{p.name} | {p.address_line_1}' for p in properties]
    default_property_index = 0
    prefill_property_id = prefill.get('property_id')
    if prefill_property_id:
        for idx, property_record in enumerate(properties):
            if property_record.id == prefill_property_id:
                default_property_index = idx
                break
    prop = properties[st.selectbox('Commercial property', range(len(properties)), format_func=lambda i: prop_labels[i], index=default_property_index)]

    account = session.get(Account, prop.account_id)
    vessels = list(session.exec(select(PoolVessel).where(PoolVessel.property_id == prop.id)).all())
    if not vessels:
        st.warning('This property does not have a vessel yet. Create one on the Accounts & Properties page before running a commercial estimate.')
        st.stop()

    vessel_labels = [f'{v.id} :: {v.name}' for v in vessels]
    default_vessel_index = 0
    prefill_vessel_id = prefill.get('vessel_id')
    if prefill_vessel_id:
        for idx, vessel_record in enumerate(vessels):
            if vessel_record.id == prefill_vessel_id:
                default_vessel_index = idx
                break
    vessel = vessels[st.selectbox('Vessel', range(len(vessels)), format_func=lambda i: vessel_labels[i], index=default_vessel_index)]
    assets = list(session.exec(select(EquipmentAsset).where(EquipmentAsset.vessel_id == vessel.id)).all())

    with st.form('commercial_estimate_form'):
        cols = st.columns(3)
        gallons = cols[0].number_input('Gallons', min_value=0.0, value=float(_prefill_value(prefill, 'gallons', vessel.gallons)))
        visits_per_month = cols[1].number_input('Visits per month', min_value=1.0, value=float(_prefill_value(prefill, 'visits_per_month', vessel.service_frequency_per_month)))
        minutes_on_site = cols[2].number_input('Minutes on site', min_value=0.0, value=float(_prefill_value(prefill, 'minutes_on_site', vessel.minutes_on_site)))

        cols = st.columns(4)
        drive_minutes = cols[0].number_input('Drive minutes round trip', min_value=0.0, value=float(_prefill_value(prefill, 'drive_minutes_round_trip', prop.drive_minutes_round_trip)))
        techs_on_visit = cols[1].number_input('Techs on visit', min_value=1, value=int(_prefill_value(prefill, 'techs_on_visit', 1)))
        training_weeks = cols[2].number_input('Training / peak weeks per year', min_value=0, value=int(_prefill_value(prefill, 'training_weeks', vessel.training_weeks_per_year)))
        target_margin = cols[3].number_input('Target margin %', min_value=0.0, value=float(_prefill_value(prefill, 'target_margin_pct', 35.0)))

        cols = st.columns(6)
        bath = cols[0].slider('Bath', 1, 10, int(_prefill_value(prefill, 'bath_score', vessel.bathing_score)))
        debris = cols[1].slider('Debris', 1, 10, int(_prefill_value(prefill, 'debris_score', vessel.debris_score)))
        filtration = cols[2].slider('Filtration', 1, 10, int(_prefill_value(prefill, 'filtration_score', vessel.filtration_score)))
        overflow = cols[3].slider('Overflow', 1, 10, int(_prefill_value(prefill, 'overflow_score', vessel.overflow_score)))
        backwash = cols[4].slider('Backwash', 1, 10, int(_prefill_value(prefill, 'backwash_score', vessel.backwash_score)))
        global_adj = cols[5].number_input('Global adj %', value=float(_prefill_value(prefill, 'global_adjustment_pct', 0.0)))

        scenario_name = st.text_input('Scenario name', value=str(_prefill_value(prefill, 'scenario_name', 'baseline commercial quote')))
        separate_chemical_pricing = st.checkbox('Generate chemical costs separately', value=bool(_prefill_value(prefill, 'separate_chemical_pricing', False)), help='Show a separate chemical line item summary for commercial quoting while still calculating the combined total quote.')
        generate_clicked = st.form_submit_button('Generate estimate', type='primary')

    if generate_clicked:
        model = get_active_model(session, 'commercial')
        estimate_input = EstimateInput(
            property_id=prop.id,
            vessel_id=vessel.id,
            model_family='commercial',
            gallons=gallons,
            visits_per_month=visits_per_month,
            minutes_on_site=minutes_on_site,
            drive_minutes_round_trip=drive_minutes,
            techs_on_visit=techs_on_visit,
            bath_score=bath,
            debris_score=debris,
            filtration_score=filtration,
            overflow_score=overflow,
            backwash_score=backwash,
            target_margin_pct=target_margin,
            global_adjustment_pct=global_adj,
        )
        output = calculate_estimate(session, estimate_input)
        breakout = commercial_breakout_dict(output, target_margin)
        output_dict = asdict(output)
        output_dict.update(breakout)
        st.session_state[INPUT_KEY] = asdict(estimate_input)
        st.session_state[OUTPUT_KEY] = output_dict
        st.session_state[SAVE_KEY] = None
        st.session_state[PREFILL_KEY] = {**asdict(estimate_input), 'scenario_name': scenario_name, 'training_weeks': training_weeks, 'separate_chemical_pricing': separate_chemical_pricing}
        st.session_state[REPORT_KEY] = build_commercial_estimate_context(
            property_record=prop,
            vessel_record=vessel,
            assets=_current_assets_payload(assets),
            account_name=account.name if account else '',
            scenario_name=scenario_name,
            training_weeks=training_weeks,
            model_version_name=model.version_name,
            estimate_input=estimate_input,
            estimate_output=output_dict,
            separate_chemical_pricing=separate_chemical_pricing,
        )

    context = st.session_state.get(REPORT_KEY)
    if context and context['property']['id'] == prop.id and context['vessel']['id'] == vessel.id:
        totals = context['totals']
        st.subheader('Estimate summary')
        m1, m2, m3, m4 = st.columns(4)
        m1.metric('Monthly real cost', _money(totals['monthly_real_cost']))
        m2.metric('Monthly sell price', _money(totals['monthly_sell_price']))
        m3.metric('Annual real cost', _money(totals['annual_real_cost']))
        m4.metric('Annual sell price', _money(totals['annual_sell_price']))

        if context.get('separate_chemical_pricing'):
            st.subheader('Separate pricing breakdown')
            breakdown_df = pd.DataFrame([
                {'Line Item': 'Service', 'Monthly Real Cost': totals['monthly_service_real_cost'], 'Monthly Sell Price': totals['monthly_service_sell_price'], 'Annual Real Cost': totals['annual_service_real_cost'], 'Annual Sell Price': totals['annual_service_sell_price']},
                {'Line Item': 'Chemicals', 'Monthly Real Cost': totals['monthly_chemical_real_cost'], 'Monthly Sell Price': totals['monthly_chemical_sell_price'], 'Annual Real Cost': totals['annual_chemical_real_cost'], 'Annual Sell Price': totals['annual_chemical_sell_price']},
                {'Line Item': 'Combined Total', 'Monthly Real Cost': totals['monthly_real_cost'], 'Monthly Sell Price': totals['monthly_sell_price'], 'Annual Real Cost': totals['annual_real_cost'], 'Annual Sell Price': totals['annual_sell_price']},
            ])
            st.dataframe(breakdown_df, width='stretch', hide_index=True)

        st.subheader('Chemical cost schedule')
        chem_rows = [{'Chemical': row['chemical'], 'Monthly Qty': row['monthly_qty'], 'Annual Qty': row['annual_qty'], 'Monthly Real Cost': row['monthly_real_cost'], 'Monthly Sell Price': row['monthly_sell_price'], 'Annual Real Cost': row['annual_real_cost'], 'Annual Sell Price': row['annual_sell_price']} for row in context['chemicals']]
        chem_rows.append({'Chemical': 'TOTAL CHEMICALS', 'Monthly Qty': None, 'Annual Qty': None, 'Monthly Real Cost': totals['monthly_chemical_real_cost'], 'Monthly Sell Price': totals['monthly_chemical_sell_price'], 'Annual Real Cost': totals['annual_chemical_real_cost'], 'Annual Sell Price': totals['annual_chemical_sell_price']})
        st.dataframe(pd.DataFrame(chem_rows), width='stretch', hide_index=True)

        html_report = render_estimate_html(context, include_print_button=True)
        pdf_report = render_estimate_pdf(context)
        json_report = render_estimate_json(context)
        file_base = context['file_name_base']

        st.subheader('Save, print, and export')
        c1, c2, c3, c4 = st.columns(4)
        if c1.button('Save estimate', type='secondary'):
            run_id = _save_current_estimate(session, prop, vessel, scenario_name, target_margin, global_adj)
            if run_id:
                st.success(f'Estimate saved as run #{run_id}. You can open it from the Estimate Library page.')
            else:
                st.warning('Generate an estimate first before saving it.')
        c2.download_button('Export estimate PDF', data=pdf_report, file_name=f'{file_base}.pdf', mime='application/pdf')
        c3.download_button('Download printable HTML', data=html_report.encode('utf-8'), file_name=f'{file_base}.html', mime='text/html')
        c4.download_button('Download estimate JSON', data=json_report, file_name=f'{file_base}.json', mime='application/json')
        st.caption('Print the estimate from the preview below or open the downloaded HTML file and print it from your browser.')
        components.html(html_report, height=900, scrolling=True)

    st.subheader('Saved estimates for this vessel')
    history = _history_rows(session, prop.id, vessel.id)
    if history:
        st.dataframe(pd.DataFrame(history), width='stretch', hide_index=True)
        last_saved_run_id = st.session_state.get(LIBRARY_KEY)
        if last_saved_run_id:
            st.caption(f'Latest saved run available in Estimate Library: #{last_saved_run_id}')
    else:
        st.info('No saved estimates yet for this property and vessel.')

    st.subheader('Equipment assets for selected vessel')
    st.dataframe(pd.DataFrame([row.model_dump() for row in assets]), width='stretch', hide_index=True)

    with st.form('add_equipment'):
        asset_type = st.text_input('Asset type')
        manufacturer = st.text_input('Manufacturer')
        model_number = st.text_input('Model number')
        part_number = st.text_input('Part number')
        reference_tag = st.text_input('Reference tag')
        notes = st.text_area('Notes')
        submit_asset = st.form_submit_button('Add asset')
        if submit_asset and asset_type:
            session.add(EquipmentAsset(vessel_id=vessel.id, asset_type=asset_type, manufacturer=manufacturer, model_number=model_number, part_number=part_number, reference_tag=reference_tag, notes=notes))
            session.commit()
            st.success('Equipment asset added')
