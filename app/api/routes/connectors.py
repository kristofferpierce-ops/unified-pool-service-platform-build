from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.database import engine
from app.models.connector_tables import SourceSystem
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
