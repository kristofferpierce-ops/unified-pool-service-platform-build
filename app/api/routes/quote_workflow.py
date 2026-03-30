from __future__ import annotations

import json
from datetime import datetime
from urllib.parse import parse_qs

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.core.database import engine
from app.services.lacrm_sync import (
    get_case_lacrm_summary,
    get_lacrm_mapping_summary,
    link_quote_case_to_lacrm_contact,
    reconcile_lacrm_payload,
    refresh_lacrm_mapping_from_api,
    store_lacrm_webhook_secret,
    sync_quote_case_to_lacrm,
    verify_lacrm_webhook_signature,
)
from app.services.freshbooks_sync import (
    get_case_freshbooks_summary,
    get_freshbooks_mapping_summary,
    link_quote_case_to_freshbooks_client,
    mark_quote_case_freshbooks_sent,
    reconcile_freshbooks_payload,
    refresh_freshbooks_context_from_api,
    refresh_quote_case_from_freshbooks,
    store_freshbooks_webhook_verifier,
    sync_quote_case_to_freshbooks,
    verify_freshbooks_webhook_signature,
)
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
    payload: dict = Field(default_factory=dict)


class ViewedBody(BaseModel):
    viewed_at: datetime | None = None


class LACRMContactLinkBody(BaseModel):
    contact_id: str
    contact_name: str = ''


class LACRMSyncBody(BaseModel):
    note: str = ''
    force_live: bool = False
    create_follow_up_task: bool = True


class LACRMReconcileBody(BaseModel):
    payload: dict = Field(default_factory=dict)


class FreshBooksLineItemBody(BaseModel):
    name: str
    description: str = ''
    qty: float = 1
    type: int = 0
    amount: float = 0
    code: str = 'USD'
    taxName1: str = ''
    taxAmount1: float = 0
    taxName2: str = ''
    taxAmount2: float = 0


class FreshBooksClientLinkBody(BaseModel):
    client_id: str
    client_name: str = ''


class FreshBooksDraftBody(BaseModel):
    note: str = ''
    force_live: bool = False
    create_client_if_missing: bool = True
    currency_code: str = 'USD'
    terms: str = ''
    notes: str = ''
    organization: str = ''
    lines: list[FreshBooksLineItemBody] = Field(default_factory=list)


class FreshBooksRefreshBody(BaseModel):
    force_live: bool = False


class FreshBooksMarkSentBody(BaseModel):
    sent_at: datetime | None = None
    move_to_follow_up: bool = True


class FreshBooksReconcileBody(BaseModel):
    payload: dict = Field(default_factory=dict)


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


@router.get('/lacrm/mapping')
def lacrm_mapping_summary():
    with Session(engine) as session:
        return get_lacrm_mapping_summary(session)


@router.post('/lacrm/mapping/refresh')
def lacrm_mapping_refresh():
    with Session(engine) as session:
        try:
            return refresh_lacrm_mapping_from_api(session)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get('/cases/{quote_case_id}/lacrm')
def case_lacrm_summary(quote_case_id: int):
    with Session(engine) as session:
        try:
            return get_case_lacrm_summary(session, quote_case_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post('/cases/{quote_case_id}/lacrm/contact-link')
def case_lacrm_contact_link(quote_case_id: int, body: LACRMContactLinkBody):
    with Session(engine) as session:
        try:
            return link_quote_case_to_lacrm_contact(
                session,
                quote_case_id,
                contact_id=body.contact_id,
                contact_name=body.contact_name,
            )
        except ValueError as exc:
            status_code = 404 if 'not found' in str(exc).lower() else 400
            raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.post('/cases/{quote_case_id}/lacrm/sync')
def case_lacrm_sync(quote_case_id: int, body: LACRMSyncBody):
    with Session(engine) as session:
        try:
            return sync_quote_case_to_lacrm(
                session,
                quote_case_id,
                note=body.note,
                force_live=body.force_live,
                create_follow_up_task=body.create_follow_up_task,
            )
        except ValueError as exc:
            status_code = 404 if 'not found' in str(exc).lower() else 400
            raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.post('/lacrm/reconcile')
def lacrm_reconcile(body: LACRMReconcileBody):
    with Session(engine) as session:
        return reconcile_lacrm_payload(session, body.payload)


@router.get('/freshbooks/mapping')
def freshbooks_mapping_summary():
    with Session(engine) as session:
        return get_freshbooks_mapping_summary(session)


@router.post('/freshbooks/context/refresh')
def freshbooks_context_refresh():
    with Session(engine) as session:
        try:
            return refresh_freshbooks_context_from_api(session)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get('/cases/{quote_case_id}/freshbooks')
def case_freshbooks_summary(quote_case_id: int):
    with Session(engine) as session:
        try:
            return get_case_freshbooks_summary(session, quote_case_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post('/cases/{quote_case_id}/freshbooks/client-link')
def case_freshbooks_client_link(quote_case_id: int, body: FreshBooksClientLinkBody):
    with Session(engine) as session:
        try:
            return link_quote_case_to_freshbooks_client(
                session,
                quote_case_id,
                client_id=body.client_id,
                client_name=body.client_name,
            )
        except ValueError as exc:
            status_code = 404 if 'not found' in str(exc).lower() else 400
            raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.post('/cases/{quote_case_id}/freshbooks/draft')
def case_freshbooks_draft(quote_case_id: int, body: FreshBooksDraftBody):
    with Session(engine) as session:
        try:
            line_items = [item.model_dump() for item in body.lines]
            return sync_quote_case_to_freshbooks(
                session,
                quote_case_id,
                lines=line_items,
                note=body.note,
                force_live=body.force_live,
                create_client_if_missing=body.create_client_if_missing,
                currency_code=body.currency_code,
                terms=body.terms,
                notes=body.notes,
                organization=body.organization,
            )
        except ValueError as exc:
            status_code = 404 if 'not found' in str(exc).lower() else 400
            raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.post('/cases/{quote_case_id}/freshbooks/refresh')
def case_freshbooks_refresh(quote_case_id: int, body: FreshBooksRefreshBody):
    with Session(engine) as session:
        try:
            return refresh_quote_case_from_freshbooks(session, quote_case_id, force_live=body.force_live)
        except ValueError as exc:
            status_code = 404 if 'not found' in str(exc).lower() else 400
            raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.post('/cases/{quote_case_id}/freshbooks/mark-sent')
def case_freshbooks_mark_sent(quote_case_id: int, body: FreshBooksMarkSentBody):
    with Session(engine) as session:
        try:
            return mark_quote_case_freshbooks_sent(
                session,
                quote_case_id,
                sent_at=body.sent_at,
                move_to_follow_up=body.move_to_follow_up,
            )
        except ValueError as exc:
            status_code = 404 if 'not found' in str(exc).lower() else 400
            raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.post('/freshbooks/reconcile')
def freshbooks_reconcile(body: FreshBooksReconcileBody):
    with Session(engine) as session:
        return reconcile_freshbooks_payload(session, body.payload)


@router.post('/freshbooks/webhook')
async def freshbooks_webhook(request: Request):
    body = await request.body()
    content_type = (request.headers.get('content-type') or '').lower()
    if 'application/json' in content_type:
        form_payload = json.loads(body.decode('utf-8') or '{}')
    else:
        parsed = parse_qs(body.decode('utf-8') if body else '', keep_blank_values=True)
        form_payload = {
            key: values[-1] if isinstance(values, list) and values else ''
            for key, values in parsed.items()
        }
    verifier = str(form_payload.get('verifier', '')).strip()
    callback_id = str(form_payload.get('callback_id', '') or form_payload.get('callbackid', '')).strip()
    with Session(engine) as session:
        if verifier and callback_id:
            store_freshbooks_webhook_verifier(session, verifier)
            return {'verification_received': True, 'callback_id': callback_id}
        signature = request.headers.get('X-FreshBooks-Hmac-SHA256')
        if not verify_freshbooks_webhook_signature(session, form_payload, signature):
            raise HTTPException(status_code=401, detail='Invalid FreshBooks webhook signature')
        return reconcile_freshbooks_payload(session, form_payload)


@router.post('/lacrm/webhook')
async def lacrm_webhook(request: Request):
    hook_secret = request.headers.get('X-Hook-Secret')
    if hook_secret:
        with Session(engine) as session:
            store_lacrm_webhook_secret(session, hook_secret)
        return Response(content='', headers={'X-Hook-Secret': hook_secret})

    body = await request.body()
    with Session(engine) as session:
        signature = request.headers.get('X-Hook-Signature')
        if not verify_lacrm_webhook_signature(session, body, signature):
            raise HTTPException(status_code=401, detail='Invalid LACRM webhook signature')
        try:
            payload = json.loads(body.decode('utf-8') or '{}')
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail='Webhook payload was not valid JSON') from exc
        return reconcile_lacrm_payload(session, payload)
