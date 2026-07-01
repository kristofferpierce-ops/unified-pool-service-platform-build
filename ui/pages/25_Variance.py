from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import streamlit as st

from ui._shared import configure_page, db_session, page_header, section
from app.services.variance import labor_variance

configure_page('Variance', icon='🎯')
page_header(
    'Expected vs Actual',
    'The forensic loop: what we priced a visit to take (the vessel\'s minutes) vs what it actually took '
    '(Skimmer\'s logged minutes), valued at the true $/hour. Overruns are silent margin erosion.',
    icon='🎯',
)

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
    st.info('No labor actuals yet. Run a Skimmer sync so visits carry logged minutes, then variance shows here.')
else:
    if summary.overruns:
        section('Chronic overruns', 'Properties whose visits average well over their priced time — reprice or re-scope.')
        for p in summary.overruns:
            st.markdown(f'🔺 **{p.name}** — priced {p.avg_expected:.0f} min, averaging {p.avg_actual:.0f} min '
                        f'over {p.visits} visit(s). Bleeding **${p.total_variance_cost:,.2f}** in unpriced labor.')
    else:
        st.success('No chronic overruns — visits are tracking close to their priced time.')

    section('By property')
    st.dataframe(pd.DataFrame([{
        'Property': p.name,
        'Visits': p.visits,
        'Avg expected (min)': round(p.avg_expected, 0),
        'Avg actual (min)': round(p.avg_actual, 0),
        'Variance (min)': round(p.total_variance_minutes, 0),
        'Variance cost': round(p.total_variance_cost, 2),
        'Overrun': '🔺' if p.overrun else '',
    } for p in summary.properties]), width='stretch', hide_index=True)

    section('Worst visits')
    st.dataframe(pd.DataFrame([{
        'Date': v.date,
        'Property': v.property_name,
        'Expected (min)': round(v.expected_minutes, 0),
        'Actual (min)': round(v.actual_minutes, 0),
        'Variance (min)': round(v.variance_minutes, 0),
        'Variance cost': round(v.variance_cost, 2),
    } for v in summary.visit_rows[:15]]), width='stretch', hide_index=True)

    st.caption('This is the labor-time dimension. Chemical-usage and margin variance are the next dimensions '
               'that read these same actuals.')
