from __future__ import annotations

import json
import sys
from pathlib import Path
from html import escape
from urllib.parse import quote

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from sqlmodel import Session

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.database import create_db_and_tables, engine
from app.services.bootstrap import seed_defaults
from app.services.heater_quote import (
    attach_heater_candidate_to_quote_case,
    create_heater_quote_run,
    delete_heater_quote_run,
    get_heater_quote_dashboard_summary,
    get_heater_quote_settings,
    list_heater_quote_runs,
    serialize_heater_quote_run,
)
from app.services.quote_workflow import list_quote_cases



def _format_optional_currency(value: object, currency_code: str = 'USD') -> str:
    if value in (None, '', 'None'):
        return ''
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    symbol = '$' if currency_code == 'USD' else ''
    return f"{symbol}{numeric:,.0f} {currency_code}".strip()


def _format_optional_number(value: object, decimals: int = 0) -> str:
    if value in (None, '', 'None'):
        return ''
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{numeric:,.{decimals}f}"


def _build_printable_heater_report_html(run_payload: dict) -> str:
    summary = run_payload.get('summary', {}) or {}
    candidates = run_payload.get('candidates', []) or []
    notes = run_payload.get('notes', []) or []
    title = escape(run_payload.get('title') or f"Heater Quote Run #{run_payload.get('id', '')}")
    source_label = escape(str(run_payload.get('source_mode', 'fallback_catalog')))
    recommendation_note = escape(str(summary.get('recommendation_note', '')))

    table_rows: list[str] = []
    for candidate in candidates:
        payload = candidate.get('payload') or {}
        per_unit_btu = payload.get('per_unit_capacity_btu_per_hr', candidate.get('capacity_btu_per_hr'))
        package_btu = candidate.get('capacity_btu_per_hr')
        est_hours = candidate.get('estimated_heatup_hours')
        table_rows.append(
            '<tr>'
            + f"<td>{escape(str(candidate.get('rank_order', '')))}</td>"
            + f"<td>{escape(str(candidate.get('recommendation_band', 'review')))}</td>"
            + f"<td>{escape(str(candidate.get('brand_name', '')))}</td>"
            + f"<td>{escape(str(candidate.get('model_name', '')))}</td>"
            + f"<td>{escape(str(candidate.get('sku', '')))}</td>"
            + f"<td>{escape(str(candidate.get('heater_kind', '')))}</td>"
            + f"<td>{escape(str(candidate.get('fuel_type', '')))}</td>"
            + f"<td>{escape(str(candidate.get('unit_count', summary.get('unit_count', 1))))}</td>"
            + f"<td>{escape(_format_optional_number(per_unit_btu, 0))}</td>"
            + f"<td>{escape(_format_optional_number(package_btu, 0))}</td>"
            + f"<td>{escape(_format_optional_number(est_hours, 1))}</td>"
            + f"<td>{escape(_format_optional_currency(payload.get('per_unit_price'), candidate.get('currency_code') or 'USD'))}</td>"
            + f"<td>{escape(_format_optional_currency(candidate.get('price'), candidate.get('currency_code') or 'USD'))}</td>"
            + f"<td>{escape(str(candidate.get('availability_status', '')))}</td>"
            + '</tr>'
        )

    notes_html = ''.join(f"<li>{escape(str(note))}</li>" for note in notes) or '<li>No additional notes recorded.</li>'
    rows_html = ''.join(table_rows) or '<tr><td colspan="14">No candidates were returned for this run.</td></tr>'

    return f"""<!doctype html>
<html>
<head>
<meta charset='utf-8'>
<title>{title}</title>
<style>
  body {{ font-family: Arial, sans-serif; margin: 24px; color: #111827; }}
  h1, h2 {{ margin-bottom: 8px; }}
  .meta {{ color: #4b5563; margin-bottom: 18px; }}
  .summary-grid {{ display: grid; grid-template-columns: repeat(3, minmax(180px, 1fr)); gap: 12px; margin: 18px 0; }}
  .card {{ border: 1px solid #d1d5db; border-radius: 10px; padding: 12px; }}
  .label {{ font-size: 12px; color: #6b7280; text-transform: uppercase; }}
  .value {{ font-size: 20px; font-weight: 700; margin-top: 4px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
  th, td {{ border: 1px solid #d1d5db; padding: 8px; font-size: 12px; text-align: left; }}
  th {{ background: #f3f4f6; }}
  .note-box {{ background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 10px; padding: 12px; margin-top: 16px; }}
  @media print {{
    body {{ margin: 12px; }}
    .page-break-avoid {{ break-inside: avoid; }}
  }}
</style>
</head>
<body>
  <h1>{title}</h1>
  <div class='meta'>Generated from the Heater Quote Tool - Source mode: {source_label}</div>
  <div class='summary-grid page-break-avoid'>
    <div class='card'><div class='label'>Gallons</div><div class='value'>{_format_optional_number(summary.get('volume_gallons', 0), 0)}</div></div>
    <div class='card'><div class='label'>Temperature Rise</div><div class='value'>{_format_optional_number(summary.get('temperature_rise_f', 0), 1)} F</div></div>
    <div class='card'><div class='label'>Recommended BTU/hr</div><div class='value'>{_format_optional_number(summary.get('recommended_btu_per_hr', 0), 0)}</div></div>
    <div class='card'><div class='label'>Total BTUs Required</div><div class='value'>{_format_optional_number(summary.get('total_btu_required', 0), 0)}</div></div>
    <div class='card'><div class='label'>Desired Heat-up Hours</div><div class='value'>{_format_optional_number(summary.get('desired_heatup_hours', 0), 1)}</div></div>
    <div class='card'><div class='label'>Units</div><div class='value'>{int(summary.get('unit_count', 1) or 1)}</div></div>
  </div>
  <div class='note-box page-break-avoid'><strong>Recommendation note:</strong> {recommendation_note}</div>
  <h2>Recommended heater models</h2>
  <table>
    <thead>
      <tr>
        <th>Rank</th><th>Band</th><th>Brand</th><th>Model</th><th>SKU</th><th>Kind</th><th>Fuel</th><th>Units</th><th>Per Unit BTU/hr</th><th>Package BTU/hr</th><th>Est. Heat-up Hours</th><th>Per Unit Price</th><th>Package Price</th><th>Availability</th>
      </tr>
    </thead>
    <tbody>{rows_html}</tbody>
  </table>
  <div class='note-box'><strong>Tool notes</strong><ul>{notes_html}</ul></div>
</body>
</html>"""


def _build_printable_heater_report_url(html_text: str) -> str:
    return "data:text/html;charset=utf-8," + quote(html_text, safe="")


st.set_page_config(page_title='Heater Quote Tool', layout='wide')

create_db_and_tables()
with Session(engine) as session:
    seed_defaults(session)
    heater_dashboard = get_heater_quote_dashboard_summary(session)
    heater_settings = get_heater_quote_settings(session)
    quote_cases = list_quote_cases(session, include_closed=False, limit=250)
    recent_runs = list_heater_quote_runs(session, limit=10)

st.title('Heater Quote Tool')
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
        candidates_df = pd.DataFrame(display_rows)
        st.dataframe(candidates_df, width='stretch')

        report_html = _build_printable_heater_report_html(run_payload)
        st.download_button(
            'Download printable heater report (HTML)',
            data=report_html,
            file_name=f"heater_quote_run_{current_run_id}.html",
            mime='text/html',
            help='Download the same printer-friendly heater recommendation report as an HTML file you can save or print later.',
        )

        attach_col, info_col = st.columns([1, 1])
        with attach_col:
            selectable_candidates = {f"#{candidate['rank_order']} {candidate['model_name']} ({candidate.get('recommendation_band', 'review')})": candidate['id'] for candidate in candidates}
            selected_candidate_label = st.selectbox('Candidate to attach', options=list(selectable_candidates.keys()), help='Choose which heater recommendation you want to attach to a quote case.')
            attach_quote_case_id = st.selectbox(
                'Quote case to attach to',
                options=[case.id for case in quote_cases] if quote_cases else [],
                format_func=lambda value: next((f"{case.id} - {case.title}" for case in quote_cases if case.id == value), str(value)),
                help='Choose the open quote case that should receive this heater recommendation as a linked equipment suggestion.',
            ) if quote_cases else None
            if st.button('Attach selected heater to quote case', help='Click to attach the selected heater recommendation to the chosen quote case using the quote workflow external-link ledger.'):
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
                            )
                            st.success(f"Attached heater recommendation to quote case {attach_result['quote_case']['id']}.")
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
