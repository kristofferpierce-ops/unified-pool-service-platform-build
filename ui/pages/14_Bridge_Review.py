from __future__ import annotations

from datetime import date
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from sqlmodel import Session

from app.core.database import create_db_and_tables, engine
from app.services.bootstrap import seed_defaults
from app.services.front_desk import (
    add_sms_thread_review_note,
    apply_sms_thread_to_lacrm,
    approve_sms_thread,
    bridge_review_summary,
    build_candidates_for_sms_thread,
    build_sms_thread_lacrm_apply_plan,
    clean_display_text,
    create_follow_up_task,
    get_sms_thread_detail,
    lacrm_apply_status,
    list_review_actions,
    list_sms_threads,
    review_action_summary,
    save_routing_preference,
    set_sms_thread_review_status,
)

st.set_page_config(page_title='Bridge Review', layout='wide')

create_db_and_tables()
with Session(engine) as _session:
    seed_defaults(_session)


def _run_db(fn):
    with Session(engine) as session:
        return fn(session)


def _status_badge(status: str) -> None:
    if status == 'approved':
        st.success(status)
    elif status == 'pending_review':
        st.warning(status)
    elif status in {'closed', 'ignored'}:
        st.info(status)
    else:
        st.caption(status or 'unknown')


def _candidate_ref_options(detail: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    for candidate in detail.get('candidates') or []:
        ref = str(candidate.get('contact_ref') or '').strip()
        if ref and ref not in refs:
            refs.append(ref)
    return refs


st.title('Bridge Review')
st.caption('Platform-side review of bridge-origin SMS threads. The original bridge/Data Hub remains on port 8000; this page writes platform state by default and uses Step 6 guarded LACRM apply controls only when explicitly requested.')

summary = _run_db(bridge_review_summary)
review_summary = _run_db(review_action_summary)
lacrm_status = _run_db(lacrm_apply_status)

metric_cols = st.columns(6)
metric_cols[0].metric('SMS Threads', summary.get('sms_threads_total', 0))
metric_cols[1].metric('SMS Messages', summary.get('sms_messages_total', 0))
metric_cols[2].metric('Pending Review', review_summary.get('pending_sms_threads_total', 0))
metric_cols[3].metric('Approved', review_summary.get('approved_sms_threads_total', 0))
metric_cols[4].metric('CRM Apply Actions', review_summary.get('crm_apply_actions_total', 0))
metric_cols[5].metric('LACRM Mode', lacrm_status.get('mode', lacrm_status.get('sync_mode', 'dry_run')))

with st.expander('Safety and connection status', expanded=False):
    st.json(lacrm_status)
    st.markdown(
        '- Dry-run apply writes local `CRMApplyAction` rows only.\n'
        '- Live LACRM writes remain blocked unless the API key, live-write env flag, dry-run override, and explicit confirmation are all present.\n'
        '- Bridge Data Hub remains available separately at `http://127.0.0.1:8000`.'
    )

st.subheader('Filters')
filter_cols = st.columns([1, 1, 1, 1, 1])
status = filter_cols[0].selectbox('Status', ['', 'pending_review', 'approved', 'needs_follow_up', 'waiting_on_customer', 'waiting_on_internal', 'closed', 'ignored', 'escalated'], index=0)
local_day = filter_cols[1].text_input('Local day', value='', placeholder='YYYY-MM-DD')
external_phone = filter_cols[2].text_input('External phone', value='')
source = filter_cols[3].text_input('Source', value='', placeholder='message_sync')
limit = filter_cols[4].number_input('Limit', min_value=5, max_value=250, value=50, step=5)

threads_payload = _run_db(lambda session: list_sms_threads(session, status=status, external_phone=external_phone, local_day=local_day, source=source, limit=int(limit), offset=0))
threads = threads_payload.get('threads') or []

left, right = st.columns([0.42, 0.58], gap='large')

with left:
    st.subheader('SMS Threads')
    if not threads:
        st.info('No platform SMS threads match the current filters.')
    thread_labels: list[str] = []
    thread_by_label: dict[str, dict[str, Any]] = {}
    for thread in threads:
        label = f"#{thread.get('id')} · {thread.get('external_phone') or 'unknown'} · {thread.get('local_day') or ''} · {thread.get('status') or ''} · {thread.get('message_count', 0)} msg"
        thread_labels.append(label)
        thread_by_label[label] = thread
    selected_label = st.radio('Select a thread', thread_labels, label_visibility='collapsed') if thread_labels else ''

selected_thread_id = None
if threads and selected_label:
    selected_thread_id = int(thread_by_label[selected_label]['id'])

if selected_thread_id:
    detail = _run_db(lambda session: get_sms_thread_detail(session, selected_thread_id))
else:
    detail = {}

with right:
    st.subheader('Selected Thread')
    if not detail:
        st.info('Select a thread to review messages and actions.')
    else:
        top_a, top_b, top_c, top_d = st.columns(4)
        top_a.metric('Thread', detail.get('id'))
        top_b.metric('Phone', detail.get('external_phone') or '')
        top_c.metric('Messages', detail.get('message_count', 0))
        with top_d:
            _status_badge(detail.get('status') or '')

        st.markdown('#### Summary')
        st.write(clean_display_text(detail.get('display_summary') or detail.get('summary') or ''))

        st.markdown('#### Messages')
        for message in detail.get('messages') or []:
            with st.container(border=True):
                st.caption(f"{message.get('occurred_at', '')} · {message.get('direction', '')} · {message.get('from_phone', '')} → {message.get('to_phone', '')}")
                st.write(clean_display_text(message.get('display_body') or message.get('body') or ''))

        action_tabs = st.tabs(['Review', 'Candidates', 'LACRM Dry Run', 'History'])

        with action_tabs[0]:
            st.markdown('##### Review status / note')
            status_choice = st.selectbox('Set review status', ['pending_review', 'needs_follow_up', 'waiting_on_customer', 'waiting_on_internal', 'approved', 'closed', 'ignored', 'escalated'])
            status_note = st.text_area('Status note', key=f'status_note_{selected_thread_id}')
            decided_by = st.text_input('Decided by', value='operator', key=f'decided_by_{selected_thread_id}')
            if st.button('Save review status', key=f'save_status_{selected_thread_id}'):
                result = _run_db(lambda session: set_sms_thread_review_status(session, selected_thread_id, status=status_choice, decided_by=decided_by, notes=status_note))
                st.success('Review status saved.')
                st.json(result)
                st.rerun()
            free_note = st.text_area('Add review note', key=f'free_note_{selected_thread_id}')
            if st.button('Add note', key=f'add_note_{selected_thread_id}'):
                result = _run_db(lambda session: add_sms_thread_review_note(session, selected_thread_id, note=free_note, decided_by=decided_by))
                st.success('Note added.')
                st.json(result)

            st.markdown('##### Platform follow-up task')
            task_title = st.text_input('Task title', value=f"Follow up SMS from {detail.get('external_phone') or ''}", key=f'task_title_{selected_thread_id}')
            task_assignee = st.text_input('Assignee ref', value='', key=f'task_assignee_{selected_thread_id}')
            task_due = st.date_input('Due date', value=None, key=f'task_due_{selected_thread_id}')
            if st.button('Queue platform task', key=f'task_{selected_thread_id}'):
                due_date = task_due if isinstance(task_due, date) else None
                result = _run_db(lambda session: create_follow_up_task(session, task_title, sms_thread_id=selected_thread_id, assignee_ref=task_assignee, due_date=due_date))
                st.success('Platform follow-up task queued.')
                st.json(result)
                st.rerun()

        with action_tabs[1]:
            st.markdown('##### Candidate matching and platform approval')
            if st.button('Build/reload candidates', key=f'cands_{selected_thread_id}'):
                result = _run_db(lambda session: build_candidates_for_sms_thread(session, selected_thread_id))
                st.success('Candidates built.')
                st.json(result)
                st.rerun()
            candidates = detail.get('candidates') or []
            if not candidates:
                st.info('No candidates loaded yet. Build candidates first, or enter a contact ref manually.')
            else:
                for candidate in candidates:
                    with st.container(border=True):
                        st.write(f"**{candidate.get('display_label', '')}**")
                        st.caption(f"{candidate.get('contact_ref', '')} · score {candidate.get('score', '')}")
                        st.write(candidate.get('reasoning') or '')
            options = [''] + _candidate_ref_options(detail)
            chosen_ref = st.selectbox('Chosen contact ref', options=options, key=f'chosen_ref_select_{selected_thread_id}')
            manual_ref = st.text_input('Or type contact ref', value=chosen_ref, key=f'chosen_ref_manual_{selected_thread_id}')
            approval_notes = st.text_area('Approval notes', key=f'approval_notes_{selected_thread_id}')
            if st.button('Approve thread in platform', key=f'approve_{selected_thread_id}'):
                result = _run_db(lambda session: approve_sms_thread(session, selected_thread_id, manual_ref, decided_by, approval_notes))
                st.success('Thread approved in platform.')
                st.json(result)
                st.rerun()

            st.markdown('##### Routing preference')
            route_mode = st.selectbox('Route mode', ['manual', 'auto', 'favorite'], key=f'route_mode_{selected_thread_id}')
            route_default = st.text_input('Default contact ref', value=manual_ref, key=f'route_default_{selected_thread_id}')
            route_notes = st.text_area('Routing notes', key=f'route_notes_{selected_thread_id}')
            if st.button('Save routing preference', key=f'route_{selected_thread_id}'):
                result = _run_db(lambda session: save_routing_preference(session, detail.get('external_phone') or '', route_mode, route_default, [], route_notes))
                st.success('Routing preference saved.')
                st.json(result)
                st.rerun()

        with action_tabs[2]:
            st.markdown('##### Guarded LACRM apply')
            st.caption('Dry-run is the default and recommended mode. Live apply remains blocked unless all Step 6 guards are intentionally enabled.')
            contact_id = st.text_input('LACRM ContactId', value='', key=f'lacrm_contact_{selected_thread_id}')
            chosen_contact_ref = st.text_input('Chosen contact ref', value=f'lacrm_contact:{contact_id}' if contact_id else '', key=f'lacrm_ref_{selected_thread_id}')
            include_note = st.checkbox('Include LACRM note', value=True, key=f'include_note_{selected_thread_id}')
            include_task = st.checkbox('Include LACRM task', value=False, key=f'include_task_{selected_thread_id}')
            task_title_apply = st.text_input('LACRM task title', value=f"Follow up SMS from {detail.get('external_phone') or ''}", key=f'lacrm_task_title_{selected_thread_id}')
            operator_note = st.text_area('Operator note for LACRM payload', key=f'lacrm_operator_note_{selected_thread_id}')
            idempotency_key = st.text_input('Optional idempotency key', value='', key=f'idempotency_{selected_thread_id}')
            dry_run = st.checkbox('Dry run', value=True, key=f'dry_run_{selected_thread_id}')
            confirm_live = st.checkbox('I explicitly confirm live LACRM write if dry-run is off', value=False, key=f'confirm_live_{selected_thread_id}')
            payload = {
                'chosen_contact_ref': chosen_contact_ref,
                'contact_id': contact_id,
                'include_note': include_note,
                'include_task': include_task,
                'task_title': task_title_apply,
                'operator_note': operator_note,
                'decided_by': decided_by,
                'dry_run': dry_run,
                'confirm_live_write': confirm_live,
                'idempotency_key': idempotency_key,
            }
            preview_col, apply_col = st.columns(2)
            with preview_col:
                if st.button('Preview LACRM payload', key=f'preview_lacrm_{selected_thread_id}'):
                    preview_payload = {k: v for k, v in payload.items() if k not in {'dry_run', 'confirm_live_write', 'decided_by'}}
                    result = _run_db(lambda session: build_sms_thread_lacrm_apply_plan(session, selected_thread_id, **preview_payload))
                    st.json(result)
            with apply_col:
                if st.button('Apply guarded LACRM action', key=f'apply_lacrm_{selected_thread_id}'):
                    result = _run_db(lambda session: apply_sms_thread_to_lacrm(session, selected_thread_id, **payload))
                    if dry_run:
                        st.success('Dry-run apply recorded locally.')
                    else:
                        st.warning('Live apply attempted; review result carefully.')
                    st.json(result)
                    st.rerun()

        with action_tabs[3]:
            st.markdown('##### Thread detail')
            st.json(detail)
            st.markdown('##### Recent review actions')
            actions = _run_db(lambda session: list_review_actions(session, sms_thread_id=selected_thread_id, limit=25))
            st.json(actions)

st.subheader('Latest review actions')
latest_actions = _run_db(lambda session: list_review_actions(session, limit=10))
st.json(latest_actions)
