from __future__ import annotations

from datetime import date, datetime
import hashlib
import os
from typing import Any

from sqlmodel import Session, desc, select

from app.connectors.lacrm.client import LACRMAPIError, get_lacrm_client
from app.models.communication_tables import (
    CRMApplyAction,
    CommunicationEvent,
    CommunicationTaskLink,
    ContactMatchCandidate,
    OperatorDecision,
    RoutingPreference,
    SMSThread,
    SMSMessage,
)
from app.models.connector_tables import ApplyEvent, ApprovalDecision, ExternalIdentityMap, MatchCandidate, NormalizedSourceRecord
from app.models.tables import Account, ApprovedAgent, Property
from app.utils.matching import similarity
from app.utils.serialization import dumps, loads



_MOJIBAKE_MARKERS = ('â', 'ð', 'ï', 'Ã', '\ufffd', '\x80', '\x81', '\x82', '\x83', '\x84', '\x85', '\x86', '\x87', '\x88', '\x89', '\x8a', '\x8b', '\x8c', '\x8d', '\x8e', '\x8f', '\x90', '\x91', '\x92', '\x93', '\x94', '\x95', '\x96', '\x97', '\x98', '\x99')


def clean_display_text(value: str | None) -> str:
    """Best-effort cleanup for legacy mojibake without mutating stored data.

    RingCentral and older bridge snapshots can contain text that was decoded as
    Latin-1/Windows-1252 after being encoded as UTF-8, producing strings like
    ``donât`` or ``ð``. The platform keeps raw data unchanged and exposes
    display-only repaired text for operator screens and audit reports.
    """
    if not value:
        return ''
    text = str(value)
    if not any(marker in text for marker in _MOJIBAKE_MARKERS):
        return text

    candidates: list[str] = []
    for encoding in ('latin1', 'cp1252'):
        try:
            candidates.append(text.encode(encoding).decode('utf-8'))
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass

    replacements = {
        'â': '’',
        'â': '‘',
        'â': '“',
        'â': '”',
        'â¦': '…',
        'â': '—',
        'â': '–',
        'â¢': '™',
        'Â ': ' ',
        'Â': '',
        'ï¸': '',
        'ð': '👍',
        'ð': '😁',
        'ð': '😅',
        'ð': '😝',
        'ð¬': '😬',
        'ð¤¦ââï¸': '🤦‍♀️',
        'ð¤¦ââï¸': '🤦‍♂️',
    }
    repaired = text
    for bad, good in replacements.items():
        repaired = repaired.replace(bad, good)
    candidates.append(repaired)

    def _score(candidate: str) -> int:
        marker_count = sum(candidate.count(marker) for marker in _MOJIBAKE_MARKERS)
        replacement_count = candidate.count('\ufffd')
        return marker_count * 10 + replacement_count * 20

    return min(candidates, key=_score) if candidates else text


def text_has_display_encoding_issue(value: str | None) -> bool:
    """Return True when display cleanup would materially change text."""
    if not value:
        return False
    text = str(value)
    return clean_display_text(text) != text or any(marker in text for marker in _MOJIBAKE_MARKERS)


def _preview_text(value: str | None, *, limit: int = 280) -> str:
    text = str(value or '')
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + '…'


def _text_quality_sample(
    *,
    kind: str,
    field: str,
    record_id: int | None,
    sms_thread_id: int | None,
    external_phone: str = '',
    local_day: str = '',
    occurred_at: str = '',
    source_text: str = '',
) -> dict[str, Any]:
    display = clean_display_text(source_text)
    return {
        'kind': kind,
        'field': field,
        'record_id': record_id,
        'sms_thread_id': sms_thread_id,
        'external_phone': external_phone,
        'local_day': local_day,
        'occurred_at': occurred_at,
        'has_issue': text_has_display_encoding_issue(source_text),
        'raw_preview': _preview_text(source_text),
        'display_preview': _preview_text(display),
        'changed': display != str(source_text or ''),
    }


def _date_from_string(value: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _loads_dict(value: str) -> dict[str, Any]:
    parsed = loads(value, {})
    return parsed if isinstance(parsed, dict) else {}


def _operator_decision_payload(row: OperatorDecision) -> dict[str, Any]:
    return row.model_dump()


def _task_link_payload(row: CommunicationTaskLink) -> dict[str, Any]:
    data = row.model_dump()
    data['kind'] = 'follow_up_task'
    return data


def _routing_preference_payload(row: RoutingPreference | None) -> dict[str, Any] | None:
    if not row:
        return None
    data = row.model_dump()
    data['favorite_refs'] = loads(row.favorite_refs_json, [])
    data.pop('favorite_refs_json', None)
    return data


def _sms_message_payload(row: SMSMessage) -> dict[str, Any]:
    data = row.model_dump()
    data['display_body'] = clean_display_text(row.body)
    data['text_quality'] = {
        'body_has_encoding_issue': text_has_display_encoding_issue(row.body),
        'body_changed_for_display': clean_display_text(row.body) != (row.body or ''),
    }
    data['raw'] = _loads_dict(row.raw_json)
    data.pop('raw_json', None)
    return data


def _sms_thread_payload(
    session: Session,
    row: SMSThread,
    *,
    include_messages: bool = False,
    include_candidates: bool = False,
    include_tasks: bool = False,
) -> dict[str, Any]:
    data = row.model_dump()
    raw = _loads_dict(row.raw_json)
    thread_seed = raw.get('thread_seed') if isinstance(raw.get('thread_seed'), dict) else raw
    bridge_context = thread_seed.get('bridge_context', {}) if isinstance(thread_seed, dict) else {}
    data['display_summary'] = clean_display_text(row.summary)
    data['display_transcript'] = clean_display_text(row.transcript)
    data['text_quality'] = {
        'summary_has_encoding_issue': text_has_display_encoding_issue(row.summary),
        'transcript_has_encoding_issue': text_has_display_encoding_issue(row.transcript),
        'summary_changed_for_display': clean_display_text(row.summary) != (row.summary or ''),
        'transcript_changed_for_display': clean_display_text(row.transcript) != (row.transcript or ''),
    }
    data['message_count'] = len(list(session.exec(select(SMSMessage).where(SMSMessage.sms_thread_id == row.id)).all()))
    data['bridge_context'] = bridge_context if isinstance(bridge_context, dict) else {}
    data['source'] = data['bridge_context'].get('source', '')
    data['provenance'] = {
        'normalized_record_id': row.normalized_record_id,
        'bridge_context': data['bridge_context'],
        'external_phone': row.external_phone,
        'internal_phone': row.internal_phone,
        'local_day': row.local_day.isoformat() if row.local_day else '',
    }
    routing = session.exec(select(RoutingPreference).where(RoutingPreference.phone == row.external_phone)).first()
    data['routing_preference'] = _routing_preference_payload(routing)
    decisions = list(session.exec(
        select(OperatorDecision)
        .where(OperatorDecision.sms_thread_id == row.id)
        .order_by(desc(OperatorDecision.created_at))
    ).all())
    data['operator_decisions'] = [_operator_decision_payload(decision) for decision in decisions]
    if include_messages:
        messages = list(session.exec(
            select(SMSMessage)
            .where(SMSMessage.sms_thread_id == row.id)
            .order_by(SMSMessage.occurred_at, SMSMessage.id)
        ).all())
        data['messages'] = [_sms_message_payload(message) for message in messages]
    if include_candidates:
        candidates = list(session.exec(
            select(ContactMatchCandidate)
            .where(ContactMatchCandidate.sms_thread_id == row.id)
            .order_by(desc(ContactMatchCandidate.score))
        ).all())
        data['candidates'] = [candidate.model_dump() for candidate in candidates]
    if include_tasks:
        tasks = list(session.exec(
            select(CommunicationTaskLink)
            .where(CommunicationTaskLink.sms_thread_id == row.id)
            .order_by(desc(CommunicationTaskLink.created_at))
        ).all())
        data['tasks'] = [task.model_dump() for task in tasks]
    return data


def list_sms_threads(
    session: Session,
    *,
    status: str = '',
    external_phone: str = '',
    local_day: str = '',
    source: str = '',
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    limit = max(1, min(int(limit or 50), 250))
    offset = max(0, int(offset or 0))
    stmt = select(SMSThread)
    if status:
        stmt = stmt.where(SMSThread.status == status)
    if external_phone:
        stmt = stmt.where(SMSThread.external_phone == external_phone)
    parsed_day = _date_from_string(local_day)
    if parsed_day:
        stmt = stmt.where(SMSThread.local_day == parsed_day)
    rows = list(session.exec(stmt.order_by(desc(SMSThread.latest_message_at)).offset(offset).limit(limit)).all())
    payloads = [_sms_thread_payload(session, row) for row in rows]
    if source:
        payloads = [row for row in payloads if row.get('source') == source]
    return {'limit': limit, 'offset': offset, 'count': len(payloads), 'threads': payloads}


def get_sms_thread_detail(session: Session, sms_thread_id: int) -> dict[str, Any]:
    row = session.get(SMSThread, sms_thread_id)
    if not row:
        raise ValueError('SMS thread not found')
    return _sms_thread_payload(session, row, include_messages=True, include_candidates=True, include_tasks=True)


def bridge_review_summary(session: Session) -> dict[str, Any]:
    threads = list(session.exec(select(SMSThread)).all())
    messages = list(session.exec(select(SMSMessage)).all())
    by_status: dict[str, int] = {}
    by_day: dict[str, int] = {}
    by_source: dict[str, int] = {}
    for thread in threads:
        by_status[thread.status] = by_status.get(thread.status, 0) + 1
        day = thread.local_day.isoformat() if thread.local_day else ''
        by_day[day] = by_day.get(day, 0) + 1
        raw = _loads_dict(thread.raw_json)
        seed = raw.get('thread_seed') if isinstance(raw.get('thread_seed'), dict) else raw
        context = seed.get('bridge_context', {}) if isinstance(seed, dict) else {}
        source = context.get('source', 'unknown') if isinstance(context, dict) else 'unknown'
        by_source[source] = by_source.get(source, 0) + 1
    latest = list(session.exec(select(SMSThread).order_by(desc(SMSThread.latest_message_at)).limit(10)).all())
    return {
        'sms_threads_total': len(threads),
        'sms_messages_total': len(messages),
        'threads_by_status': by_status,
        'threads_by_day': dict(sorted(by_day.items(), reverse=True)),
        'threads_by_source': by_source,
        'latest_threads': [_sms_thread_payload(session, row) for row in latest],
    }



def list_text_quality_samples(
    session: Session,
    *,
    kind: str = 'all',
    only_issues: bool = True,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """List display-cleanup samples without mutating stored RingCentral/bridge text."""
    normalized_kind = (kind or 'all').strip().lower()
    limit = max(1, min(int(limit or 50), 250))
    offset = max(0, int(offset or 0))
    samples: list[dict[str, Any]] = []

    if normalized_kind in {'all', 'thread', 'threads', 'sms_thread', 'sms_threads'}:
        threads = list(session.exec(select(SMSThread).order_by(desc(SMSThread.latest_message_at))).all())
        for thread in threads:
            local_day = thread.local_day.isoformat() if thread.local_day else ''
            for field, value in (('summary', thread.summary), ('transcript', thread.transcript)):
                sample = _text_quality_sample(
                    kind='sms_thread',
                    field=field,
                    record_id=thread.id,
                    sms_thread_id=thread.id,
                    external_phone=thread.external_phone,
                    local_day=local_day,
                    occurred_at=thread.latest_message_at.isoformat() if thread.latest_message_at else '',
                    source_text=value or '',
                )
                if not only_issues or sample['has_issue']:
                    samples.append(sample)

    if normalized_kind in {'all', 'message', 'messages', 'sms_message', 'sms_messages'}:
        messages = list(session.exec(select(SMSMessage).order_by(desc(SMSMessage.occurred_at), desc(SMSMessage.id))).all())
        thread_ids = {message.sms_thread_id for message in messages if message.sms_thread_id}
        threads_by_id = {row.id: row for row in session.exec(select(SMSThread).where(SMSThread.id.in_(thread_ids))).all()} if thread_ids else {}
        for message in messages:
            thread = threads_by_id.get(message.sms_thread_id)
            sample = _text_quality_sample(
                kind='sms_message',
                field='body',
                record_id=message.id,
                sms_thread_id=message.sms_thread_id,
                external_phone=thread.external_phone if thread else '',
                local_day=thread.local_day.isoformat() if thread and thread.local_day else '',
                occurred_at=message.occurred_at.isoformat() if message.occurred_at else '',
                source_text=message.body or '',
            )
            if not only_issues or sample['has_issue']:
                samples.append(sample)

    total = len(samples)
    page = samples[offset: offset + limit]
    return {
        'kind': normalized_kind,
        'only_issues': bool(only_issues),
        'limit': limit,
        'offset': offset,
        'total': total,
        'count': len(page),
        'samples': page,
    }


def text_quality_summary(session: Session, *, sample_limit: int = 10) -> dict[str, Any]:
    """Return display-text quality counts for bridge-origin SMS review screens."""
    threads = list(session.exec(select(SMSThread)).all())
    messages = list(session.exec(select(SMSMessage)).all())
    thread_issue_count = 0
    message_issue_count = 0
    by_day: dict[str, int] = {}
    by_phone: dict[str, int] = {}
    for thread in threads:
        issue = text_has_display_encoding_issue(thread.summary) or text_has_display_encoding_issue(thread.transcript)
        if issue:
            thread_issue_count += 1
            day = thread.local_day.isoformat() if thread.local_day else ''
            by_day[day] = by_day.get(day, 0) + 1
            by_phone[thread.external_phone] = by_phone.get(thread.external_phone, 0) + 1
    for message in messages:
        if text_has_display_encoding_issue(message.body):
            message_issue_count += 1
    sample_payload = list_text_quality_samples(session, kind='all', only_issues=True, limit=sample_limit, offset=0)
    return {
        'safe_mode': 'display_only_no_raw_mutation',
        'sms_threads_total': len(threads),
        'sms_threads_with_encoding_issues': thread_issue_count,
        'sms_messages_total': len(messages),
        'sms_messages_with_encoding_issues': message_issue_count,
        'issue_threads_by_day': dict(sorted(by_day.items(), reverse=True)),
        'top_issue_phones': [
            {'external_phone': phone, 'issue_count': count}
            for phone, count in sorted(by_phone.items(), key=lambda item: item[1], reverse=True)[:10]
        ],
        'sample_count': sample_payload['count'],
        'samples': sample_payload['samples'],
    }


_ALLOWED_THREAD_STATUSES = {
    'pending_review',
    'needs_follow_up',
    'waiting_on_customer',
    'waiting_on_internal',
    'approved',
    'closed',
    'ignored',
    'escalated',
}


def set_sms_thread_review_status(
    session: Session,
    sms_thread_id: int,
    *,
    status: str,
    decided_by: str = 'operator',
    notes: str = '',
) -> dict[str, Any]:
    """Update the platform-owned review status for an SMS thread and audit it.

    This intentionally does not write back to the bridge or LACRM. It is the first
    platform-side review ownership step after ingestion/parity.
    """
    normalized_status = (status or '').strip().lower()
    if normalized_status not in _ALLOWED_THREAD_STATUSES:
        raise ValueError(f"Unsupported SMS thread status: {status}")
    thread = session.get(SMSThread, sms_thread_id)
    if not thread:
        raise ValueError('SMS thread not found')
    previous_status = thread.status
    thread.status = normalized_status
    session.add(thread)
    decision = OperatorDecision(
        sms_thread_id=sms_thread_id,
        decision=f'status:{normalized_status}',
        chosen_contact_ref='',
        notes=notes,
        decided_by=decided_by or 'operator',
    )
    session.add(decision)
    session.commit()
    session.refresh(thread)
    session.refresh(decision)
    return {
        'sms_thread_id': sms_thread_id,
        'previous_status': previous_status,
        'status': thread.status,
        'operator_decision_id': decision.id,
        'decided_by': decision.decided_by,
        'notes': decision.notes,
    }


def add_sms_thread_review_note(
    session: Session,
    sms_thread_id: int,
    *,
    note: str,
    decided_by: str = 'operator',
) -> dict[str, Any]:
    thread = session.get(SMSThread, sms_thread_id)
    if not thread:
        raise ValueError('SMS thread not found')
    cleaned_note = (note or '').strip()
    if not cleaned_note:
        raise ValueError('Review note is required')
    decision = OperatorDecision(
        sms_thread_id=sms_thread_id,
        decision='note',
        chosen_contact_ref='',
        notes=cleaned_note,
        decided_by=decided_by or 'operator',
    )
    session.add(decision)
    session.commit()
    session.refresh(decision)
    return {
        'sms_thread_id': sms_thread_id,
        'operator_decision_id': decision.id,
        'decision': decision.decision,
        'decided_by': decision.decided_by,
        'notes': decision.notes,
        'created_at': decision.created_at.isoformat(),
    }


def list_review_actions(
    session: Session,
    *,
    sms_thread_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    limit = max(1, min(int(limit or 50), 250))
    offset = max(0, int(offset or 0))
    stmt = select(OperatorDecision).order_by(desc(OperatorDecision.created_at)).offset(offset).limit(limit)
    if sms_thread_id:
        stmt = select(OperatorDecision).where(OperatorDecision.sms_thread_id == sms_thread_id).order_by(desc(OperatorDecision.created_at)).offset(offset).limit(limit)
    rows = list(session.exec(stmt).all())
    thread_ids = {row.sms_thread_id for row in rows if row.sms_thread_id}
    threads = {row.id: row for row in session.exec(select(SMSThread).where(SMSThread.id.in_(thread_ids))).all()} if thread_ids else {}
    actions: list[dict[str, Any]] = []
    for row in rows:
        payload = row.model_dump()
        thread = threads.get(row.sms_thread_id or 0)
        if thread:
            payload['sms_thread'] = {
                'id': thread.id,
                'external_phone': thread.external_phone,
                'local_day': thread.local_day.isoformat() if thread.local_day else '',
                'status': thread.status,
                'display_summary': clean_display_text(thread.summary),
            }
        actions.append(payload)
    return {'limit': limit, 'offset': offset, 'count': len(actions), 'actions': actions}

def compare_bridge_sms_batches(session: Session, bridge_batches: list[dict[str, Any]]) -> dict[str, Any]:
    platform_threads = list(session.exec(select(SMSThread)).all())
    platform_keys = {(row.external_phone, row.local_day.isoformat() if row.local_day else '') for row in platform_threads}
    matched: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for batch in bridge_batches:
        phone = str(batch.get('external_phone') or '')
        batch_day = str(batch.get('batch_date') or '')[:10]
        item = {
            'bridge_batch_id': batch.get('id', ''),
            'external_phone': phone,
            'batch_date': batch_day,
            'latest_message_at': batch.get('latest_message_at', ''),
            'status': batch.get('status', ''),
        }
        if (phone, batch_day) in platform_keys:
            matched.append(item)
        else:
            missing.append(item)
    return {
        'bridge_batches_total': len(bridge_batches),
        'platform_sms_threads_total': len(platform_threads),
        'matched_count': len(matched),
        'missing_count': len(missing),
        'matched_preview': matched[:25],
        'missing_preview': missing[:25],
    }


def review_action_summary(session: Session) -> dict[str, Any]:
    decisions = list(session.exec(select(OperatorDecision).order_by(desc(OperatorDecision.created_at)).limit(50)).all())
    tasks = list(session.exec(select(CommunicationTaskLink).order_by(desc(CommunicationTaskLink.created_at)).limit(50)).all())
    routing = list(session.exec(select(RoutingPreference).order_by(desc(RoutingPreference.updated_at)).limit(50)).all())
    apply_actions = list(session.exec(select(CRMApplyAction).order_by(desc(CRMApplyAction.created_at)).limit(50)).all())
    approved_threads = list(session.exec(select(SMSThread).where(SMSThread.status == 'approved')).all())
    pending_threads = list(session.exec(select(SMSThread).where(SMSThread.status == 'pending_review')).all())
    task_status_counts: dict[str, int] = {}
    apply_status_counts: dict[str, int] = {}
    for task in tasks:
        task_status_counts[task.status] = task_status_counts.get(task.status, 0) + 1
    for action in apply_actions:
        apply_status_counts[action.status] = apply_status_counts.get(action.status, 0) + 1
    return {
        'operator_decisions_total': len(list(session.exec(select(OperatorDecision)).all())),
        'approved_sms_threads_total': len(approved_threads),
        'pending_sms_threads_total': len(pending_threads),
        'task_links_total': len(list(session.exec(select(CommunicationTaskLink)).all())),
        'task_status_counts': task_status_counts,
        'routing_preferences_total': len(list(session.exec(select(RoutingPreference)).all())),
        'crm_apply_actions_total': len(list(session.exec(select(CRMApplyAction)).all())),
        'crm_apply_status_counts': apply_status_counts,
        'latest_decisions': [_operator_decision_payload(row) for row in decisions[:10]],
        'latest_tasks': [_task_link_payload(row) for row in tasks[:10]],
        'latest_routing_preferences': [_routing_preference_payload(row) for row in routing[:10]],
    }


def _truthy_env(name: str) -> bool:
    return (os.getenv(name, '') or '').strip().lower() in {'1', 'true', 'yes', 'on'}


def _live_confirmation_phrase() -> str:
    return (os.getenv('PLATFORM_LACRM_LIVE_WRITE_CONFIRMATION_PHRASE') or 'WRITE TO LACRM').strip() or 'WRITE TO LACRM'


def _lacrm_live_apply_gate_snapshot(session: Session, *, submitted_phrase: str = '') -> dict[str, Any]:
    """Return the live-write gate state without performing any CRM writes.

    Step 10 intentionally adds a second arm switch and a typed phrase gate on top
    of the Step 6 dry-run/live-write controls. The phrase is not a secret; it is
    a deliberate friction point so accidental checkbox clicks cannot write to LACRM.
    """
    status = lacrm_apply_status(session)
    status_counts = status.get('status_counts', {}) if isinstance(status.get('status_counts'), dict) else {}
    dry_run_total = int(status_counts.get('dry_run', 0) or 0)
    error_total = int(status_counts.get('error', 0) or 0)
    phrase = _live_confirmation_phrase()
    submitted = (submitted_phrase or '').strip()
    phrase_matched = submitted == phrase if submitted else False
    gates = {
        'lacrm_api_key_configured': bool(status.get('lacrm_api_key_configured')),
        'live_write_enabled': _truthy_env('PLATFORM_LACRM_LIVE_WRITE_ENABLED'),
        'live_write_armed': _truthy_env('PLATFORM_LACRM_LIVE_WRITE_ARMED'),
        'dry_run_history_present': dry_run_total > 0,
        'no_error_actions': error_total == 0,
        'confirmation_phrase_matched': phrase_matched,
    }
    blockers: list[str] = []
    if not gates['lacrm_api_key_configured']:
        blockers.append('LACRM_API_KEY is not configured in the platform environment.')
    if not gates['live_write_enabled']:
        blockers.append('PLATFORM_LACRM_LIVE_WRITE_ENABLED is not true.')
    if not gates['live_write_armed']:
        blockers.append('PLATFORM_LACRM_LIVE_WRITE_ARMED is not true.')
    if not gates['dry_run_history_present']:
        blockers.append('At least one dry-run CRM apply action must exist before any live apply attempt.')
    if not gates['no_error_actions']:
        blockers.append(f'{error_total} CRM apply action(s) are in error status.')
    if submitted and not gates['confirmation_phrase_matched']:
        blockers.append('Typed live confirmation phrase does not match the configured phrase.')
    elif not submitted:
        blockers.append('Typed live confirmation phrase is required for live apply attempts.')
    return {
        'safe_default_mode': 'dry_run',
        'ready_for_live_apply': len(blockers) == 0,
        'gates': gates,
        'blockers': blockers,
        'required_confirmation_phrase': phrase,
        'submitted_confirmation_phrase_present': bool(submitted),
        'dry_run_total': dry_run_total,
        'error_total': error_total,
        'status_counts': status_counts,
        'latest_actions': status.get('latest_actions', []),
    }


def lacrm_live_apply_readiness(session: Session, *, submitted_phrase: str = '') -> dict[str, Any]:
    """Public readiness view for the guarded live-apply cutover controls."""
    snapshot = _lacrm_live_apply_gate_snapshot(session, submitted_phrase=submitted_phrase)
    snapshot['next_steps'] = [
        'Keep dry_run=true for normal operator review.',
        'Review the Apply Audit tab before considering live writes.',
        'For a future live cutover, configure LACRM_API_KEY, PLATFORM_LACRM_LIVE_WRITE_ENABLED=true, PLATFORM_LACRM_LIVE_WRITE_ARMED=true, and type the confirmation phrase.',
    ]
    return snapshot


def _extract_lacrm_contact_id(chosen_contact_ref: str = '', contact_id: str = '') -> str:
    explicit = (contact_id or '').strip()
    if explicit:
        return explicit
    ref = (chosen_contact_ref or '').strip()
    for prefix in ('lacrm_contact:', 'lacrm:', 'contact:'):
        if ref.startswith(prefix):
            return ref.split(':', 1)[1].strip()
    return ''


def _thread_apply_note(thread: SMSThread, messages: list[SMSMessage], *, operator_note: str = '') -> str:
    lines = [
        'KPS Bridge SMS review',
        f'Phone: {thread.external_phone}',
        f'Day: {thread.local_day.isoformat() if thread.local_day else ""}',
        f'Status: {thread.status}',
        '',
        'Summary:',
        clean_display_text(thread.summary or thread.transcript or ''),
    ]
    if operator_note:
        lines.extend(['', 'Operator note:', operator_note.strip()])
    if messages:
        lines.extend(['', 'Recent messages:'])
        for msg in messages[-8:]:
            ts = msg.occurred_at.isoformat() if msg.occurred_at else ''
            lines.append(f'- [{ts}] {msg.direction}: {clean_display_text(msg.body)}')
    return '\n'.join(lines).strip()


def build_sms_thread_lacrm_apply_plan(
    session: Session,
    sms_thread_id: int,
    *,
    chosen_contact_ref: str = '',
    contact_id: str = '',
    include_note: bool = True,
    include_task: bool = False,
    task_title: str = '',
    task_due_date: date | None = None,
    operator_note: str = '',
    idempotency_key: str = '',
) -> dict[str, Any]:
    """Build a guarded LACRM apply plan without writing to LACRM."""
    thread = session.get(SMSThread, sms_thread_id)
    if not thread:
        raise ValueError('SMS thread not found')
    resolved_contact_id = _extract_lacrm_contact_id(chosen_contact_ref, contact_id)
    if not resolved_contact_id:
        raise ValueError('LACRM contact_id is required. Use contact_id or chosen_contact_ref like lacrm_contact:12345.')
    messages = list(session.exec(
        select(SMSMessage)
        .where(SMSMessage.sms_thread_id == sms_thread_id)
        .order_by(SMSMessage.occurred_at, SMSMessage.id)
    ).all())
    note_body = _thread_apply_note(thread, messages, operator_note=operator_note)
    base_key = idempotency_key or hashlib.sha256(
        f'sms_thread:{sms_thread_id}|lacrm_contact:{resolved_contact_id}|{note_body}|{task_title}|{task_due_date}'.encode('utf-8')
    ).hexdigest()
    operations: list[dict[str, Any]] = []
    if include_note:
        operations.append({
            'operation': 'create_note',
            'idempotency_key': f'{base_key}:note',
            'target_contact_ref': f'lacrm_contact:{resolved_contact_id}',
            'parameters': {'ContactId': resolved_contact_id, 'Note': note_body},
        })
    if include_task:
        title = (task_title or '').strip() or f'Follow up SMS from {thread.external_phone}'
        operations.append({
            'operation': 'create_task',
            'idempotency_key': f'{base_key}:task',
            'target_contact_ref': f'lacrm_contact:{resolved_contact_id}',
            'parameters': {
                'Name': title,
                'Description': note_body,
                'ContactId': resolved_contact_id,
                'DueDate': task_due_date.isoformat() if task_due_date else None,
            },
        })
    if not operations:
        raise ValueError('At least one LACRM apply operation is required.')
    return {
        'sms_thread_id': sms_thread_id,
        'chosen_contact_ref': chosen_contact_ref or f'lacrm_contact:{resolved_contact_id}',
        'contact_id': resolved_contact_id,
        'dry_run_default': True,
        'live_write_enabled': _truthy_env('PLATFORM_LACRM_LIVE_WRITE_ENABLED'),
        'operation_count': len(operations),
        'operations': operations,
    }


def _existing_apply_action(session: Session, idempotency_key: str, action_type: str, target_contact_ref: str) -> CRMApplyAction | None:
    rows = list(session.exec(
        select(CRMApplyAction)
        .where(CRMApplyAction.action_type == action_type)
        .where(CRMApplyAction.target_contact_ref == target_contact_ref)
        .order_by(desc(CRMApplyAction.created_at))
    ).all())
    needle = f'"idempotency_key":"{idempotency_key}"'
    needle_spaced = f'"idempotency_key": "{idempotency_key}"'
    for row in rows:
        if needle in row.payload_json or needle_spaced in row.payload_json:
            return row
    return None


def apply_sms_thread_to_lacrm(
    session: Session,
    sms_thread_id: int,
    *,
    chosen_contact_ref: str = '',
    contact_id: str = '',
    include_note: bool = True,
    include_task: bool = False,
    task_title: str = '',
    task_due_date: date | None = None,
    operator_note: str = '',
    decided_by: str = 'operator',
    dry_run: bool = True,
    confirm_live_write: bool = False,
    live_confirmation_phrase: str = '',
    idempotency_key: str = '',
) -> dict[str, Any]:
    """Queue or execute guarded LACRM actions for an SMS thread.

    Default behavior is dry-run only. Live writes require both
    PLATFORM_LACRM_LIVE_WRITE_ENABLED=true and confirm_live_write=true.
    """
    plan = build_sms_thread_lacrm_apply_plan(
        session,
        sms_thread_id,
        chosen_contact_ref=chosen_contact_ref,
        contact_id=contact_id,
        include_note=include_note,
        include_task=include_task,
        task_title=task_title,
        task_due_date=task_due_date,
        operator_note=operator_note,
        idempotency_key=idempotency_key,
    )
    live_requested = not dry_run
    live_gate = _lacrm_live_apply_gate_snapshot(session, submitted_phrase=live_confirmation_phrase)
    live_blockers = list(live_gate.get('blockers') or [])
    if live_requested and not confirm_live_write:
        live_blockers.append('confirm_live_write must be true for live apply attempts.')
    live_allowed = bool(live_requested and confirm_live_write and not live_blockers)
    client = get_lacrm_client() if live_allowed else None
    if live_allowed and client is None:
        live_blockers.append('Live LACRM write blocked because LACRM_API_KEY is not configured.')
        live_allowed = False
    live_block_reason = 'Live LACRM write blocked: ' + '; '.join(live_blockers) if live_requested and not live_allowed else ''

    decision = OperatorDecision(
        sms_thread_id=sms_thread_id,
        decision='lacrm_apply_live' if live_allowed else 'lacrm_apply_dry_run',
        chosen_contact_ref=plan['chosen_contact_ref'],
        notes=operator_note or live_block_reason,
        decided_by=decided_by or 'operator',
    )
    session.add(decision)
    session.commit()
    session.refresh(decision)

    results: list[dict[str, Any]] = []
    for op in plan['operations']:
        existing = _existing_apply_action(session, op['idempotency_key'], op['operation'], op['target_contact_ref'])
        if existing:
            results.append({
                'operation': op['operation'],
                'status': existing.status,
                'deduped': True,
                'crm_apply_action_id': existing.id,
                'idempotency_key': op['idempotency_key'],
            })
            continue
        status = 'dry_run'
        response_payload: dict[str, Any] = {}
        error = ''
        if live_requested and not live_allowed:
            status = 'blocked'
            error = live_block_reason
        elif live_allowed and client is not None:
            try:
                if op['operation'] == 'create_note':
                    response = client.call('CreateNote', op['parameters'])
                    response_payload = dict(response) if isinstance(response, dict) else {'response': response}
                elif op['operation'] == 'create_task':
                    params = op['parameters']
                    response_payload = client.create_task(
                        name=params.get('Name', ''),
                        due_date=params.get('DueDate'),
                        description=params.get('Description', ''),
                        contact_id=params.get('ContactId'),
                    )
                status = 'applied'
            except (LACRMAPIError, ValueError) as exc:
                status = 'error'
                error = str(exc)
        payload = {
            'idempotency_key': op['idempotency_key'],
            'sms_thread_id': sms_thread_id,
            'operation': op['operation'],
            'parameters': op['parameters'],
            'dry_run': dry_run,
            'confirm_live_write': confirm_live_write,
            'live_write_enabled': _truthy_env('PLATFORM_LACRM_LIVE_WRITE_ENABLED'),
            'live_write_armed': _truthy_env('PLATFORM_LACRM_LIVE_WRITE_ARMED'),
            'live_confirmation_phrase_matched': bool(live_gate.get('gates', {}).get('confirmation_phrase_matched')),
            'live_gate_blockers': live_blockers,
            'response': response_payload,
            'error': error,
        }
        action = CRMApplyAction(
            operator_decision_id=decision.id,
            action_type=op['operation'],
            target_contact_ref=op['target_contact_ref'],
            payload_json=dumps(payload),
            status=status,
        )
        session.add(action)
        session.commit()
        session.refresh(action)
        results.append({
            'operation': op['operation'],
            'status': status,
            'deduped': False,
            'crm_apply_action_id': action.id,
            'idempotency_key': op['idempotency_key'],
            'error': error,
        })
    return {
        'ok': all(item['status'] in {'dry_run', 'applied'} or item.get('deduped') for item in results),
        'mode': 'live' if live_allowed else 'dry_run' if dry_run else 'blocked',
        'sms_thread_id': sms_thread_id,
        'operator_decision_id': decision.id,
        'contact_id': plan['contact_id'],
        'chosen_contact_ref': plan['chosen_contact_ref'],
        'operation_count': len(results),
        'results': results,
        'live_block_reason': live_block_reason,
        'live_readiness': live_gate,
    }



def _crm_apply_action_payload(row: CRMApplyAction) -> dict[str, Any]:
    """Return a normalized CRM apply action with parsed payload and audit fields."""
    payload = _loads_dict(row.payload_json)
    data = row.model_dump()
    data['payload'] = payload
    data['idempotency_key'] = str(payload.get('idempotency_key') or '')
    data['sms_thread_id'] = payload.get('sms_thread_id')
    data['operation'] = str(payload.get('operation') or row.action_type)
    data['target_contact_id'] = _extract_lacrm_contact_id(row.target_contact_ref)
    data['dry_run'] = bool(payload.get('dry_run', row.status == 'dry_run'))
    data['confirm_live_write'] = bool(payload.get('confirm_live_write', False))
    data['live_write_armed'] = bool(payload.get('live_write_armed', False))
    data['live_confirmation_phrase_matched'] = bool(payload.get('live_confirmation_phrase_matched', False))
    data['live_gate_blockers'] = payload.get('live_gate_blockers', []) if isinstance(payload.get('live_gate_blockers'), list) else []
    data['live_intent'] = not bool(payload.get('dry_run', True))
    data['error'] = str(payload.get('error') or '')
    return data


def list_crm_apply_actions(
    session: Session,
    *,
    status: str = '',
    action_type: str = '',
    target_contact_ref: str = '',
    sms_thread_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """List guarded LACRM apply actions for operator audit/replay review."""
    limit = max(1, min(int(limit or 50), 500))
    offset = max(0, int(offset or 0))
    stmt = select(CRMApplyAction)
    if status:
        stmt = stmt.where(CRMApplyAction.status == status)
    if action_type:
        stmt = stmt.where(CRMApplyAction.action_type == action_type)
    if target_contact_ref:
        stmt = stmt.where(CRMApplyAction.target_contact_ref == target_contact_ref)
    rows = list(session.exec(stmt.order_by(desc(CRMApplyAction.created_at))).all())
    payloads = [_crm_apply_action_payload(row) for row in rows]
    if sms_thread_id is not None:
        payloads = [row for row in payloads if row.get('sms_thread_id') == sms_thread_id]
    total = len(payloads)
    page = payloads[offset:offset + limit]
    return {
        'limit': limit,
        'offset': offset,
        'total': total,
        'count': len(page),
        'actions': page,
    }


def get_crm_apply_action_detail(session: Session, crm_apply_action_id: int) -> dict[str, Any]:
    row = session.get(CRMApplyAction, crm_apply_action_id)
    if not row:
        raise ValueError('CRM apply action not found')
    data = _crm_apply_action_payload(row)
    if row.operator_decision_id:
        decision = session.get(OperatorDecision, row.operator_decision_id)
        data['operator_decision'] = decision.model_dump() if decision else None
    else:
        data['operator_decision'] = None
    thread_id = data.get('sms_thread_id')
    if thread_id:
        thread = session.get(SMSThread, int(thread_id))
        data['sms_thread'] = _sms_thread_payload(session, thread) if thread else None
    else:
        data['sms_thread'] = None
    return data


def crm_apply_action_export(
    session: Session,
    *,
    status: str = '',
    action_type: str = '',
    limit: int = 500,
) -> dict[str, Any]:
    """Return a compact export-friendly audit list without making live CRM calls."""
    result = list_crm_apply_actions(session, status=status, action_type=action_type, limit=limit, offset=0)
    rows: list[dict[str, Any]] = []
    for action in result['actions']:
        payload = action.get('payload') if isinstance(action.get('payload'), dict) else {}
        rows.append({
            'id': action.get('id'),
            'created_at': action.get('created_at'),
            'status': action.get('status'),
            'action_type': action.get('action_type'),
            'target_contact_ref': action.get('target_contact_ref'),
            'target_contact_id': action.get('target_contact_id'),
            'sms_thread_id': action.get('sms_thread_id'),
            'idempotency_key': action.get('idempotency_key'),
            'dry_run': action.get('dry_run'),
            'confirm_live_write': action.get('confirm_live_write'),
            'error': action.get('error'),
            'payload_operation': payload.get('operation'),
        })
    return {'count': len(rows), 'rows': rows}


def lacrm_apply_readiness(session: Session) -> dict[str, Any]:
    """Summarize whether the platform is ready for an intentional live LACRM apply step.

    Step 10 keeps dry-run as the safe default and requires an additional
    PLATFORM_LACRM_LIVE_WRITE_ARMED flag plus a typed confirmation phrase before
    any future live write can pass the gate. This function does not perform live
    writes.
    """
    status = lacrm_apply_status(session)
    status_counts = status.get('status_counts', {}) if isinstance(status.get('status_counts'), dict) else {}
    dry_run_total = int(status_counts.get('dry_run', 0) or 0)
    blocked_total = int(status_counts.get('blocked', 0) or 0)
    error_total = int(status_counts.get('error', 0) or 0)
    applied_total = int(status_counts.get('applied', 0) or 0)
    live_snapshot = lacrm_live_apply_readiness(session)
    blockers = [blocker for blocker in live_snapshot.get('blockers', []) if 'Typed live confirmation phrase' not in blocker]
    return {
        'ready_for_live_apply': len(blockers) == 0,
        'safe_default_mode': 'dry_run',
        'lacrm_api_key_configured': bool(status.get('lacrm_api_key_configured')),
        'live_write_enabled': bool(status.get('live_write_enabled')),
        'live_write_armed': bool(status.get('live_write_armed')),
        'required_confirmation_phrase': live_snapshot.get('required_confirmation_phrase'),
        'dry_run_total': dry_run_total,
        'blocked_total': blocked_total,
        'error_total': error_total,
        'applied_total': applied_total,
        'status_counts': status_counts,
        'action_type_counts': status.get('action_type_counts', {}),
        'blockers': blockers,
        'live_gate': live_snapshot.get('gates', {}),
        'next_steps': [
            'Review latest dry-run actions and payloads in the Streamlit Bridge Review Apply Audit tab.',
            'Confirm selected LACRM contacts are correct before enabling live writes.',
            'Keep PLATFORM_LACRM_LIVE_WRITE_ENABLED=false and PLATFORM_LACRM_LIVE_WRITE_ARMED=false until a deliberate live-write cutover step.',
        ],
        'latest_actions': status.get('latest_actions', []),
    }

def lacrm_apply_status(session: Session) -> dict[str, Any]:
    actions = list(session.exec(select(CRMApplyAction).order_by(desc(CRMApplyAction.created_at)).limit(25)).all())
    status_counts: dict[str, int] = {}
    type_counts: dict[str, int] = {}
    for action in session.exec(select(CRMApplyAction)).all():
        status_counts[action.status] = status_counts.get(action.status, 0) + 1
        type_counts[action.action_type] = type_counts.get(action.action_type, 0) + 1
    return {
        'lacrm_api_key_configured': get_lacrm_client() is not None,
        'live_write_enabled': _truthy_env('PLATFORM_LACRM_LIVE_WRITE_ENABLED'),
        'live_write_armed': _truthy_env('PLATFORM_LACRM_LIVE_WRITE_ARMED'),
        'required_confirmation_phrase': _live_confirmation_phrase(),
        'default_mode': 'dry_run',
        'status_counts': status_counts,
        'action_type_counts': type_counts,
        'latest_actions': [action.model_dump() | {'payload': _loads_dict(action.payload_json)} for action in actions],
    }



def _lacrm_first_value(contact: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = contact.get(key)
        if value is None:
            continue
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, (int, float)):
            return str(value)
    return ''


def _lacrm_contact_id(contact: dict[str, Any]) -> str:
    return _lacrm_first_value(contact, 'ContactId', 'ContactID', 'contact_id', 'Id', 'ID', 'id')


def _lacrm_phone_values(contact: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ('Phone', 'PhoneNumber', 'MobilePhone', 'WorkPhone', 'HomePhone', 'CellPhone', 'phone'):
        value = contact.get(key)
        if isinstance(value, str) and value.strip():
            values.append(value.strip())
    for key in ('Phones', 'PhoneNumbers', 'ContactPhones'):
        value = contact.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item.strip():
                    values.append(item.strip())
                elif isinstance(item, dict):
                    nested = _lacrm_first_value(item, 'Phone', 'PhoneNumber', 'Number', 'Value', 'value')
                    if nested:
                        values.append(nested)
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            unique.append(value)
    return unique


def _lacrm_contact_label(contact: dict[str, Any]) -> str:
    name = _lacrm_first_value(contact, 'Name', 'FullName', 'Full Name', 'ContactName', 'DisplayName', 'display_name')
    company = _lacrm_first_value(contact, 'CompanyName', 'Company Name', 'Company', 'company')
    email = _lacrm_first_value(contact, 'Email', 'EmailAddress', 'email')
    phones = _lacrm_phone_values(contact)
    parts = [part for part in (name, company, phones[0] if phones else '', email) if part]
    return ' — '.join(parts) if parts else f'LACRM contact {_lacrm_contact_id(contact)}'


def _normalize_lacrm_contact(contact: dict[str, Any]) -> dict[str, Any]:
    contact_id = _lacrm_contact_id(contact)
    phones = _lacrm_phone_values(contact)
    name = _lacrm_first_value(contact, 'Name', 'FullName', 'Full Name', 'ContactName', 'DisplayName', 'display_name')
    company = _lacrm_first_value(contact, 'CompanyName', 'Company Name', 'Company', 'company')
    email = _lacrm_first_value(contact, 'Email', 'EmailAddress', 'email')
    address = _lacrm_first_value(contact, 'Address', 'StreetAddress', 'MailingAddress', 'Background Info', 'BackgroundInfo')
    return {
        'contact_id': contact_id,
        'contact_ref': f'lacrm_contact:{contact_id}' if contact_id else '',
        'display_label': _lacrm_contact_label(contact),
        'name': name,
        'company': company,
        'email': email,
        'phones': phones,
        'address': address,
        'raw': contact,
    }


def _phone_tail(value: str) -> str:
    digits = ''.join(ch for ch in (value or '') if ch.isdigit())
    return digits[-7:]


def search_lacrm_contacts(
    search_terms: str,
    *,
    limit: int = 10,
    sample_contacts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Search LACRM contacts safely for platform candidate selection.

    Tests and local validation can supply sample_contacts to avoid live API calls.
    Without LACRM_API_KEY this returns mode=not_configured instead of failing.
    """
    limit = max(1, min(int(limit or 10), 50))
    terms = (search_terms or '').strip()
    if sample_contacts is not None:
        rows = [dict(row) for row in sample_contacts if isinstance(row, dict)]
        contacts = [_normalize_lacrm_contact(row) for row in rows if _lacrm_contact_id(row)]
        return {
            'configured': False,
            'mode': 'sample',
            'search_terms': terms,
            'count': len(contacts[:limit]),
            'contacts': contacts[:limit],
            'error': '',
        }
    client = get_lacrm_client()
    if client is None:
        return {
            'configured': False,
            'mode': 'not_configured',
            'search_terms': terms,
            'count': 0,
            'contacts': [],
            'error': 'LACRM_API_KEY is not configured for platform-side contact search.',
        }
    try:
        rows = client.get_contacts(terms, max_results=limit)
    except (LACRMAPIError, ValueError) as exc:
        return {
            'configured': True,
            'mode': 'error',
            'search_terms': terms,
            'count': 0,
            'contacts': [],
            'error': str(exc),
        }
    contacts = [_normalize_lacrm_contact(row) for row in rows if _lacrm_contact_id(row)]
    return {
        'configured': True,
        'mode': 'live_search',
        'search_terms': terms,
        'count': len(contacts[:limit]),
        'contacts': contacts[:limit],
        'error': '',
    }


def _thread_lacrm_search_terms(thread: SMSThread) -> list[str]:
    terms: list[str] = []
    for value in (thread.external_phone, thread.extracted_names, thread.extracted_address):
        cleaned = (value or '').strip()
        if cleaned and cleaned not in terms:
            terms.append(cleaned)
    for source in (thread.summary, thread.transcript):
        cleaned = clean_display_text(source or '').strip()
        if cleaned:
            snippet = cleaned.replace('\n', ' ')[:90].strip()
            if snippet and snippet not in terms:
                terms.append(snippet)
            break
    return terms[:5]


def _score_lacrm_contact_for_thread(thread: SMSThread, contact: dict[str, Any]) -> tuple[float, str]:
    reasons: list[str] = []
    score = 0.55
    thread_phone_tail = _phone_tail(thread.external_phone)
    if thread_phone_tail:
        for phone in contact.get('phones', []):
            if _phone_tail(str(phone)) == thread_phone_tail:
                score = max(score, 0.97)
                reasons.append('phone_match')
                break
    text_hint = ' '.join(filter(None, [thread.extracted_names, thread.extracted_address, thread.summary, thread.transcript]))
    label = ' '.join(filter(None, [contact.get('display_label', ''), contact.get('name', ''), contact.get('company', ''), contact.get('address', '')]))
    if text_hint and label:
        sim = similarity(text_hint[:300], label[:300])
        if sim >= 0.25:
            score = max(score, min(0.94, 0.55 + sim / 2))
            reasons.append(f'text_similarity:{sim:.2f}')
    if not reasons:
        reasons.append('lacrm_search_result')
    return round(score, 4), ','.join(reasons)


def build_lacrm_candidates_for_sms_thread(
    session: Session,
    sms_thread_id: int,
    *,
    search_terms: str = '',
    limit: int = 8,
    store: bool = True,
    sample_contacts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    thread = session.get(SMSThread, sms_thread_id)
    if not thread:
        raise ValueError('SMS thread not found')
    limit = max(1, min(int(limit or 8), 25))
    query_terms = [(search_terms or '').strip()] if (search_terms or '').strip() else _thread_lacrm_search_terms(thread)
    if not query_terms and sample_contacts is None:
        query_terms = [thread.external_phone]
    by_ref: dict[str, dict[str, Any]] = {}
    searches: list[dict[str, Any]] = []
    sample_consumed = False
    for term in query_terms:
        result = search_lacrm_contacts(term, limit=limit, sample_contacts=sample_contacts if not sample_consumed else None)
        sample_consumed = sample_contacts is not None
        searches.append({k: v for k, v in result.items() if k != 'contacts'})
        for contact in result.get('contacts', []):
            ref = contact.get('contact_ref', '')
            if ref and ref not in by_ref:
                by_ref[ref] = contact
        if len(by_ref) >= limit:
            break
    candidates: list[dict[str, Any]] = []
    for contact in by_ref.values():
        score, reason = _score_lacrm_contact_for_thread(thread, contact)
        item = {
            'ref': contact['contact_ref'],
            'contact_id': contact['contact_id'],
            'label': contact['display_label'],
            'score': score,
            'reason': reason,
            'raw': contact['raw'],
        }
        candidates.append(item)
    candidates.sort(key=lambda item: item['score'], reverse=True)
    candidates = candidates[:limit]
    if store:
        for item in candidates:
            existing = session.exec(
                select(ContactMatchCandidate).where(
                    ContactMatchCandidate.sms_thread_id == sms_thread_id,
                    ContactMatchCandidate.contact_ref == item['ref'],
                )
            ).first()
            if existing:
                existing.display_label = item['label']
                existing.score = item['score']
                existing.reasoning = f"lacrm:{item['reason']}"
                session.add(existing)
            else:
                session.add(ContactMatchCandidate(
                    sms_thread_id=sms_thread_id,
                    contact_ref=item['ref'],
                    display_label=item['label'],
                    score=item['score'],
                    reasoning=f"lacrm:{item['reason']}",
                ))
        session.commit()
    return {
        'sms_thread_id': sms_thread_id,
        'query_terms': query_terms,
        'searches': searches,
        'count': len(candidates),
        'stored': bool(store),
        'candidates': candidates,
    }


def list_queue(session: Session) -> dict[str, list[dict[str, Any]]]:
    comms = list(session.exec(select(CommunicationEvent).order_by(desc(CommunicationEvent.occurred_at)).limit(50)).all())
    threads = list(session.exec(select(SMSThread).order_by(desc(SMSThread.latest_message_at)).limit(50)).all())
    return {
        'communications': [item.model_dump() for item in comms],
        'sms_threads': [item.model_dump() for item in threads],
    }


def _candidate_payloads(session: Session, phone: str, text_hint: str = '') -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    agents = list(session.exec(select(ApprovedAgent)).all())
    for agent in agents:
        score = 0.0
        if phone and agent.phone and phone[-7:] == agent.phone[-7:]:
            score += 0.92
        if text_hint and agent.full_name:
            score = max(score, similarity(text_hint, agent.full_name))
        if score > 0:
            candidates.append({'ref': f'approved_agent:{agent.id}', 'label': agent.full_name, 'score': round(score, 4), 'reason': 'approved_agent'})
    accounts = list(session.exec(select(Account)).all())
    for account in accounts:
        score = similarity(text_hint, account.name) if text_hint else 0.0
        if score >= 0.55:
            candidates.append({'ref': f'account:{account.id}', 'label': account.name, 'score': round(score, 4), 'reason': 'account_name'})
    properties = list(session.exec(select(Property)).all())
    for prop in properties:
        label = ' '.join(filter(None, [prop.name, prop.address_line_1, prop.city]))
        score = similarity(text_hint, label) if text_hint else 0.0
        if score >= 0.55:
            candidates.append({'ref': f'property:{prop.id}', 'label': label, 'score': round(score, 4), 'reason': 'property_hint'})
    candidates.sort(key=lambda item: item['score'], reverse=True)
    return candidates[:8]


def build_candidates_for_communication(session: Session, communication_event_id: int) -> list[dict[str, Any]]:
    event = session.get(CommunicationEvent, communication_event_id)
    if not event:
        raise ValueError('Communication event not found')
    text_hint = ' '.join(filter(None, [event.caller_name, event.extracted_names, event.extracted_address, event.summary, event.transcript]))
    candidates = _candidate_payloads(session, event.external_phone, text_hint)
    session.exec(select(ContactMatchCandidate).where(ContactMatchCandidate.communication_event_id == communication_event_id)).all()
    for item in candidates:
        exists = session.exec(
            select(ContactMatchCandidate).where(
                ContactMatchCandidate.communication_event_id == communication_event_id,
                ContactMatchCandidate.contact_ref == item['ref'],
            )
        ).first()
        if not exists:
            session.add(ContactMatchCandidate(
                communication_event_id=communication_event_id,
                contact_ref=item['ref'],
                display_label=item['label'],
                score=item['score'],
                reasoning=item['reason'],
            ))
    session.commit()
    normalized = session.exec(select(NormalizedSourceRecord).where(NormalizedSourceRecord.id == event.normalized_record_id)).first()
    if normalized:
        session.exec(select(MatchCandidate).where(MatchCandidate.normalized_record_id == normalized.id)).all()
        for item in candidates:
            if not session.exec(select(MatchCandidate).where(MatchCandidate.normalized_record_id == normalized.id, MatchCandidate.candidate_ref == item['ref'])).first():
                session.add(MatchCandidate(
                    normalized_record_id=normalized.id,
                    candidate_type='contact',
                    candidate_ref=item['ref'],
                    score=item['score'],
                    reason=item['reason'],
                ))
        session.commit()
    return candidates


def build_candidates_for_sms_thread(session: Session, sms_thread_id: int) -> list[dict[str, Any]]:
    thread = session.get(SMSThread, sms_thread_id)
    if not thread:
        raise ValueError('SMS thread not found')
    text_hint = ' '.join(filter(None, [thread.extracted_names, thread.extracted_address, thread.summary, thread.transcript]))
    candidates = _candidate_payloads(session, thread.external_phone, text_hint)
    for item in candidates:
        exists = session.exec(
            select(ContactMatchCandidate).where(
                ContactMatchCandidate.sms_thread_id == sms_thread_id,
                ContactMatchCandidate.contact_ref == item['ref'],
            )
        ).first()
        if not exists:
            session.add(ContactMatchCandidate(
                sms_thread_id=sms_thread_id,
                contact_ref=item['ref'],
                display_label=item['label'],
                score=item['score'],
                reasoning=item['reason'],
            ))
    session.commit()
    return candidates


def approve_communication(session: Session, communication_event_id: int, chosen_contact_ref: str, decided_by: str = 'operator', notes: str = '') -> dict[str, Any]:
    event = session.get(CommunicationEvent, communication_event_id)
    if not event:
        raise ValueError('Communication event not found')
    event.status = 'approved'
    session.add(event)
    decision = OperatorDecision(
        communication_event_id=communication_event_id,
        decision='approved',
        chosen_contact_ref=chosen_contact_ref,
        notes=notes,
        decided_by=decided_by,
    )
    session.add(decision)
    normalized = session.get(NormalizedSourceRecord, event.normalized_record_id) if event.normalized_record_id else None
    approval = None
    apply_event = None
    if normalized:
        normalized.match_status = 'matched'
        normalized.approval_status = 'approved'
        normalized.apply_status = 'applied'
        session.add(normalized)
        approval = ApprovalDecision(
            normalized_record_id=normalized.id,
            decided_by=decided_by,
            decision='approved',
            decision_notes=notes,
            approved_ref=chosen_contact_ref,
        )
        session.add(approval)
        session.flush()
        apply_event = ApplyEvent(
            normalized_record_id=normalized.id,
            approval_decision_id=approval.id,
            target_type='communication_event',
            target_ref=f'communication_event:{communication_event_id}',
            outcome='applied',
            details_json=dumps({'chosen_contact_ref': chosen_contact_ref}),
        )
        session.add(apply_event)
        external_id = event.external_phone or f'event:{communication_event_id}'
        if not session.exec(select(ExternalIdentityMap).where(ExternalIdentityMap.source_slug == 'ringcentral', ExternalIdentityMap.external_id == external_id, ExternalIdentityMap.internal_id == chosen_contact_ref)).first():
            session.add(ExternalIdentityMap(
                source_slug='ringcentral',
                entity_type='phone',
                external_id=external_id,
                internal_type='contact_ref',
                internal_id=chosen_contact_ref,
                confidence=0.95,
            ))
    session.commit()
    return {
        'communication_event_id': communication_event_id,
        'chosen_contact_ref': chosen_contact_ref,
        'operator_decision_id': decision.id,
        'approval_decision_id': approval.id if approval else None,
        'apply_event_id': apply_event.id if apply_event else None,
    }


def approve_sms_thread(session: Session, sms_thread_id: int, chosen_contact_ref: str, decided_by: str = 'operator', notes: str = '') -> dict[str, Any]:
    thread = session.get(SMSThread, sms_thread_id)
    if not thread:
        raise ValueError('SMS thread not found')
    thread.status = 'approved'
    thread.auto_attached = True
    session.add(thread)
    decision = OperatorDecision(
        sms_thread_id=sms_thread_id,
        decision='approved',
        chosen_contact_ref=chosen_contact_ref,
        notes=notes,
        decided_by=decided_by,
    )
    session.add(decision)
    session.commit()
    return {
        'sms_thread_id': sms_thread_id,
        'chosen_contact_ref': chosen_contact_ref,
        'operator_decision_id': decision.id,
    }


def save_routing_preference(session: Session, phone: str, route_mode: str, default_contact_ref: str = '', favorite_refs: list[str] | None = None, notes: str = '') -> RoutingPreference:
    favorite_refs = favorite_refs or []
    record = session.exec(select(RoutingPreference).where(RoutingPreference.phone == phone)).first()
    if not record:
        record = RoutingPreference(phone=phone)
        session.add(record)
    record.route_mode = route_mode
    record.default_contact_ref = default_contact_ref
    record.favorite_refs_json = dumps(favorite_refs)
    record.notes = notes
    record.updated_at = datetime.utcnow()
    session.commit()
    session.refresh(record)
    return record


def create_follow_up_task(session: Session, title: str, *, communication_event_id: int | None = None, sms_thread_id: int | None = None, assignee_ref: str = '', due_date=None) -> dict[str, Any]:
    action = CRMApplyAction(
        action_type='task',
        target_contact_ref=assignee_ref,
        payload_json=dumps({'title': title}),
        status='queued',
    )
    session.add(action)
    session.commit()
    session.refresh(action)
    link = CommunicationTaskLink(
        communication_event_id=communication_event_id,
        sms_thread_id=sms_thread_id,
        crm_apply_action_id=action.id,
        title=title,
        due_date=due_date,
        assignee_ref=assignee_ref,
        status='open',
    )
    session.add(link)
    session.commit()
    session.refresh(link)
    return {'task_link_id': link.id, 'crm_apply_action_id': action.id, 'status': 'queued'}
