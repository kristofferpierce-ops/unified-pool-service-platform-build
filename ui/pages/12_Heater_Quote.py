from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from sqlmodel import Session

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.database import create_db_and_tables, engine
from app.services.bootstrap import seed_defaults
from app.services.heater_quote import (
    attach_heater_candidate_to_quote_case,
    build_heater_package_preview,
    create_heater_quote_run,
    delete_heater_quote_run,
    get_heater_quote_dashboard_summary,
    get_heater_quote_settings,
    get_quote_case_heater_package_workspace,
    list_heater_quote_runs,
    serialize_heater_quote_run,
)
from app.services.quote_workflow import list_quote_cases
from ui._shared import configure_page, page_header

configure_page('Heater Quote Tool', icon='🔥')

create_db_and_tables()
with Session(engine) as session:
    seed_defaults(session)
    heater_dashboard = get_heater_quote_dashboard_summary(session)
    heater_settings = get_heater_quote_settings(session)
    quote_cases = list_quote_cases(session, include_closed=False, limit=250)
    recent_runs = list_heater_quote_runs(session, limit=10)

page_header('Heater Quote Tool', 'BTU sizing, equipment ranking, and heater package quoting.', icon='🔥')
st.caption('Size the heating requirement, review recommended equipment, and attach the chosen heater recommendation to a quote case without rebuilding the rest of the platform.')

summary_a, summary_b, summary_c, summary_d = st.columns(4)
summary_a.metric('Heater Quote Runs', heater_dashboard['total_runs'], help='Total heater sizing runs already saved in the local platform database.')
summary_b.metric('Candidate Rows', heater_dashboard['candidate_count'], help='Total recommended heater candidates saved across all heater quote runs.')
summary_c.metric('Heritage Mode', heater_dashboard['heritage_connection']['sync_mode'], help='Dry run uses the fallback catalog only. Live mode tries the configured Heritage catalog source first.')
summary_d.metric('Catalog Ready', 'Yes' if heater_dashboard['heritage_connection']['configured'] else 'No', help='This turns to Yes only when the Heritage account id, API key, and a catalog source are available.')

with st.expander('How this sizing tool works', expanded=False):
    st.write('The tool computes the total BTUs required to raise the water from the current temperature to the target temperature. It then compares that heat-up target with a maintenance-style BTU per hour target based on pool surface area, temperature rise, and wind. Candidates are ranked against the larger of those two targets.')
    st.write('This page is conservative by design. It does not silently discount the recommendation for a pool cover, and it does not assume a private Heritage endpoint contract that has not been documented publicly yet.')

with st.expander('Heritage connection summary', expanded=False):
    st.json(heater_dashboard['heritage_connection'])
    st.write(heater_settings.get('heritage', {}).get('notes', ''))

with st.form('heater_quote_form'):
    left, right = st.columns(2)
    with left:
        title = st.text_input('Run title', value='', help='Type a short label that helps staff recognize this heater sizing run later.')
        linked_quote_case_id = st.selectbox(
            'Link this run to an existing quote case',
            options=[None] + [case.id for case in quote_cases],
            format_func=lambda value: 'Not linked yet' if value is None else next((f"{case.id} - {case.title}" for case in quote_cases if case.id == value), str(value)),
            help='Choose an open quote case if you want to attach the heater recommendation to an active quote workflow record later.',
        )
        direct_gallons = st.number_input('Known gallons', min_value=0.0, value=0.0, step=100.0, help='Enter the exact gallons if you know them. Leave this at zero if you want the tool to estimate gallons from dimensions instead.')
        shape = st.selectbox('Shape', options=['direct', 'rectangle', 'oval', 'round'], help='Choose the body of water shape. Direct means you are supplying gallons yourself instead of dimensions.')
        length_ft = st.number_input('Length in feet', min_value=0.0, value=0.0, step=1.0, help='Enter the pool length in feet when using dimensions.')
        width_ft = st.number_input('Width in feet', min_value=0.0, value=0.0, step=1.0, help='Enter the pool width in feet when using dimensions.')
        avg_depth_ft = st.number_input('Average depth in feet', min_value=0.0, value=0.0, step=0.5, help='Enter the average water depth in feet when using dimensions.')
        diameter_ft = st.number_input('Diameter in feet', min_value=0.0, value=0.0, step=1.0, help='Use this for round pools instead of length and width.')
    with right:
        current_water_temp_f = st.number_input('Current water temperature °F', min_value=32.0, max_value=120.0, value=78.0, step=1.0, help='Enter the starting water temperature in degrees Fahrenheit.')
        target_water_temp_f = st.number_input('Target water temperature °F', min_value=32.0, max_value=120.0, value=84.0, step=1.0, help='Enter the desired target water temperature in degrees Fahrenheit.')
        ambient_air_temp_f = st.number_input('Outdoor air temperature °F', min_value=0.0, max_value=130.0, value=80.0, step=1.0, help='Enter the outdoor air temperature. This matters because heater performance and heat loss change with ambient conditions.')
        desired_heatup_hours = st.number_input('Desired heat-up hours', min_value=1.0, max_value=168.0, value=24.0, step=1.0, help='Enter how quickly you want the water to reach the target temperature. Shorter time windows require larger heater output.')
        unit_count = st.number_input('Number of identical heater units', min_value=1, max_value=12, value=int(heater_settings.get('defaults', {}).get('unit_count', 1) or 1), step=1, help='Use this for multi-unit installations where two or more identical heaters will work together in parallel.')
        wind_mph = st.number_input('Approximate wind mph', min_value=0.0, max_value=50.0, value=0.0, step=1.0, help='Wind increases heat loss. The tool uses conservative wind multipliers for 5 mph and 10 mph thresholds.')
        covered = st.checkbox('Usually covered while heating', value=False, help='Check this if the pool is usually covered during heating. The tool still keeps the recommendation conservative and does not automatically reduce the BTU target.')
        heater_kind_preference = st.selectbox('Heater type preference', options=['auto', 'gas', 'heat_pump', 'heat_cool'], help='Auto lets the tool choose the more sensible type based on heat-up speed and air temperature.')
        fuel_preference = st.selectbox('Fuel preference', options=['auto', 'natural_gas', 'propane', 'electric'], help='Choose a fuel preference if the project has a real fuel constraint.')
    submitted = st.form_submit_button('Calculate heater quote', help='Click to compute the heating requirement and rank equipment candidates from the configured Heritage or fallback catalog source.')

if submitted:
    with Session(engine) as session:
        try:
            run_payload = create_heater_quote_run(
                session,
                title=title,
                quote_case_id=linked_quote_case_id,
                direct_gallons=direct_gallons or None,
                shape=shape,
                length_ft=length_ft,
                width_ft=width_ft,
                avg_depth_ft=avg_depth_ft,
                diameter_ft=diameter_ft,
                current_water_temp_f=current_water_temp_f,
                target_water_temp_f=target_water_temp_f,
                ambient_air_temp_f=ambient_air_temp_f,
                desired_heatup_hours=desired_heatup_hours,
                wind_mph=wind_mph,
                covered=covered,
                heater_kind_preference=heater_kind_preference,
                fuel_preference=fuel_preference,
                unit_count=unit_count,
            )
            st.session_state['heater_quote_run_id'] = run_payload['id']
            st.success(f"Saved heater quote run {run_payload['id']}.")
        except ValueError as exc:
            st.error(str(exc))

current_run_id = st.session_state.get('heater_quote_run_id')
if current_run_id:
    with Session(engine) as session:
        run_payload = serialize_heater_quote_run(session, current_run_id)
    summary = run_payload.get('summary', {})
    st.subheader('Sizing summary')
    s1, s2, s3, s4, s5, s6 = st.columns(6)
    s1.metric('Gallons', f"{summary.get('volume_gallons', 0):,.0f}", help='Estimated or supplied gallons used for the heating calculation.')
    s2.metric('Temp rise °F', f"{summary.get('temperature_rise_f', 0):,.1f}", help='Difference between the current water temperature and the target temperature.')
    s3.metric('Total BTUs', f"{summary.get('total_btu_required', 0):,.0f}", help='Total BTUs needed to raise the full water volume to the target temperature.')
    s4.metric('Heat-up BTU/hr', f"{summary.get('heatup_btu_per_hr', 0):,.0f}", help='BTU per hour needed to meet the requested heat-up time window.')
    s5.metric('Recommended BTU/hr', f"{summary.get('recommended_btu_per_hr', 0):,.0f}", help='Larger of the heat-up target and the maintenance-style surface area target.')
    s6.metric('Units', int(summary.get('unit_count', 1) or 1), help='Number of identical heaters being considered for this installation.')
    if int(summary.get('unit_count', 1) or 1) > 1:
        st.caption(f"Per-unit target BTU/hr: {float(summary.get('per_unit_target_btu_per_hr', 0) or 0):,.0f}")
    st.info(summary.get('recommendation_note', ''))

    candidates = run_payload.get('candidates', [])
    st.subheader('Recommended heaters')
    if candidates:
        display_rows = []
        for candidate in candidates:
            display_rows.append({
                'Rank': candidate.get('rank_order'),
                'Band': candidate.get('recommendation_band'),
                'Brand': candidate.get('brand_name'),
                'Model': candidate.get('model_name'),
                'SKU': candidate.get('sku'),
                'Kind': candidate.get('heater_kind'),
                'Fuel': candidate.get('fuel_type'),
                'Units': candidate.get('unit_count', summary.get('unit_count', 1)),
                'Per Unit BTU/hr': (candidate.get('payload') or {}).get('per_unit_capacity_btu_per_hr', candidate.get('capacity_btu_per_hr')),
                'Package BTU/hr': candidate.get('capacity_btu_per_hr'),
                'Est. Heat-up Hours': candidate.get('estimated_heatup_hours'),
                'Per Unit Price': (candidate.get('payload') or {}).get('per_unit_price'),
                'Package Price': candidate.get('price'),
                'Currency': candidate.get('currency_code'),
                'Availability': candidate.get('availability_status'),
                'Branch': candidate.get('branch_name'),
                'Fit Score': candidate.get('fit_score'),
            })
        st.dataframe(pd.DataFrame(display_rows), width='stretch')

        attach_col, info_col = st.columns([1, 1])
        with attach_col:
            selectable_candidates = {f"#{candidate['rank_order']} {candidate['model_name']} ({candidate.get('recommendation_band', 'review')})": candidate['id'] for candidate in candidates}
            selected_candidate_label = st.selectbox('Candidate to attach', options=list(selectable_candidates.keys()), help='Choose which heater recommendation you want to attach to a quote case.')
            package_profile_options = ['auto'] + list((heater_settings.get('package_profiles') or {}).keys())
            selected_package_profile = st.selectbox('Install package profile', options=package_profile_options, help='Choose the install package template used to build equipment, materials, and labor lines for the quote.')
            labor_profile_options = list((heater_settings.get('labor_profiles') or {}).keys()) or ['standard']
            selected_labor_profile = st.selectbox('Labor profile', options=labor_profile_options, help='Choose the labor profile used to build the install labor line for the heater package.')
            option_left, option_right = st.columns(2)
            with option_left:
                include_bypass_kit = st.checkbox('Include bypass / union kit', value=True, help='Include plumbing bypass materials and unions in the heater package preview.')
                include_pad_kit = st.checkbox('Include equipment pad / stand', value=True, help='Include a pad, stand, or base materials allowance in the heater package preview.')
                include_startup_visit = st.checkbox('Include startup and commissioning', value=True, help='Include a final startup and commissioning visit line item in the package preview.')
            with option_right:
                include_gas_allowance = st.checkbox('Include gas allowance', value=summary.get('preferred_heater_kind') == 'gas', help='Include a gas tie-in allowance when the install requires gas piping work.')
                include_electrical_allowance = st.checkbox('Include electrical allowance', value=summary.get('preferred_heater_kind') != 'gas', help='Include an electrical allowance when the install requires disconnect, whip, or breaker work.')
                include_automation_integration = st.checkbox('Include automation integration', value=False, help='Include a control integration allowance when the heater should tie into automation.')
            misc_materials_amount = st.number_input('Additional materials allowance', min_value=0.0, value=0.0, step=25.0, help='Add a field-adjustable allowance for miscellaneous materials on top of the package template.')
            labor_rate_override = st.number_input('Labor rate override', min_value=0.0, value=0.0, step=5.0, help='Leave at zero to use the selected labor profile rate. Use a real value to override the labor rate for this package preview.')
            attach_quote_case_id = st.selectbox(
                'Quote case to attach to',
                options=[case.id for case in quote_cases] if quote_cases else [],
                format_func=lambda value: next((f"{case.id} - {case.title}" for case in quote_cases if case.id == value), str(value)),
                help='Choose the open quote case that should receive this heater recommendation as a linked equipment suggestion.',
            ) if quote_cases else None
            replace_existing = st.checkbox('Replace existing heater packages on this quote case', value=False, help='Turn this on when you want this attachment to replace any previously attached heater package lines on the selected quote case.')
            existing_workspace = {'package_count': 0, 'grand_total': 0.0, 'currency_code': 'USD', 'packages': []}
            if attach_quote_case_id is not None:
                with Session(engine) as session:
                    existing_workspace = get_quote_case_heater_package_workspace(session, attach_quote_case_id)
                if existing_workspace['package_count']:
                    st.info(f"Quote case {attach_quote_case_id} already has {existing_workspace['package_count']} attached heater package(s) totaling {existing_workspace['grand_total']:,.2f} {existing_workspace['currency_code']}. Enable replacement if you want this new package to take over.")
            with Session(engine) as session:
                try:
                    package_preview = build_heater_package_preview(
                        session,
                        run_id=current_run_id,
                        candidate_id=selectable_candidates[selected_candidate_label],
                        package_profile=selected_package_profile,
                        labor_profile=selected_labor_profile,
                        include_bypass_kit=include_bypass_kit,
                        include_pad_kit=include_pad_kit,
                        include_gas_allowance=include_gas_allowance,
                        include_electrical_allowance=include_electrical_allowance,
                        include_automation_integration=include_automation_integration,
                        include_startup_visit=include_startup_visit,
                        misc_materials_amount=misc_materials_amount,
                        labor_rate_override=labor_rate_override or None,
                    )
                except ValueError as exc:
                    package_preview = None
                    st.error(str(exc))
            if package_preview:
                st.write('**Package preview**')
                package_rows = [
                    {
                        'Name': line.get('name'),
                        'Description': line.get('description'),
                        'Qty': line.get('qty'),
                        'Unit Price': line.get('amount'),
                        'Currency': line.get('code'),
                        'Category': line.get('category', ''),
                    }
                    for line in package_preview.get('lines', [])
                ]
                st.dataframe(pd.DataFrame(package_rows), width='stretch')
                st.metric('Package Total', f"{package_preview.get('package_total', 0):,.2f} {package_preview.get('currency_code', 'USD')}", help='Total value of the equipment, materials, allowances, and labor lines that will attach to the quote case.')
            if st.button('Attach selected heater package to quote case', help='Attach the selected heater package lines to the chosen quote case so they can flow into the quote workflow and FreshBooks draft creation.'):
                if attach_quote_case_id is None:
                    st.error('Create or keep an open quote case first, then return here to attach the heater recommendation.')
                else:
                    with Session(engine) as session:
                        try:
                            attach_result = attach_heater_candidate_to_quote_case(
                                session,
                                run_id=current_run_id,
                                candidate_id=selectable_candidates[selected_candidate_label],
                                quote_case_id=attach_quote_case_id,
                                package_profile=selected_package_profile,
                                labor_profile=selected_labor_profile,
                                include_bypass_kit=include_bypass_kit,
                                include_pad_kit=include_pad_kit,
                                include_gas_allowance=include_gas_allowance,
                                include_electrical_allowance=include_electrical_allowance,
                                include_automation_integration=include_automation_integration,
                                include_startup_visit=include_startup_visit,
                                misc_materials_amount=misc_materials_amount,
                                labor_rate_override=labor_rate_override or None,
                                replace_existing=replace_existing,
                            )
                            removed_count = int(attach_result.get('removed_existing_count') or 0)
                            if removed_count:
                                st.success(f"Replaced {removed_count} existing heater package(s) on quote case {attach_result['quote_case']['id']}.")
                            else:
                                st.success(f"Attached heater package to quote case {attach_result['quote_case']['id']}.")
                        except ValueError as exc:
                            st.error(str(exc))
        with info_col:
            st.write('**Notes**')
            if run_payload.get('source_mode') == 'fallback_catalog':
                st.warning('These recommendations came from the starter planning catalog, not a live Heritage feed. Pricing and availability remain placeholders until the Heritage catalog connection is configured.')
            for note in run_payload.get('notes', []):
                st.write(f'- {note}')
            st.write('**Why these candidates are ranked this way**')
            st.write('Candidates are scored by how close they are to the recommended BTU per hour target. The tool boosts the score when the candidate matches the preferred heater type and mildly penalizes heat pumps in cooler ambient conditions.')
            st.write('**Quote workflow behavior**')
            st.write('Attached heater packages now store prepared equipment, materials, allowance, and labor lines on the quote case. If a FreshBooks draft is created without manual lines, the draft service will use the attached heater package lines automatically.')
    else:
        st.warning('No heater candidates were returned. The tool should normally fall back to the starter planning catalog now, so this usually means the heater quote setting was overwritten with an empty catalog or the run needs to be recalculated.')

st.subheader('Recent heater quote runs')
if recent_runs:
    recent_rows = []
    for run in recent_runs:
        recent_rows.append({
            'Run Id': run['id'],
            'Title': run.get('title') or '',
            'Units': (run.get('summary') or {}).get('unit_count', 1),
            'Gallons': run.get('volume_gallons'),
            'Recommended BTU/hr': run.get('recommended_btu_per_hr'),
            'Source Mode': run.get('source_mode'),
            'Linked Quote Case': run.get('quote_case_id'),
            'Created At': run.get('created_at'),
        })
    st.dataframe(pd.DataFrame(recent_rows), width='stretch')
    deletable_runs = {f"#{run['id']} {run.get('title') or 'Untitled heater quote'}": run['id'] for run in recent_runs}
    delete_label = st.selectbox('Delete heater quote run', options=list(deletable_runs.keys()), help='Choose a saved heater quote run to remove. This deletes its stored candidates and any heater-quote external links attached from this run.')
    if st.button('Delete selected heater quote run', help='Click to permanently remove the selected heater quote run and its saved candidate records.'):
        with Session(engine) as session:
            try:
                delete_result = delete_heater_quote_run(session, deletable_runs[delete_label])
                if st.session_state.get('heater_quote_run_id') == delete_result['deleted_run_id']:
                    st.session_state.pop('heater_quote_run_id', None)
                st.success(f"Deleted heater quote run {delete_result['deleted_run_id']} and {delete_result['deleted_candidate_count']} saved candidates.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
else:
    st.caption('No heater quote runs have been created yet.')
