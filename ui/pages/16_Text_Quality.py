from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from sqlmodel import Session

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.database import create_db_and_tables, engine
from app.services.bootstrap import seed_defaults
from app.services.front_desk import (
    clean_display_text,
    list_text_quality_samples,
    text_quality_summary,
)

st.set_page_config(page_title='Text Quality', layout='wide')

create_db_and_tables()
with Session(engine) as _session:
    seed_defaults(_session)


def _run_db(fn):
    with Session(engine) as session:
        return fn(session)


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _sample_rows(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            'kind': row.get('kind'),
            'field': row.get('field'),
            'record_id': row.get('record_id'),
            'thread_id': row.get('sms_thread_id'),
            'phone': row.get('external_phone'),
            'day': row.get('local_day'),
            'changed': row.get('changed'),
            'raw_preview': row.get('raw_preview'),
            'display_preview': row.get('display_preview'),
        }
        for row in samples
    ]


st.title('Text Quality Workbench')
st.caption('Display-only mojibake detection and cleanup preview for bridge-origin SMS text. This page does not mutate raw RingCentral, bridge, or platform records.')

st.info('Raw SMS records remain unchanged. Operator screens should use the display previews when text contains legacy mojibake such as `donât`, `Iâm`, or malformed emoji byte sequences.')

summary = _run_db(lambda session: text_quality_summary(session, sample_limit=10))

metric_cols = st.columns(6)
metric_cols[0].metric('SMS Threads', summary.get('sms_threads_total', 0))
metric_cols[1].metric('Thread Issues', summary.get('sms_threads_with_encoding_issues', 0))
metric_cols[2].metric('SMS Messages', summary.get('sms_messages_total', 0))
metric_cols[3].metric('Message Issues', summary.get('sms_messages_with_encoding_issues', 0))
metric_cols[4].metric('Safe Mode', summary.get('safe_mode', 'display_only'))
issue_rate = 0.0
if _safe_int(summary.get('sms_messages_total')):
    issue_rate = round(_safe_int(summary.get('sms_messages_with_encoding_issues')) / _safe_int(summary.get('sms_messages_total')) * 100, 1)
metric_cols[5].metric('Message Issue Rate', f'{issue_rate}%')

if _safe_int(summary.get('sms_messages_with_encoding_issues')) or _safe_int(summary.get('sms_threads_with_encoding_issues')):
    st.warning('Some bridge-origin text needs display cleanup. This is expected for older RingCentral/bridge data and is handled without changing raw records.')
else:
    st.success('No display encoding issues were detected in current SMS rows.')

st.subheader('Issue distribution')
left, right = st.columns(2)
with left:
    st.write('Threads with issues by day')
    by_day = summary.get('issue_threads_by_day') or {}
    if by_day:
        st.dataframe(pd.DataFrame([{'day': day, 'issue_threads': count} for day, count in by_day.items()]), use_container_width=True, hide_index=True)
    else:
        st.caption('No day-level issues detected.')
with right:
    st.write('Top issue phones')
    phones = summary.get('top_issue_phones') or []
    if phones:
        st.dataframe(pd.DataFrame(phones), use_container_width=True, hide_index=True)
    else:
        st.caption('No phone-level issues detected.')

st.subheader('Cleanup preview')
kind = st.selectbox('Sample kind', ['all', 'sms_messages', 'sms_threads'], index=0)
only_issues = st.checkbox('Only rows with display issues', value=True)
limit = st.slider('Sample limit', min_value=5, max_value=100, value=25, step=5)
samples_payload = _run_db(lambda session: list_text_quality_samples(session, kind=kind, only_issues=only_issues, limit=limit, offset=0))
samples = samples_payload.get('samples') or []

if samples:
    st.dataframe(_sample_rows(samples), use_container_width=True, hide_index=True)
    selected_index = st.number_input('Inspect sample row number', min_value=1, max_value=len(samples), value=1, step=1) - 1
    selected = samples[int(selected_index)]
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown('**Raw stored text**')
        st.text_area('Raw preview', selected.get('raw_preview') or '', height=180, disabled=True, label_visibility='collapsed')
    with col_b:
        st.markdown('**Display-cleaned text**')
        st.text_area('Display preview', selected.get('display_preview') or '', height=180, disabled=True, label_visibility='collapsed')
else:
    st.info('No samples match the current filters.')

with st.expander('Manual cleanup preview', expanded=False):
    manual = st.text_area('Paste text to preview display cleanup', value='This Is what Iâm seeing in work order.', height=120)
    st.write('Display cleaned:')
    st.code(clean_display_text(manual))

with st.expander('Raw text quality JSON', expanded=False):
    snapshot = {'summary': summary, 'samples': samples_payload}
    st.json(snapshot)
    st.download_button(
        'Download text quality JSON',
        data=json.dumps(snapshot, default=str, indent=2),
        file_name='phase19_text_quality.json',
        mime='application/json',
    )

st.caption('Step 13 is display-only. It adds diagnostics and preview cleanup; it does not rewrite SMS bodies, transcripts, raw payloads, or CRM apply audit rows.')
