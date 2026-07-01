from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import streamlit as st

from ui._shared import configure_page, db_session, page_header, section
from app.services.variance import chemical_variance, labor_variance

configure_page('Variance', icon='🎯')
page_header(
    'Expected vs Actual',
    'The forensic loop: what we priced/modeled a visit for vs what it actually took. Labor time and chemical '
    'cost, both valued in dollars — silent margin erosion, surfaced.',
    icon='🎯',
)

tab_labor, tab_chem = st.tabs(['Labor time', 'Chemical cost'])

# --------------------------------------------------------------------------
# Labor time variance
# --------------------------------------------------------------------------
with tab_labor:
    with db_session() as session:
        summary = labor_variance(session)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric('Visits analyzed', summary.visits_analyzed)
    m2.metric('Total variance', f'{summary.total_variance_minutes:+,.0f} min',
              help='Actual minus expected across all analyzed visits. Positive = over the priced time.')
    m3.metric('Variance cost', f'${summary.total_variance_cost:,.2f}',
              help='The variance minutes valued at the true cost per hour.')
    m4.metric('Properties overrunning', len(summary.overruns))

    if summary.visits_analyzed == 0:
        st.info('No labor actuals yet. Run a Skimmer sync so visits carry logged minutes.')
    else:
        if summary.overruns:
            section('Chronic overruns', 'Properties averaging well over their priced time — reprice or re-scope.')
            for p in summary.overruns:
                st.markdown(f'🔺 **{p.name}** — priced {p.avg_expected:.0f} min, averaging {p.avg_actual:.0f} min '
                            f'over {p.visits} visit(s). Bleeding **${p.total_variance_cost:,.2f}** in unpriced labor.')
        else:
            st.success('No chronic overruns — visits track close to priced time.')

        section('By property')
        st.dataframe(pd.DataFrame([{
            'Property': p.name, 'Visits': p.visits,
            'Avg expected (min)': round(p.avg_expected, 0), 'Avg actual (min)': round(p.avg_actual, 0),
            'Variance (min)': round(p.total_variance_minutes, 0), 'Variance cost': round(p.total_variance_cost, 2),
            'Overrun': '🔺' if p.overrun else '',
        } for p in summary.properties]), width='stretch', hide_index=True)

# --------------------------------------------------------------------------
# Chemical cost variance
# --------------------------------------------------------------------------
with tab_chem:
    with db_session() as session:
        chem = chemical_variance(session)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric('Visits analyzed', chem.visits_analyzed)
    m2.metric('Expected chemical', f'${chem.total_expected:,.2f}',
              help='Modeled chemical cost per visit (deterministic estimator) across analyzed visits.')
    m3.metric('Actual chemical', f'${chem.total_actual:,.2f}',
              help='Logged chemical usage valued at latest unit cost.')
    m4.metric('Variance', f'${chem.total_variance_cost:+,.2f}',
              help='Actual minus expected. Positive = over-using (waste); negative = under model (under-dosing or model over-estimates).')

    if chem.visits_analyzed == 0:
        st.info('No chemical actuals yet. Run a Skimmer sync so visits carry logged chemical usage.')
    else:
        overusers = [p for p in chem.properties if p.overrun]
        if overusers:
            section('Chemical over-use', 'Properties using materially more chemical than modeled — waste or a dosing issue.')
            for p in overusers:
                st.markdown(f'🔺 **{p.name}** — modeled ${p.avg_expected:,.2f}/visit, using ${p.avg_actual:,.2f}/visit '
                            f'over {p.visits} visit(s) (**+${p.total_variance_cost:,.2f}** total).')
        else:
            st.success('No properties are over-using chemical vs the model.')

        section('By property')
        st.dataframe(pd.DataFrame([{
            'Property': p.name, 'Visits': p.visits,
            'Avg expected $': round(p.avg_expected, 2), 'Avg actual $': round(p.avg_actual, 2),
            'Variance $': round(p.total_variance_cost, 2),
            'Flag': '🔺 over' if p.overrun else ('🔻 under' if p.avg_actual < p.avg_expected else ''),
        } for p in chem.properties]), width='stretch', hide_index=True)

        st.caption('Expected chemical cost comes from the deterministic estimator model per vessel. Consistent '
                   'under-use may mean the model over-estimates for that pool or techs are under-dosing; '
                   'consistent over-use is waste. Both are worth a look.')
