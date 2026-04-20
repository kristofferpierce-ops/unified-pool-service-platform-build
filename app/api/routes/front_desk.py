from __future__ import annotations

import os
from datetime import date
from typing import Any

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from app.core.database import engine
from app.services.front_desk import (
    approve_communication,
    approve_sms_thread,
    bridge_review_summary,
    build_candidates_for_communication,
    build_candidates_for_sms_thread,
    compare_bridge_sms_batches,
    create_follow_up_task,
    get_sms_thread_detail,
    list_queue,
    list_review_actions,
    list_sms_threads,
    review_action_summary,
    save_routing_preference,
    set_sms_thread_review_status,
    add_sms_thread_review_note,
)

router = APIRouter(prefix='/front-desk', tags=['front-desk'])


class ApprovalBody(BaseModel):
    chosen_contact_ref: str
    decided_by: str = 'operator'
    notes: str = ''


class RoutingBody(BaseModel):
    phone: str
    route_mode: str
    default_contact_ref: str = ''
    favorite_refs: list[str] = []
    notes: str = ''


class TaskBody(BaseModel):
    title: str
    assignee_ref: str = ''
    due_date: date | None = None


class ReviewStatusBody(BaseModel):
    status: str
    decided_by: str = 'operator'
    notes: str = ''


class ReviewNoteBody(BaseModel):
    note: str
    decided_by: str = 'operator'


@router.get('/queue')
def queue():
    with Session(engine) as session:
        return list_queue(session)


@router.get('/sms-threads')
def sms_threads(status: str = '', external_phone: str = '', local_day: str = '', source: str = '', limit: int = 50, offset: int = 0):
    with Session(engine) as session:
        return list_sms_threads(
            session,
            status=status,
            external_phone=external_phone,
            local_day=local_day,
            source=source,
            limit=limit,
            offset=offset,
        )


@router.get('/sms-threads/{sms_thread_id}')
def sms_thread_detail(sms_thread_id: int):
    with Session(engine) as session:
        try:
            return get_sms_thread_detail(session, sms_thread_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get('/review-actions')
def review_actions(sms_thread_id: int | None = None, limit: int = 50, offset: int = 0):
    with Session(engine) as session:
        return list_review_actions(session, sms_thread_id=sms_thread_id, limit=limit, offset=offset)


@router.post('/sms-threads/{sms_thread_id}/review-status')
def sms_thread_review_status(sms_thread_id: int, body: ReviewStatusBody):
    with Session(engine) as session:
        try:
            return set_sms_thread_review_status(
                session,
                sms_thread_id,
                status=body.status,
                decided_by=body.decided_by,
                notes=body.notes,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400 if 'Unsupported' in str(exc) else 404, detail=str(exc)) from exc


@router.post('/sms-threads/{sms_thread_id}/review-note')
def sms_thread_review_note(sms_thread_id: int, body: ReviewNoteBody):
    with Session(engine) as session:
        try:
            return add_sms_thread_review_note(session, sms_thread_id, note=body.note, decided_by=body.decided_by)
        except ValueError as exc:
            raise HTTPException(status_code=400 if 'required' in str(exc) else 404, detail=str(exc)) from exc


@router.get('/bridge-review-summary')
def bridge_review_queue_summary():
    with Session(engine) as session:
        return bridge_review_summary(session)


@router.get('/review-action-summary')
def front_desk_review_action_summary():
    with Session(engine) as session:
        return review_action_summary(session)


@router.get('/bridge-compare/sms-batches')
def bridge_compare_sms_batches(bridge_api_base_url: str = '', limit: int = 250):
    base_url = (bridge_api_base_url or os.getenv('BRIDGE_API_BASE_URL') or 'http://127.0.0.1:8000').rstrip('/')
    headers: dict[str, str] = {}
    token = os.getenv('BRIDGE_CONTROL_TOKEN', '').strip()
    if token:
        headers['X-Bridge-Admin-Token'] = token
    try:
        response = requests.get(f'{base_url}/api/sms/batches', params={'view': 'active'}, headers=headers, timeout=8)
        response.raise_for_status()
        payload: Any = response.json()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f'Could not reach bridge API at {base_url}: {exc}') from exc
    batches = payload.get('batches', payload) if isinstance(payload, dict) else payload
    if not isinstance(batches, list):
        batches = []
    batches = batches[: max(1, min(int(limit or 250), 1000))]
    with Session(engine) as session:
        result = compare_bridge_sms_batches(session, batches)
    result['bridge_api_base_url'] = base_url
    return result


@router.post('/communications/{communication_event_id}/candidates')
def communication_candidates(communication_event_id: int):
    with Session(engine) as session:
        try:
            return build_candidates_for_communication(session, communication_event_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post('/communications/{communication_event_id}/approve')
def communication_approve(communication_event_id: int, body: ApprovalBody):
    with Session(engine) as session:
        try:
            return approve_communication(session, communication_event_id, body.chosen_contact_ref, body.decided_by, body.notes)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post('/communications/{communication_event_id}/task')
def communication_task(communication_event_id: int, body: TaskBody):
    with Session(engine) as session:
        return create_follow_up_task(session, body.title, communication_event_id=communication_event_id, assignee_ref=body.assignee_ref, due_date=body.due_date)


@router.post('/sms-threads/{sms_thread_id}/candidates')
def sms_candidates(sms_thread_id: int):
    with Session(engine) as session:
        try:
            return build_candidates_for_sms_thread(session, sms_thread_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post('/sms-threads/{sms_thread_id}/approve')
def sms_approve(sms_thread_id: int, body: ApprovalBody):
    with Session(engine) as session:
        try:
            return approve_sms_thread(session, sms_thread_id, body.chosen_contact_ref, body.decided_by, body.notes)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post('/sms-threads/{sms_thread_id}/task')
def sms_task(sms_thread_id: int, body: TaskBody):
    with Session(engine) as session:
        return create_follow_up_task(session, body.title, sms_thread_id=sms_thread_id, assignee_ref=body.assignee_ref, due_date=body.due_date)


@router.post('/routing-preferences')
def routing_preferences(body: RoutingBody):
    with Session(engine) as session:
        record = save_routing_preference(session, body.phone, body.route_mode, body.default_contact_ref, body.favorite_refs, body.notes)
        return record
