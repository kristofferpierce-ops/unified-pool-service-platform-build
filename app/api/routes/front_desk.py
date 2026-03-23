from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from app.core.database import engine
from app.services.front_desk import (
    approve_communication,
    approve_sms_thread,
    build_candidates_for_communication,
    build_candidates_for_sms_thread,
    create_follow_up_task,
    list_queue,
    save_routing_preference,
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


@router.get('/queue')
def queue():
    with Session(engine) as session:
        return list_queue(session)


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
