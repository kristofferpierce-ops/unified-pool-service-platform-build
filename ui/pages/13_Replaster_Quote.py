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
from app.services.replaster_quote import (
    DEFAULT_REPLASTER_QUOTE_CONFIG,
    build_replaster_quote,
    create_replaster_quote_run,
    list_replaster_quote_runs,
)
from ui._shared import configure_page, page_header

configure_page('Replaster Quote Tool', icon='🧱')

create_db_and_tables()
with Session(engine) as session:
    seed_defaults(session)
    recent_runs = list_replaster_quote_runs(session, limit=10)

config = DEFAULT_REPLASTER_QUOTE_CONFIG
finish_profiles = config['finish_profiles']
bond_profiles = config['bond_profiles']
labor_profiles = config['labor_profiles']
defaults = config['defaults']
tile_defaults = config['tile_defaults']
sub_defaults = config.get('subcontractor_defaults', {})

page_header('Replaster Quote Tool',
            'On-site replaster quote from surface area, tile footage, and chip-out measurements, with a material-cost or subcontractor template.',
            icon='🧱')

with st.expander('How this tool sizes the job', expanded=False):
    st.write('This page follows the supplied replaster estimating research: surface area drives finish and bond coat quantities, tile line footage drives tile quantity, and chip-out measurements drive HSR patch mortar. The tool keeps the waste factors, unit costs, labor profile, and target markup adjustable so field staff can tighten the quote on site instead of guessing later.')

with st.form('replaster_quote_form'):
    left, right = st.columns(2)
    with left:
        title = st.text_input('Run title', value='', help='Give the estimate a short label so staff can recognize it later in recent replaster quote history.')
        geometry_mode = st.selectbox(
            'Measurement mode',
            options=['rectangular_segmented', 'freeform_approximation', 'direct_surface_area'],
            format_func=lambda value: {
                'rectangular_segmented': 'Rectangular with shallow / slope / deep runs',
                'freeform_approximation': 'Freeform using measured perimeter and floor area',
                'direct_surface_area': 'Direct measured total surface area',
            }[value],
            help='Pick the field measurement method that best matches the shell you are standing in front of.',
        )
        finish_profile = st.selectbox(
            'Finish material',
            options=list(finish_profiles.keys()),
            format_func=lambda value: finish_profiles[value]['label'],
            help='Choose the plaster / aggregate finish family so the right bag coverage and default cost basis are used.',
        )
        bond_profile = st.selectbox(
            'Bond coat system',
            options=list(bond_profiles.keys()),
            format_func=lambda value: bond_profiles[value]['label'],
            help='Choose the bond coat system so the estimator can convert surface area into purchasing units.',
        )
        pricing_mode = st.selectbox(
            'Pricing mode',
            options=['detailed_materials_and_labor', 'subcontractor_linear_feet'],
            format_func=lambda value: {
                'detailed_materials_and_labor': 'Detailed materials and labor build-up',
                'subcontractor_linear_feet': 'Subcontractor linear-foot template',
            }[value],
            help='Choose whether the quote should price from the detailed takeoff or from subcontractor surface, tile, and bullnose lineal-foot rates.',
        )
        labor_profile = st.selectbox(
            'Labor profile',
            options=list(labor_profiles.keys()),
            format_func=lambda value: labor_profiles[value]['label'],
            help='Choose the access / difficulty profile used to auto-build the labor-hour baseline for this quote when detailed pricing is being used.',
        )
        replace_tile = st.checkbox('Include waterline tile replacement', value=True, help='Leave this on when the quote includes replacing the tile band along the pool perimeter.')
        feature_area_sqft = st.number_input('Measured feature area add-on', min_value=0.0, value=0.0, step=5.0, help='Add steps, benches, shelves, spillways, or other surfaces that need finish but are easy to miss in a quick shell takeoff.')

        if geometry_mode == 'rectangular_segmented':
            length_ft = st.number_input('Pool length (ft)', min_value=0.0, value=28.0, step=1.0, help='Measured pool length used for perimeter and floor calculations.')
            width_ft = st.number_input('Pool width (ft)', min_value=0.0, value=14.0, step=1.0, help='Measured pool width used for perimeter and floor calculations.')
            shallow_depth_ft = st.number_input('Shallow depth (ft)', min_value=0.0, value=3.5, step=0.5, help='Measured shallow-end water depth used for wall area and floor slope calculations.')
            deep_depth_ft = st.number_input('Deep depth (ft)', min_value=0.0, value=6.0, step=0.5, help='Measured deep-end water depth used for wall area and floor slope calculations.')
            shallow_flat_run_ft = st.number_input('Shallow flat run (ft)', min_value=0.0, value=10.0, step=0.5, help='Horizontal run length of the shallow flat section of the floor.')
            slope_run_ft = st.number_input('Slope run (ft)', min_value=0.0, value=10.0, step=0.5, help='Horizontal run length of the sloped transition between shallow and deep water.')
            deep_flat_run_ft = st.number_input('Deep flat run (ft)', min_value=0.0, value=8.0, step=0.5, help='Horizontal run length of the deep flat section of the floor.')
            perimeter_ft = 0.0
            average_depth_ft = 0.0
            floor_area_sqft = 0.0
            total_surface_area_sqft = 0.0
        elif geometry_mode == 'freeform_approximation':
            perimeter_ft = st.number_input('Measured perimeter / tile line (ft)', min_value=0.0, value=110.0, step=1.0, help='Measured lineal footage along the waterline used for wall and tile calculations.')
            average_depth_ft = st.number_input('Average depth (ft)', min_value=0.0, value=5.25, step=0.25, help='Average water depth used for the wall-area approximation.')
            floor_area_sqft = st.number_input('Measured floor plan area (sq ft)', min_value=0.0, value=525.0, step=5.0, help='Measured or sketched floor area of the shell excluding steps and benches already entered above.')
            length_ft = width_ft = shallow_depth_ft = deep_depth_ft = shallow_flat_run_ft = slope_run_ft = deep_flat_run_ft = 0.0
            total_surface_area_sqft = 0.0
        else:
            total_surface_area_sqft = st.number_input('Measured total interior surface area (sq ft)', min_value=0.0, value=900.0, step=5.0, help='Use this when you already measured the full shell directly and do not need the tool to derive the area from dimensions.')
            perimeter_ft = st.number_input('Measured perimeter / tile line (ft)', min_value=0.0, value=84.0, step=1.0, help='Measured lineal footage of the waterline used for tile calculations when tile replacement is included.')
            average_depth_ft = st.number_input('Average depth for notes (ft)', min_value=0.0, value=4.75, step=0.25, help='This is optional context for saved runs when the shell area is already measured directly.')
            length_ft = width_ft = shallow_depth_ft = deep_depth_ft = shallow_flat_run_ft = slope_run_ft = deep_flat_run_ft = floor_area_sqft = 0.0

    with right:
        surface_linear_feet = st.number_input('Surface lineal feet override', min_value=0.0, value=0.0, step=1.0, help='Leave this at zero to let the tool use the measured perimeter as the resurfacing lineal-foot basis. Enter a value when your subcontractor prices the surface scope from a different measured lineal-foot count.')
        tile_linear_feet = st.number_input('Tile line feet override', min_value=0.0, value=0.0, step=1.0, help='Leave this at zero to use the measured perimeter. Enter a value only when tile replacement applies to selected sections instead of the full perimeter.')
        bullnose_linear_feet = st.number_input('Bullnose / step-edge lineal feet', min_value=0.0, value=0.0, step=1.0, help='Enter the measured lineal feet of bullnose step-edge replacement when the subcontractor carries it as a separate unit-price item.')
        tile_height_in = st.number_input('Tile band height (in)', min_value=0.0, value=float(defaults['tile_height_in']), step=0.5, help='Measured tile band height used to convert lineal feet into tile square footage.')
        tile_length_in = st.number_input('Tile length (in)', min_value=1.0, value=float(tile_defaults['tile_length_in']), step=1.0, help='Face length of the chosen tile used to turn tile square footage into tile count.')
        tile_width_in = st.number_input('Tile width (in)', min_value=1.0, value=float(tile_defaults['tile_width_in']), step=1.0, help='Face width of the chosen tile used to turn tile square footage into tile count.')
        target_margin_pct = st.number_input('Target markup / margin percent', min_value=0.0, max_value=95.0, value=float(defaults['target_margin_pct']), step=1.0, help='Adjust this to change the sell price the tool recommends from the underlying real cost basis.')
        additional_labor_hours = st.number_input('Additional labor hours', min_value=0.0, value=0.0, step=0.5, help='Add hours for demo complications, long walks, staging, or owner-requested extras that the base labor profile does not capture.')
        manual_total_labor_hours_override = st.number_input('Manual total labor-hour override', min_value=0.0, value=0.0, step=0.5, help='Leave this at zero to use the auto labor model. Enter a value only when you want to override the full labor-hour total directly.')
        if pricing_mode == 'subcontractor_linear_feet':
            subcontract_surface_unit_cost = st.number_input('Subcontract surface price per linear ft', min_value=0.0, value=float(sub_defaults.get('surface_linear_feet_cost', 0.0) or 0.0), step=1.0, help='Enter the subcontractor unit price per linear foot for the resurfacing scope.')
            subcontract_tile_unit_cost = st.number_input('Subcontract tile price per linear ft', min_value=0.0, value=float(sub_defaults.get('tile_linear_feet_cost', 0.0) or 0.0), step=1.0, help='Enter the subcontractor unit price per linear foot for waterline tile replacement.')
            subcontract_bullnose_unit_cost = st.number_input('Subcontract bullnose price per linear ft', min_value=0.0, value=float(sub_defaults.get('bullnose_linear_feet_cost', 0.0) or 0.0), step=1.0, help='Enter the subcontractor unit price per linear foot for bullnose step-edge replacement.')
            finish_unit_cost_override = float(finish_profiles[finish_profile]['default_unit_cost'])
            bond_unit_cost_override = float(bond_profiles[bond_profile]['default_unit_cost'])
            patch_unit_cost_override = 32.0
            tile_unit_cost_override = float(tile_defaults['default_tile_unit_cost'])
            thinset_unit_cost_override = float(tile_defaults['thinset_unit_cost'])
            grout_allowance_per_sqft_override = float(tile_defaults['grout_allowance_per_sqft'])
        else:
            subcontract_surface_unit_cost = float(sub_defaults.get('surface_linear_feet_cost', 0.0) or 0.0)
            subcontract_tile_unit_cost = float(sub_defaults.get('tile_linear_feet_cost', 0.0) or 0.0)
            subcontract_bullnose_unit_cost = float(sub_defaults.get('bullnose_linear_feet_cost', 0.0) or 0.0)
            finish_unit_cost_override = st.number_input('Finish bag cost override', min_value=0.0, value=float(finish_profiles[finish_profile]['default_unit_cost']), step=1.0, help='Adjust the finish material cost basis when the current distributor price differs from the default research baseline.')
            bond_unit_cost_override = st.number_input('Bond coat unit cost override', min_value=0.0, value=float(bond_profiles[bond_profile]['default_unit_cost']), step=1.0, help='Adjust the bond coat cost basis when your actual supplier price differs from the default baseline.')
            patch_unit_cost_override = st.number_input('HSR patch bag cost override', min_value=0.0, value=32.0, step=1.0, help='Adjust the patch material bag price when your actual supplier quote differs from the default baseline.')
            tile_unit_cost_override = st.number_input('Tile cost override per tile', min_value=0.0, value=float(tile_defaults['default_tile_unit_cost']), step=0.25, help='Adjust the selected tile cost basis per tile when the chosen finish band uses a different tile price.')
            thinset_unit_cost_override = st.number_input('Thin-set bag cost override', min_value=0.0, value=float(tile_defaults['thinset_unit_cost']), step=1.0, help='Adjust the pool-rated thin-set cost basis per bag.')
            grout_allowance_per_sqft_override = st.number_input('Grout allowance per tile sq ft', min_value=0.0, value=float(tile_defaults['grout_allowance_per_sqft']), step=0.1, help='Adjust the grout allowance carried on the tile-band area until the final grout system is selected.')

    st.write('**Hollow-spot chip-out measurements**')
    patch_seed = pd.DataFrame([
        {'label': 'Patch 1', 'length_ft': 3.0, 'width_ft': 2.0, 'avg_depth_in': 1.0, 'shape_factor': 1.0},
        {'label': 'Patch 2', 'length_ft': 2.0, 'width_ft': 2.0, 'avg_depth_in': 0.75, 'shape_factor': 1.0},
        {'label': 'Patch 3', 'length_ft': 4.0, 'width_ft': 1.5, 'avg_depth_in': 0.5, 'shape_factor': 1.0},
    ])
    patch_editor = st.data_editor(
        patch_seed,
        width='stretch',
        hide_index=True,
        num_rows='dynamic',
        key='replaster_patch_editor',
    )

    submitted = st.form_submit_button('Build replaster quote', help='Click to convert the field measurements into a material takeoff, cost basis, and recommended sell price.')

if submitted:
    input_payload = {
        'title': title,
        'geometry_mode': geometry_mode,
        'finish_profile': finish_profile,
        'bond_profile': bond_profile,
        'labor_profile': labor_profile,
        'total_surface_area_sqft': total_surface_area_sqft,
        'perimeter_ft': perimeter_ft,
        'surface_linear_feet': surface_linear_feet,
        'tile_linear_feet': tile_linear_feet,
        'bullnose_linear_feet': bullnose_linear_feet,
        'tile_height_in': tile_height_in,
        'tile_length_in': tile_length_in,
        'tile_width_in': tile_width_in,
        'replace_tile': replace_tile,
        'length_ft': length_ft,
        'width_ft': width_ft,
        'shallow_depth_ft': shallow_depth_ft,
        'deep_depth_ft': deep_depth_ft,
        'shallow_flat_run_ft': shallow_flat_run_ft,
        'slope_run_ft': slope_run_ft,
        'deep_flat_run_ft': deep_flat_run_ft,
        'average_depth_ft': average_depth_ft,
        'floor_area_sqft': floor_area_sqft,
        'feature_area_sqft': feature_area_sqft,
        'patches': patch_editor.to_dict(orient='records') if hasattr(patch_editor, 'to_dict') else [],
        'target_margin_pct': target_margin_pct,
        'pricing_mode': pricing_mode,
        'finish_unit_cost_override': finish_unit_cost_override,
        'bond_unit_cost_override': bond_unit_cost_override,
        'patch_unit_cost_override': patch_unit_cost_override,
        'tile_unit_cost_override': tile_unit_cost_override,
        'thinset_unit_cost_override': thinset_unit_cost_override,
        'grout_allowance_per_sqft_override': grout_allowance_per_sqft_override,
        'subcontract_surface_unit_cost': subcontract_surface_unit_cost,
        'subcontract_tile_unit_cost': subcontract_tile_unit_cost,
        'subcontract_bullnose_unit_cost': subcontract_bullnose_unit_cost,
        'manual_total_labor_hours_override': manual_total_labor_hours_override,
        'additional_labor_hours': additional_labor_hours,
    }
    with Session(engine) as session:
        try:
            output_payload = build_replaster_quote(session, **input_payload)
            run = create_replaster_quote_run(session, title=title or 'Replaster quote run', input_payload=input_payload, output_payload=output_payload)
            st.session_state['replaster_quote_run_id'] = run['id']
            st.session_state['replaster_quote_run_output'] = output_payload
            st.success(f"Saved replaster quote run {run['id']}.")
        except ValueError as exc:
            st.error(str(exc))

current_run_id = st.session_state.get('replaster_quote_run_id')
current_run_output = st.session_state.get('replaster_quote_run_output')
if current_run_id and current_run_output:
    output = current_run_output
    area_summary = output['area_summary']
    tile_summary = output['tile_summary']
    cost_basis = output['cost_basis']
    patch_summary = output['patch_summary']
    quantities = output['quantities']
    labor_hours = output['labor_hours']

    st.subheader('Replaster quote summary')
    s1, s2, s3, s4, s5 = st.columns(5)
    s1.metric('Total surface area', f"{area_summary['total_area_sqft']:,.1f} sq ft", help='Interior shell area used to size finish and bond coat materials.')
    s2.metric('Tile line', f"{tile_summary['tile_linear_feet']:,.1f} ft", help='Waterline footage used to size the tile band and tile quantity.')
    s3.metric('Patch volume', f"{patch_summary['total_volume_ft3']:,.2f} ft³", help='Measured hollow-spot volume used to size HSR patch mortar.')
    s4.metric('Real cost', f"${cost_basis['real_cost']:,.0f}", help='Material, labor, and overhead cost basis before markup.')
    s5.metric('Recommended sell', f"${cost_basis['sell_price']:,.0f}", help='Sell price calculated from the selected target markup / margin percent.')

    st.write('**Active pricing lines**')
    st.dataframe(pd.DataFrame(output['pricing_lines']), width='stretch', hide_index=True)

    with st.expander('Detailed material takeoff reference', expanded=output['cost_basis'].get('pricing_mode') != 'subcontractor_linear_feet'):
        st.dataframe(pd.DataFrame(output['material_lines']), width='stretch', hide_index=True)

    q1, q2, q3, q4 = st.columns(4)
    q1.metric('Surface lineal feet', f"{tile_summary['surface_linear_feet']:,.1f} ft", help='Lineal-foot basis used for subcontract resurfacing pricing when the subcontractor template is selected.')
    q2.metric('Bond coat units', int(quantities['bond_units']), help='Estimated number of bond-coat purchasing units including waste.')
    q3.metric('Patch bags', int(quantities['patch_bags']), help='Estimated number of HSR patch bags including waste.')
    q4.metric('Bullnose edge', f"{tile_summary['bullnose_linear_feet']:,.1f} ft", help='Measured bullnose / step-edge footage carried when the subcontractor template is used.')

    st.write('**Labor basis**')
    st.dataframe(pd.DataFrame([{'Labor bucket': key, 'Hours': value} for key, value in labor_hours.items()]), width='stretch', hide_index=True)

    st.write('**Patch details**')
    if patch_summary['rows']:
        st.dataframe(pd.DataFrame(patch_summary['rows']), width='stretch', hide_index=True)
    else:
        st.info('No hollow-spot patches were entered for this run.')

    st.write('**Notes**')
    for note in output.get('notes', []):
        st.write(f'- {note}')

st.subheader('Recent replaster quote runs')
if recent_runs:
    recent_df = pd.DataFrame([
        {
            'Run Id': run['id'],
            'Title': run.get('title') or '',
            'Created At': run.get('created_at'),
            'Finish': (run.get('input') or {}).get('finish_profile'),
            'Sell Price': ((run.get('output') or {}).get('cost_basis') or {}).get('sell_price', 0.0),
            'Real Cost': ((run.get('output') or {}).get('cost_basis') or {}).get('real_cost', 0.0),
        }
        for run in recent_runs
    ])
    st.dataframe(recent_df, width='stretch', hide_index=True)
else:
    st.caption('No replaster quote runs have been created yet.')
