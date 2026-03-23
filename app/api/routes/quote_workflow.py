from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from app.core.database import engine
from app.services.quote_workflow import (
    add_external_link,
    create_quote_case,
    get_dashboard_summary,
    get_quote_case,
    get_quote_workflow_config,
    list_external_links,
    list_quote_cases,
    list_stage_history,
    mark_quote_viewed,
    move_quote_case,
    serialize_quote_case,
)

router = APIRouter(prefix='/quote-workflow', tags=['quote-workflow'])


class QuoteCaseCreateBody(BaseModel):
    pipeline_slug: str
    title: str
    stage_slug: str | None = None
    workflow_mode: str = 'quote'
    account_id: int | None = None
    property_id: int | None = None
    vessel_id: int | None = None
    requester_name: str = ''
    requester_phone: str = ''
    requester_email: str = ''
    description: str = ''
    assigned_to: str = ''


class QuoteMoveBody(BaseModel):
    target_stage_slug: str
    moved_by: str = 'operator'
    move_reason: str = ''
    sync_status: str | None = None
    sync_notes: str | None = None


class ExternalLinkBody(BaseModel):
    system_slug: str
    external_id: str
    external_type: str = 'record'
    external_label: str = ''
    sync_direction: str = 'bidirectional'
    sync_status: str = 'linked'
    payload: dict = {}


class ViewedBody(BaseModel):
    viewed_at: datetime | None = None


@router.get('/config')
def workflow_config():
    with Session(engine) as session:
        return get_quote_workflow_config(session)


@router.get('/dashboard')
def workflow_dashboard():
    with Session(engine) as session:
        return get_dashboard_summary(session)


@router.get('/cases')
def quote_cases(pipeline_slug: str | None = None, stage_slug: str | None = None, include_closed: bool = True, limit: int = 200):
    with Session(engine) as session:
        config = get_quote_workflow_config(session)
        return [serialize_quote_case(session, case, config) for case in list_quote_cases(session, pipeline_slug=pipeline_slug, stage_slug=stage_slug, include_closed=include_closed, limit=limit)]


@router.get('/cases/{quote_case_id}')
def quote_case_detail(quote_case_id: int):
    with Session(engine) as session:
        case = get_quote_case(session, quote_case_id)
        if not case:
            raise HTTPException(status_code=404, detail='Quote case not found')
        config = get_quote_workflow_config(session)
        payload = serialize_quote_case(session, case, config)
        payload['external_links'] = [item.model_dump() for item in list_external_links(session, quote_case_id)]
        payload['stage_history'] = [item.model_dump() for item in list_stage_history(session, quote_case_id)]
        return payload


@router.post('/cases')
def create_case(body: QuoteCaseCreateBody):
    with Session(engine) as session:
        try:
            case = create_quote_case(
                session,
                pipeline_slug=body.pipeline_slug,
                title=body.title,
                stage_slug=body.stage_slug,
                workflow_mode=body.workflow_mode,
                account_id=body.account_id,
                property_id=body.property_id,
                vessel_id=body.vessel_id,
                requester_name=body.requester_name,
                requester_phone=body.requester_phone,
                requester_email=body.requester_email,
                description=body.description,
                assigned_to=body.assigned_to,
            )
            return serialize_quote_case(session, case)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/cases/{quote_case_id}/move')
def move_case(quote_case_id: int, body: QuoteMoveBody):
    with Session(engine) as session:
        try:
            case = move_quote_case(
                session,
                quote_case_id,
                target_stage_slug=body.target_stage_slug,
                moved_by=body.moved_by,
                move_reason=body.move_reason,
                sync_status=body.sync_status,
                sync_notes=body.sync_notes,
            )
            return serialize_quote_case(session, case)
        except ValueError as exc:
            status_code = 404 if 'not found' in str(exc).lower() else 400
            raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.post('/cases/{quote_case_id}/viewed')
def mark_case_viewed(quote_case_id: int, body: ViewedBody):
    with Session(engine) as session:
        try:
            case = mark_quote_viewed(session, quote_case_id, body.viewed_at)
            return serialize_quote_case(session, case)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post('/cases/{quote_case_id}/external-links')
def link_case(quote_case_id: int, body: ExternalLinkBody):
    with Session(engine) as session:
        case = get_quote_case(session, quote_case_id)
        if not case:
            raise HTTPException(status_code=404, detail='Quote case not found')
        link = add_external_link(
            session,
            quote_case_id=quote_case_id,
            system_slug=body.system_slug,
            external_id=body.external_id,
            external_type=body.external_type,
            external_label=body.external_label,
            sync_direction=body.sync_direction,
            sync_status=body.sync_status,
            payload=body.payload,
        )
        return link.model_dump()
