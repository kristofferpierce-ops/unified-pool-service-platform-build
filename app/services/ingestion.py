from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session, select

from app.connectors.ringcentral.normalizer import normalize_ringcentral_payload
from app.models.communication_tables import CallSession, CommunicationEvent, SMSMessage, SMSThread, VoicemailItem
from app.models.connector_tables import (
    ConnectorRun,
    NormalizedSourceRecord,
    RawSourceRecord,
    SourceSystem,
)
from app.utils.serialization import dumps


def normalize_occurrence_timestamp(value: str | None) -> datetime:
    if not value:
        return datetime.utcnow()
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is not None:
        return parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def normalize_database_timestamp(value: datetime | None) -> datetime:
    if value is None:
        return datetime.utcnow()
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def ensure_source_system(session: Session, slug: str, display_name: str, category: str = 'connector') -> SourceSystem:
    record = session.exec(select(SourceSystem).where(SourceSystem.slug == slug)).first()
    if record:
        return record
    record = SourceSystem(slug=slug, display_name=display_name, category=category)
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def begin_connector_run(session: Session, source_slug: str, run_type: str = 'webhook', direction: str = 'inbound', notes: str = '') -> ConnectorRun:
    source = ensure_source_system(session, source_slug, source_slug.replace('_', ' ').title())
    run = ConnectorRun(source_system_id=source.id, source_slug=source_slug, run_type=run_type, direction=direction, notes=notes)
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def record_raw_payload(session: Session, run: ConnectorRun, source_slug: str, payload: dict[str, Any], record_type: str, external_id: str = '') -> RawSourceRecord:
    payload_json = dumps(payload)
    payload_hash = hashlib.sha256(payload_json.encode('utf-8')).hexdigest()
    raw = RawSourceRecord(
        source_slug=source_slug,
        connector_run_id=run.id,
        external_id=external_id,
        record_type=record_type,
        payload_json=payload_json,
        payload_hash=payload_hash,
    )
    session.add(raw)
    run.raw_record_count += 1
    session.commit()
    session.refresh(raw)
    session.refresh(run)
    return raw


def record_normalized_payload(session: Session, raw: RawSourceRecord, source_slug: str, entity_type: str, normalized_payload: dict[str, Any]) -> NormalizedSourceRecord:
    fingerprint = hashlib.sha256(dumps(normalized_payload).encode('utf-8')).hexdigest()
    normalized = NormalizedSourceRecord(
        raw_record_id=raw.id,
        source_slug=source_slug,
        entity_type=entity_type,
        normalized_json=dumps(normalized_payload),
        fingerprint=fingerprint,
    )
    session.add(normalized)
    run = session.get(ConnectorRun, raw.connector_run_id)
    if run:
        run.normalized_record_count += 1
    session.commit()
    session.refresh(normalized)
    return normalized


def materialize_ringcentral_event(session: Session, normalized: NormalizedSourceRecord, normalized_payload: dict[str, Any]) -> dict[str, Any]:
    event_kind = normalized_payload['event_kind']
    result: dict[str, Any] = {'event_kind': event_kind, 'normalized_record_id': normalized.id}
    occurred_at = normalize_occurrence_timestamp(normalized_payload.get('occurred_at'))
    if event_kind in {'call', 'voicemail'}:
        event = CommunicationEvent(
            normalized_record_id=normalized.id,
            source_slug='ringcentral',
            event_kind=event_kind,
            external_phone=normalized_payload.get('external_phone', ''),
            internal_phone=normalized_payload.get('internal_phone', ''),
            caller_name=normalized_payload.get('caller_name', ''),
            occurred_at=occurred_at,
            status='pending_review',
            extracted_address=normalized_payload.get('extracted_address', ''),
            extracted_names=normalized_payload.get('extracted_names', ''),
            summary=normalized_payload.get('summary', ''),
            transcript=normalized_payload.get('transcript', ''),
            raw_json=dumps(normalized_payload),
        )
        session.add(event)
        session.commit()
        session.refresh(event)
        result['communication_event_id'] = event.id
        if event_kind == 'call':
            call = CallSession(
                communication_event_id=event.id,
                telephony_session_id=normalized_payload.get('telephony_session_id', ''),
                direction=normalized_payload.get('direction', ''),
                agent_extension_id=normalized_payload.get('agent_extension_id', ''),
                recording_uri=normalized_payload.get('recording_uri', ''),
                disposition=normalized_payload.get('disposition', ''),
            )
            session.add(call)
        else:
            voicemail = VoicemailItem(
                communication_event_id=event.id,
                voicemail_message_id=normalized_payload.get('voicemail_message_id', ''),
                duration_seconds=normalized_payload.get('duration_seconds', 0),
                transcription_status=normalized_payload.get('transcription_status', ''),
                recording_uri=normalized_payload.get('recording_uri', ''),
                transcription_uri=normalized_payload.get('transcription_uri', ''),
            )
            session.add(voicemail)
        session.commit()
        return result

    if event_kind == 'sms':
        local_day = occurred_at.date()
        thread = session.exec(
            select(SMSThread).where(
                SMSThread.external_phone == normalized_payload.get('external_phone', ''),
                SMSThread.local_day == local_day,
            )
        ).first()
        if not thread:
            thread = SMSThread(
                normalized_record_id=normalized.id,
                external_phone=normalized_payload.get('external_phone', ''),
                internal_phone=normalized_payload.get('internal_phone', ''),
                local_day=local_day,
                latest_message_at=occurred_at,
                status='pending_review',
                summary=normalized_payload.get('summary', ''),
                transcript=normalized_payload.get('transcript', ''),
                extracted_address=normalized_payload.get('extracted_address', ''),
                extracted_names=normalized_payload.get('extracted_names', ''),
                raw_json=dumps({'thread_seed': normalized_payload}),
            )
            session.add(thread)
            session.commit()
            session.refresh(thread)
        else:
            thread.latest_message_at = max(normalize_database_timestamp(thread.latest_message_at), occurred_at)
            if normalized_payload.get('body'):
                existing = thread.transcript or ''
                thread.transcript = (existing + ('\n' if existing else '') + normalized_payload['body']).strip()
            session.add(thread)
            session.commit()
        msg = SMSMessage(
            sms_thread_id=thread.id,
            message_external_id=normalized_payload.get('message_external_id', ''),
            direction=normalized_payload.get('direction', ''),
            from_phone=normalized_payload.get('from_phone', ''),
            to_phone=normalized_payload.get('to_phone', ''),
            body=normalized_payload.get('body', ''),
            occurred_at=occurred_at,
            raw_json=dumps(normalized_payload),
        )
        session.add(msg)
        session.commit()
        result['sms_thread_id'] = thread.id
        result['sms_message_id'] = msg.id
        return result

    return result


def ingest_ringcentral_event(session: Session, payload: dict[str, Any]) -> dict[str, Any]:
    normalized_payload = normalize_ringcentral_payload(payload)
    run = begin_connector_run(session, 'ringcentral', run_type='webhook', direction='inbound', notes=normalized_payload['event_kind'])
    raw = record_raw_payload(
        session,
        run,
        'ringcentral',
        payload,
        record_type=normalized_payload['event_kind'],
        external_id=normalized_payload.get('external_id', ''),
    )
    normalized = record_normalized_payload(session, raw, 'ringcentral', normalized_payload['entity_type'], normalized_payload)
    materialized = materialize_ringcentral_event(session, normalized, normalized_payload)
    run.status = 'materialized'
    run.finished_at = datetime.utcnow()
    session.add(run)
    session.commit()
    return {
        'connector_run_id': run.id,
        'raw_record_id': raw.id,
        'normalized_record_id': normalized.id,
        'normalized_payload': normalized_payload,
        'materialized': materialized,
    }
