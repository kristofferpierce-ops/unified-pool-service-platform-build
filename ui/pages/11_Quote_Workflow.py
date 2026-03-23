from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from sqlmodel import Session, select

from app.core.database import create_db_and_tables, engine
from app.models.quote_tables import QuoteCase
from app.models.tables import Account, Property
from app.services.bootstrap import seed_defaults
from app.services.quote_workflow import (
    create_quote_case,
    get_dashboard_summary,
    get_quote_workflow_config,
    list_quote_cases,
    list_stage_options,
    move_quote_case,
    serialize_quote_case,
)

st.set_page_config(page_title='Quote Workflow', layout='wide')

create_db_and_tables()
with Session(engine) as session:
    seed_defaults(session)
    workflow_config = get_quote_workflow_config(session)
    account_options = list(session.exec(select(Account).order_by(Account.name)).all())
    property_options = list(session.exec(select(Property).order_by(Property.name)).all())
    dashboard = get_dashboard_summary(session)

pipeline_options = workflow_config.get('pipelines', [])
pipeline_lookup = {item['slug']: item for item in pipeline_options}

st.title('Quote Workflow')
st.caption('Create quote cases, move them across the mirrored CRM buckets, and review age, follow up timing, and visibility at a glance.')

summary_a, summary_b, summary_c, summary_d = st.columns(4)
summary_a.metric('Open Cases', dashboard['totals']['open_cases'], help='Cases that are not in a closed stage.')
summary_b.metric('Stale Cases', dashboard['totals']['stale_cases'], help='Cases that have sat in their current stage longer than the configured threshold.')
summary_c.metric('Follow Ups Due', dashboard['totals']['follow_ups_due'], help='Cases with a follow up date due today or earlier.')
summary_d.metric('Sent Not Viewed', dashboard['totals']['sent_not_viewed'], help='Cases in sent style stages that have not yet been marked viewed.')

with st.expander('Create new quote case', expanded=True):
    with st.form('create_quote_case_form', clear_on_submit=True):
        c1, c2 = st.columns(2)
        selected_pipeline_slug = c1.selectbox(
            'Pipeline',
            options=[item['slug'] for item in pipeline_options],
            format_func=lambda slug: pipeline_lookup[slug]['name'],
            help='Select the workflow bucket family that should own this quote request.',
        )
        stage_choices = list_stage_options(workflow_config, selected_pipeline_slug)
        selected_stage_slug = c2.selectbox(
            'Starting stage',
            options=[item['slug'] for item in stage_choices],
            index=0,
            format_func=lambda slug: next(stage['name'] for stage in stage_choices if stage['slug'] == slug),
            help='Choose the starting stage. Most new requests should begin in Info + Costing.',
        )
        title = st.text_input('Case title', help='Use a short title that makes the request obvious at a glance.')
        d1, d2, d3 = st.columns(3)
        requester_name = d1.text_input('Requester name', help='Customer or caller name tied to this quote request.')
        requester_phone = d2.text_input('Requester phone', help='Primary phone number for follow up and CRM matching.')
        requester_email = d3.text_input('Requester email', help='Primary email for FreshBooks estimate delivery later.')
        e1, e2 = st.columns(2)
        selected_account_name = e1.selectbox(
            'Account',
            options=[''] + [account.name for account in account_options],
            help='Optional internal account link for known customers or associations.',
        )
        selected_property_name = e2.selectbox(
            'Property',
            options=[''] + [prop.name for prop in property_options],
            help='Optional property link for requests tied to a specific property.',
        )
        assigned_to = st.text_input('Assigned to', help='Optional owner for the case inside the office workflow.')
        description = st.text_area('Description', help='Add intake notes, pricing notes, or any context needed before the case moves into quoting.')
        submitted = st.form_submit_button('Create quote case', help='Create the internal quote case in the workflow ledger.')
        if submitted:
            if not title.strip():
                st.error('Case title is required.')
            else:
                account_id = next((account.id for account in account_options if account.name == selected_account_name), None)
                property_id = next((prop.id for prop in property_options if prop.name == selected_property_name), None)
                with Session(engine) as session:
                    case = create_quote_case(
                        session,
                        pipeline_slug=selected_pipeline_slug,
                        stage_slug=selected_stage_slug,
                        title=title.strip(),
                        requester_name=requester_name.strip(),
                        requester_phone=requester_phone.strip(),
                        requester_email=requester_email.strip(),
                        account_id=account_id,
                        property_id=property_id,
                        description=description.strip(),
                        assigned_to=assigned_to.strip(),
                    )
                st.success(f'Created {case.quote_number} in {selected_pipeline_slug}.')
                st.rerun()

st.subheader('Case queue')
filter_a, filter_b, filter_c = st.columns(3)
selected_pipeline_filter = filter_a.selectbox(
    'Filter by pipeline',
    options=['all'] + [item['slug'] for item in pipeline_options],
    format_func=lambda slug: 'All pipelines' if slug == 'all' else pipeline_lookup[slug]['name'],
    help='Limit the queue to a single pipeline when you want to work one bucket at a time.',
)
selected_stage_filter = filter_b.text_input('Filter by stage slug', help='Optional exact stage slug filter such as quoting or follow_up.')
include_closed = filter_c.checkbox('Include closed cases', value=False, help='Show closed cases when you need historical context.')

with Session(engine) as session:
    cases = list_quote_cases(
        session,
        pipeline_slug=None if selected_pipeline_filter == 'all' else selected_pipeline_filter,
        stage_slug=selected_stage_filter.strip() or None,
        include_closed=include_closed,
        limit=200,
    )
    serialized_cases = [serialize_quote_case(session, case, workflow_config) for case in cases]

if not serialized_cases:
    st.info('No quote cases match the current filters yet.')
else:
    for case in serialized_cases:
        stage_choices = list_stage_options(workflow_config, case['pipeline_slug'])
        allowed_stage_labels = {stage['slug']: stage['name'] for stage in stage_choices}
        with st.container(border=True):
            row1, row2, row3 = st.columns([2, 2, 2])
            row1.markdown(f"### {case['quote_number']} | {case['title']}")
            row1.caption(f"{case['pipeline_name']} | {case['stage_name']}")
            row2.metric('Age', f"{case['age_days']} days", help='Total days since the quote case was created.')
            row2.metric('Stage Age', f"{case['stage_age_days']} days", help='Days spent in the current stage.')
            viewed_label = 'Yes' if case['is_viewed'] else 'No'
            row3.metric('Viewed', viewed_label, help='Quick glance indicator showing whether the quote has been marked viewed yet.')
            detail_a, detail_b, detail_c = st.columns([2, 2, 2])
            detail_a.write(f"**Requester:** {case['requester_name'] or 'Unknown'}")
            detail_a.write(f"**Phone:** {case['requester_phone'] or 'Not set'}")
            detail_b.write(f"**Follow Up Due:** {case['follow_up_due_on'] or 'Not set'}")
            detail_b.write(f"**FreshBooks Status:** {case['freshbooks_status']}")
            detail_c.write(f"**Sync Status:** {case['sync_status']}")
            detail_c.write(f"**Assigned To:** {case['assigned_to'] or 'Unassigned'}")
            if case['description']:
                st.write(case['description'])
            move_cols = st.columns([3, 2, 1])
            target_stage_slug = move_cols[0].selectbox(
                f"Move {case['quote_number']} to",
                options=[item['slug'] for item in stage_choices],
                index=[item['slug'] for item in stage_choices].index(case['stage_slug']),
                format_func=lambda slug, labels=allowed_stage_labels: labels[slug],
                key=f"move_target_{case['id']}",
                help='Select the next stage you want the case to move into. Allowed stage rules are enforced by the service layer.',
            )
            move_reason = move_cols[1].text_input(
                'Move note',
                key=f"move_reason_{case['id']}",
                help='Optional note explaining why the case is moving stages.',
            )
            if move_cols[2].button('Move', key=f"move_button_{case['id']}", help='Apply the stage change for this quote case.'):
                with Session(engine) as session:
                    move_quote_case(
                        session,
                        case['id'],
                        target_stage_slug=target_stage_slug,
                        moved_by='streamlit_operator',
                        move_reason=move_reason,
                    )
                st.rerun()
