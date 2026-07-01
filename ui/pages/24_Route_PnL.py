from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import streamlit as st

from ui._shared import configure_page, date_range_selector, db_session, page_header, section
from app.services.route_pnl import route_pnl

configure_page('Route P&L', icon='🚚')
page_header(
    'Route Profitability',
    'Which routes make money and which cost more. Cost per route is exact (labor + chemicals on its visits); '
    'revenue is each customer\'s FreshBooks revenue split evenly across their visits.',
    icon='🚚',
)

section('Period')
start, end = date_range_selector('route')
if start or end:
    st.caption(f"Scoped to routes/visits {start or '(open)'} → {end or '(open)'}.")

with db_session() as session:
    summary = route_pnl(session, start, end)

m1, m2, m3, m4 = st.columns(4)
m1.metric('Route revenue (allocated)', f'${summary.total_revenue:,.2f}')
m2.metric('Route cost', f'${summary.total_cost:,.2f}')
m3.metric('Route profit', f'${summary.total_profit:,.2f}')
m4.metric('Unrouted visits', summary.unrouted_visits,
          help='Service visits not attached to any route yet (not counted in route totals).')

if not summary.routes:
    st.info('No routes yet. Run a Skimmer sync (routes + work orders) and pull FreshBooks invoices, then '
            'route-level P&L shows here.')
else:
    section('Profit by route', 'Sorted most to least profitable.')
    st.dataframe(pd.DataFrame([{
        'Route': r.name,
        'Date': r.route_date,
        'Tech': r.technician,
        'Visits': r.visits,
        'Revenue': round(r.revenue, 2),
        'Cost': round(r.cost, 2),
        'Profit': round(r.profit, 2),
        'Margin %': round(r.margin_pct, 1),
    } for r in summary.routes]), width='stretch', hide_index=True)

    section('By technician')
    st.dataframe(pd.DataFrame([{
        'Technician': t.technician,
        'Routes': t.routes,
        'Visits': t.visits,
        'Revenue': round(t.revenue, 2),
        'Cost': round(t.cost, 2),
        'Profit': round(t.profit, 2),
        'Margin %': round(t.margin_pct, 1),
    } for t in summary.technicians]), width='stretch', hide_index=True)

    losers = [r for r in summary.routes if r.profit < 0]
    if losers:
        section('Underperforming routes')
        for r in losers:
            st.markdown(f'🔻 **{r.name}** ({r.technician}) — revenue ${r.revenue:,.2f}, cost ${r.cost:,.2f}, '
                        f'**loss ${abs(r.profit):,.2f}** across {r.visits} visits.')
    else:
        st.success('No routes are running at a loss on the data recorded so far.')

    st.caption('Revenue allocation: each customer\'s invoiced revenue is split evenly across their service '
               'visits, then attributed to the route each visit is on. Cost is exact per visit.')
