from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from sqlmodel import Session, desc, select

from app.core.database import engine
from app.models.communication_tables import CommunicationEvent, SMSMessage, SMSThread
from app.models.connector_tables import NormalizedSourceRecord, RawSourceRecord, SourceSystem
from app.utils.serialization import loads
from app.services.ingestion import ingest_ringcentral_event

router = APIRouter(prefix='/connectors', tags=['connectors'])


class RawPayload(BaseModel):
    payload: dict


@router.get('/sources')
def list_sources():
    with Session(engine) as session:
        return list(session.exec(select(SourceSystem)).all())


@router.post('/ringcentral/events')
def push_ringcentral_event(body: RawPayload):
    with Session(engine) as session:
        return ingest_ringcentral_event(session, body.payload)


def _raw_record_payload(row: RawSourceRecord, include_payload: bool = False) -> dict:
    data = row.model_dump()
    if include_payload:
        data['payload'] = loads(row.payload_json, {})
    data.pop('payload_json', None)
    return data


def _normalized_record_payload(row: NormalizedSourceRecord, include_payload: bool = False) -> dict:
    data = row.model_dump()
    if include_payload:
        data['normalized'] = loads(row.normalized_json, {})
    data.pop('normalized_json', None)
    return data


def _count(session: Session, model, *conditions) -> int:
    stmt = select(model)
    for condition in conditions:
        stmt = stmt.where(condition)
    return len(list(session.exec(stmt).all()))


@router.get('/ringcentral/ingestion-status')
def ringcentral_ingestion_status():
    with Session(engine) as session:
        raw_rows = list(session.exec(select(RawSourceRecord).where(RawSourceRecord.source_slug == 'ringcentral')).all())
        normalized_rows = list(session.exec(select(NormalizedSourceRecord).where(NormalizedSourceRecord.source_slug == 'ringcentral')).all())
        raw_by_type: dict[str, int] = {}
        for row in raw_rows:
            raw_by_type[row.record_type] = raw_by_type.get(row.record_type, 0) + 1
        normalized_by_entity: dict[str, int] = {}
        for row in normalized_rows:
            normalized_by_entity[row.entity_type] = normalized_by_entity.get(row.entity_type, 0) + 1
        latest_raw = list(session.exec(
            select(RawSourceRecord)
            .where(RawSourceRecord.source_slug == 'ringcentral')
            .order_by(desc(RawSourceRecord.received_at))
            .limit(5)
        ).all())
        latest_threads = list(session.exec(
            select(SMSThread)
            .order_by(desc(SMSThread.latest_message_at))
            .limit(5)
        ).all())
        return {
            'raw_total': len(raw_rows),
            'raw_by_type': raw_by_type,
            'normalized_total': len(normalized_rows),
            'normalized_by_entity': normalized_by_entity,
            'communication_events_total': _count(session, CommunicationEvent, CommunicationEvent.source_slug == 'ringcentral'),
            'sms_threads_total': _count(session, SMSThread),
            'sms_messages_total': _count(session, SMSMessage),
            'latest_raw_records': [_raw_record_payload(row, include_payload=False) for row in latest_raw],
            'latest_sms_threads': [row.model_dump() for row in latest_threads],
        }


@router.get('/ringcentral/raw-records')
def ringcentral_raw_records(limit: int = 50, offset: int = 0, record_type: str = '', include_payload: bool = False):
    limit = max(1, min(int(limit or 50), 250))
    offset = max(0, int(offset or 0))
    with Session(engine) as session:
        stmt = select(RawSourceRecord).where(RawSourceRecord.source_slug == 'ringcentral')
        if record_type:
            stmt = stmt.where(RawSourceRecord.record_type == record_type)
        rows = list(session.exec(stmt.order_by(desc(RawSourceRecord.received_at)).offset(offset).limit(limit)).all())
        return {'limit': limit, 'offset': offset, 'records': [_raw_record_payload(row, include_payload=include_payload) for row in rows]}


@router.get('/ringcentral/normalized-records')
def ringcentral_normalized_records(limit: int = 50, offset: int = 0, entity_type: str = '', include_payload: bool = False):
    limit = max(1, min(int(limit or 50), 250))
    offset = max(0, int(offset or 0))
    with Session(engine) as session:
        stmt = select(NormalizedSourceRecord).where(NormalizedSourceRecord.source_slug == 'ringcentral')
        if entity_type:
            stmt = stmt.where(NormalizedSourceRecord.entity_type == entity_type)
        rows = list(session.exec(stmt.order_by(desc(NormalizedSourceRecord.created_at)).offset(offset).limit(limit)).all())
        return {'limit': limit, 'offset': offset, 'records': [_normalized_record_payload(row, include_payload=include_payload) for row in rows]}


@router.get('/ringcentral/sms-messages')
def ringcentral_sms_messages(limit: int = 50, offset: int = 0):
    limit = max(1, min(int(limit or 50), 250))
    offset = max(0, int(offset or 0))
    with Session(engine) as session:
        rows = list(session.exec(select(SMSMessage).order_by(desc(SMSMessage.occurred_at)).offset(offset).limit(limit)).all())
        return {'limit': limit, 'offset': offset, 'messages': [row.model_dump() for row in rows]}
