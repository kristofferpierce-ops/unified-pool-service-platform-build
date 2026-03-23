from __future__ import annotations

from datetime import datetime
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
)
from app.models.connector_tables import ApplyEvent, ApprovalDecision, ExternalIdentityMap, MatchCandidate, NormalizedSourceRecord
from app.models.tables import Account, ApprovedAgent, Property
from app.utils.matching import similarity
from app.utils.serialization import dumps, loads


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
