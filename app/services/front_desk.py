from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlmodel import Session, desc, select

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
    """Best-effort cleanup for legacy mojibake without mutating stored data."""
    if not value:
        return ''
    text = str(value)
    if not any(marker in text for marker in _MOJIBAKE_MARKERS):
        return text
    try:
        repaired = text.encode('latin1').decode('utf-8')
        if repaired.count('\ufffd') <= text.count('\ufffd'):
            return repaired
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
        'ï¸': '',
    }
    repaired = text
    for bad, good in replacements.items():
        repaired = repaired.replace(bad, good)
    return repaired


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
