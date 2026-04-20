from __future__ import annotations

from datetime import datetime, timezone
import json
import sys
from pathlib import Path
from typing import Any

import requests
import streamlit as st
from sqlmodel import Session

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.database import create_db_and_tables, engine
from app.services.bootstrap import seed_defaults
from app.services.front_desk import (
    bridge_review_summary,
    clean_display_text,
    crm_apply_action_export,
    lacrm_apply_readiness,
    lacrm_apply_status,
    lacrm_live_apply_readiness,
    list_sms_threads,
)

st.set_page_config(page_title='Integration Health', layout='wide')

FASTAPI_URL = 'http://127.0.0.1:8010'
BRIDGE_URL = 'http://127.0.0.1:8000'
STREAMLIT_URL = 'http://127.0.0.1:8501'


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


def _endpoint_health(url: str, label: str) -> dict[str, Any]:
    """Read-only health probe used by the Step 12 dashboard."""
    started = datetime.now(timezone.utc)
    try:
        response = requests.get(url, timeout=2.5)
        elapsed_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        text = response.text[:500]
        ok = 200 <= response.status_code < 300
        return {
            'label': label,
            'url': url,
            'ok': ok,
            'status_code': response.status_code,
            'elapsed_ms': elapsed_ms,
            'preview': text,
            'error': '',
        }
    except Exception as exc:  # pragma: no cover - UI fallback path
        elapsed_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        return {
            'label': label,
            'url': url,
            'ok': False,
            'status_code': None,
            'elapsed_ms': elapsed_ms,
            'preview': '',
            'error': str(exc),
        }


def _bool_word(value: Any) -> str:
    return 'yes' if bool(value) else 'no'


def _status_pill(label: str, ok: bool) -> None:
    if ok:
        st.success(f'{label}: OK')
    else:
        st.error(f'{label}: CHECK')


def _is_synthetic_apply_action(action: dict[str, Any]) -> bool:
    payload = action.get('payload') if isinstance(action.get('payload'), dict) else {}
    haystack = ' '.join([
        str(action.get('target_contact_ref') or ''),
        str(action.get('payload_json') or ''),
        str(action.get('idempotency_key') or payload.get('idempotency_key') or ''),
        str(payload.get('parameters') or ''),
        str(action.get('error') or payload.get('error') or ''),
    ]).lower()
    return any(marker in haystack for marker in (
        'phase19-step',
        'step5',
        'step6',
        'step8',
        'step9',
        'step10',
        'step11',
        'smoke',
        'synthetic',
        'audit-test',
        'shell-test',
    ))


st.title('Integration Health')
st.caption('Read-only control-center for the current Phase 19 bridge → platform integration. This page does not call live LACRM write endpoints and does not change bridge state.')

st.info(
    'Correct local app map: '
    '`8501 = Streamlit dashboard`, '
    '`8010 = FastAPI backend/API`, '
    '`8000 = original KPS Bridge / Data Hub UI`.'
)

summary = _run_db(bridge_review_summary)
lacrm_status = _run_db(lacrm_apply_status)
lacrm_readiness = _run_db(lacrm_apply_readiness)
live_readiness = _run_db(lacrm_live_apply_readiness)
threads_payload = _run_db(lambda session: list_sms_threads(session, limit=10, offset=0))
apply_export = _run_db(lambda session: crm_apply_action_export(session, limit=250))

status_counts = lacrm_status.get('status_counts') or {}
applied_count = _safe_int(status_counts.get('applied'))
dry_run_count = _safe_int(status_counts.get('dry_run'))
blocked_count = _safe_int(status_counts.get('blocked'))
queued_count = _safe_int(status_counts.get('queued'))

live_enabled = bool(lacrm_status.get('live_write_enabled'))
live_armed = bool(lacrm_status.get('live_write_armed'))
live_ready = bool(live_readiness.get('ready_for_live_apply'))

fastapi_health = _endpoint_health(f'{FASTAPI_URL}/health', 'FastAPI backend')
bridge_health = _endpoint_health(f'{BRIDGE_URL}/health', 'KPS Bridge')
streamlit_health = {
    'label': 'Streamlit dashboard',
    'url': STREAMLIT_URL,
    'ok': True,
    'status_code': 200,
    'elapsed_ms': 0,
    'preview': 'current Streamlit process',
    'error': '',
}

metric_cols = st.columns(8)
metric_cols[0].metric('Platform SMS Threads', summary.get('sms_threads_total', 0))
metric_cols[1].metric('Platform SMS Messages', summary.get('sms_messages_total', 0))
metric_cols[2].metric('Pending Review', summary.get('pending_sms_threads_total', 0))
metric_cols[3].metric('Dry-run Applies', dry_run_count)
metric_cols[4].metric('Blocked Applies', blocked_count)
metric_cols[5].metric('Queued Tasks', queued_count)
metric_cols[6].metric('Applied Live', applied_count)
metric_cols[7].metric('Live Ready', _bool_word(live_ready))

st.subheader('System reachability')
health_cols = st.columns(3)
with health_cols[0]:
    _status_pill('FastAPI 8010', bool(fastapi_health.get('ok')))
    st.caption(f"{fastapi_health.get('status_code')} · {fastapi_health.get('elapsed_ms')} ms")
with health_cols[1]:
    _status_pill('Bridge 8000', bool(bridge_health.get('ok')))
    st.caption(f"{bridge_health.get('status_code')} · {bridge_health.get('elapsed_ms')} ms")
with health_cols[2]:
    _status_pill('Streamlit 8501', bool(streamlit_health.get('ok')))
    st.caption('current page process')

st.subheader('LACRM safety state')
if not live_enabled and not live_armed and not live_ready and applied_count == 0:
    st.success('Live LACRM writes are OFF, unarmed, not ready, and no live-applied actions are recorded.')
elif live_ready:
    st.error('Live LACRM readiness is TRUE. Confirm this is intentional before doing any live CRM work.')
else:
    st.warning('Live LACRM writes are not fully ready, but one or more safety flags differ from the safe default.')

safety_cols = st.columns(6)
safety_cols[0].metric('API key configured', _bool_word(lacrm_status.get('lacrm_api_key_configured')))
safety_cols[1].metric('Live enabled', _bool_word(live_enabled))
safety_cols[2].metric('Live armed', _bool_word(live_armed))
safety_cols[3].metric('Live ready', _bool_word(live_ready))
safety_cols[4].metric('Default mode', lacrm_status.get('default_mode') or lacrm_readiness.get('safe_default_mode') or 'dry_run')
safety_cols[5].metric('Applied count', applied_count)

blockers = live_readiness.get('blockers') or lacrm_readiness.get('blockers') or []
if blockers:
    with st.expander('Current live-apply blockers', expanded=True):
        for blocker in blockers:
            st.write(f'- {clean_display_text(str(blocker))}')

st.subheader('Readiness checklist')
checks = [
    ('Bridge health endpoint reachable', bool(bridge_health.get('ok'))),
    ('FastAPI health endpoint reachable', bool(fastapi_health.get('ok'))),
    ('Platform has bridge-origin SMS data', _safe_int(summary.get('sms_messages_total')) > 0),
    ('Live LACRM writes disabled', not live_enabled),
    ('Live LACRM writes unarmed', not live_armed),
    ('Live apply readiness false', not live_ready),
    ('No live-applied action rows', applied_count == 0),
]
for label, ok in checks:
    if ok:
        st.write(f'✅ {label}')
    else:
        st.write(f'⚠️ {label}')

st.subheader('Latest platform SMS threads')
latest_threads = threads_payload.get('threads') or []
if latest_threads:
    st.dataframe(
        [
            {
                'id': thread.get('id'),
                'phone': thread.get('external_phone'),
                'day': thread.get('local_day'),
                'status': thread.get('status'),
                'message_count': thread.get('message_count'),
                'latest_message_at': thread.get('latest_message_at'),
                'summary': clean_display_text(thread.get('display_summary') or thread.get('summary') or ''),
            }
            for thread in latest_threads
        ],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info('No SMS threads are available in the platform database yet.')

st.subheader('Apply audit summary')
raw_actions = apply_export.get('actions') or []
real_actions = [action for action in raw_actions if not _is_synthetic_apply_action(action)]
action_cols = st.columns(4)
action_cols[0].metric('Audit rows', len(raw_actions))
action_cols[1].metric('Non-synthetic rows', len(real_actions))
action_cols[2].metric('Synthetic/test rows hidden in normal views', len(raw_actions) - len(real_actions))
action_cols[3].metric('Blocked rows', blocked_count)

with st.expander('Raw integration health snapshot', expanded=False):
    snapshot = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'urls': {
            'streamlit': STREAMLIT_URL,
            'fastapi': FASTAPI_URL,
            'bridge': BRIDGE_URL,
        },
        'fastapi_health': fastapi_health,
        'bridge_health': bridge_health,
        'bridge_review_summary': summary,
        'lacrm_status': lacrm_status,
        'lacrm_readiness': lacrm_readiness,
        'lacrm_live_readiness': live_readiness,
        'readiness_checks': [{'label': label, 'ok': ok} for label, ok in checks],
    }
    st.json(snapshot)
    st.download_button(
        'Download integration health JSON',
        data=json.dumps(snapshot, default=str, indent=2),
        file_name='phase19_integration_health.json',
        mime='application/json',
    )

st.caption('Step 12 is read-only. Use Bridge Review for platform review actions and the original KPS Bridge/Data Hub on port 8000 for existing live bridge operations.')
