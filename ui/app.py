from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from sqlmodel import Session, select

from app.core.database import create_db_and_tables, engine
from app.models.quote_tables import QuoteCase
from app.models.tables import Account, PoolVessel, Property
from app.services.bootstrap import seed_defaults
from app.services.quote_workflow import get_dashboard_summary

st.set_page_config(page_title='Unified Pool Service Operations Core', layout='wide')

create_db_and_tables()
with Session(engine) as session:
    seed_defaults(session)
    accounts_count = len(list(session.exec(select(Account)).all()))
    properties_count = len(list(session.exec(select(Property)).all()))
    vessels_count = len(list(session.exec(select(PoolVessel)).all()))
    active_quotes = len(list(session.exec(select(QuoteCase)).all()))
    quote_dashboard = get_dashboard_summary(session)

st.title('Unified Pool Service Operations Core')
st.caption('Operations dashboard shell for quoting, billing readiness, deliveries, front desk review, and modular estimating tools.')

m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric('Accounts', accounts_count, help='Total account records currently stored in the platform database.')
m2.metric('Properties', properties_count, help='Total property records currently stored in the platform database.')
m3.metric('Vessels', vessels_count, help='Total pool vessels currently stored in the platform database.')
m4.metric('Quote Cases', active_quotes, help='Total quote workflow cases currently tracked in the new workflow ledger.')
m5.metric('Stale Cases', quote_dashboard['totals']['stale_cases'], help='Cases that have been in their current stage longer than the configured threshold.')
m6.metric('Follow Ups Due', quote_dashboard['totals']['follow_ups_due'], help='Cases with a follow up due date on or before today.')

st.subheader('Operations launchpad')
launch_a, launch_b, launch_c, launch_d = st.columns(4)
with launch_a:
    st.page_link('ui/pages/11_Quote_Workflow.py', label='Quote Workflow', icon='🧭', help='Open the new quote workflow board to create, review, and move quote cases.')
    st.page_link('ui/pages/7_Invoice_Review.py', label='Invoice Review', icon='🧾', help='Open the invoice review queue for staged invoice parsing and approval.')
with launch_b:
    st.page_link('ui/pages/5_Commercial_Estimator.py', label='Commercial Estimator', icon='🏢', help='Open the commercial estimator for scenario building and pricing.')
    st.page_link('ui/pages/4_Residential_Estimator.py', label='Residential Estimator', icon='🏠', help='Open the residential estimator for service pricing workflows.')
with launch_c:
    st.page_link('ui/pages/6_Commercial_Deliveries.py', label='Commercial Deliveries', icon='🚚', help='Open monthly delivery reporting and property level billing review.')
    st.page_link('ui/pages/9_Tools.py', label='Tools', icon='🛠️', help='Open operational tools such as property verification and future equipment quote modules.')
with launch_d:
    st.page_link('ui/pages/8_Compare_&_Train.py', label='Compare + Train', icon='📊', help='Open compare and train workflows for pricing calibration and review.')
    st.page_link('ui/pages/10_Estimate_Library.py', label='Estimate Library', icon='📚', help='Open saved estimate runs and exported reporting views.')

st.subheader('Quote workflow dashboard')
st.caption('These cards mirror the current CRM bucket language so staff can recognize the same workflow while the platform becomes the orchestration layer.')

pipeline_columns = st.columns(2)
for index, pipeline in enumerate(quote_dashboard['pipelines']):
    with pipeline_columns[index % 2]:
        with st.container(border=True):
            st.markdown(f"### {pipeline['pipeline_name']}")
            st.caption(f"Pipeline slug: `{pipeline['pipeline_slug']}`")
            for stage in pipeline['stages']:
                label = f"{stage['stage_name']}"
                counts = f"{stage['count']} total"
                extras: list[str] = []
                if stage['stale_count']:
                    extras.append(f"{stage['stale_count']} stale")
                if stage['follow_ups_due']:
                    extras.append(f"{stage['follow_ups_due']} due")
                if stage['sent_not_viewed']:
                    extras.append(f"{stage['sent_not_viewed']} sent not viewed")
                suffix = f" | {' | '.join(extras)}" if extras else ''
                st.write(f"**{label}:** {counts}{suffix}")

with st.expander('What this dashboard is becoming', expanded=False):
    st.write('Repo B is being turned into the workflow and quote orchestration layer that mirrors CRM stages, tracks case age, and later will coordinate draft estimates in FreshBooks and live vendor pricing tools without forcing a full rebuild when workflow rules change.')
