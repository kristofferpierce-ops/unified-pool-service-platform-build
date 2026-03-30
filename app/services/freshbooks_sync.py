from __future__ import annotations

import base64
import hashlib
import hmac
import json
from copy import deepcopy
from datetime import UTC, date, datetime
from typing import Any
from urllib.parse import parse_qs

from sqlmodel import Session, select

from app.connectors.freshbooks.client import FreshBooksAPIError, get_freshbooks_client, get_freshbooks_connection_status
from app.connectors.freshbooks.contracts import FreshBooksSyncOperation, FreshBooksSyncResult
from app.models.quote_tables import QuoteCase, QuoteCaseExternalLink
from app.services.heater_quote import list_quote_case_heater_package_lines
from app.services.quote_workflow import (
    get_pipeline_config,
    get_quote_case,
    get_quote_workflow_config,
    get_stage_config,
    list_external_links,
    mark_quote_viewed,
    move_quote_case,
    serialize_quote_case,
)
from app.services.system_settings import get_setting, set_setting
from app.utils.serialization import dumps, loads

FRESHBOOKS_SYNC_SETTING_KEY = 'freshbooks_sync_config'
FRESHBOOKS_WEBHOOK_VERIFIER_KEY = 'freshbooks_webhook_verifier'


# timedelta imported lazily below to keep the file head readable.
from datetime import timedelta  # noqa: E402


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _casefold(value: str | None) -> str:
    return (value or '').strip().casefold()


def _safe_payload_load(blob: str | None) -> dict[str, Any]:
    if not blob:
        return {}
    loaded = loads(blob, {})
    return loaded if isinstance(loaded, dict) else {}


def _split_name(value: str) -> tuple[str, str]:
    cleaned = (value or '').strip()
    if not cleaned:
        return '', ''
    parts = cleaned.split(None, 1)
    if len(parts) == 1:
        return parts[0], ''
    return parts[0], parts[1]


def _string_amount(value: float | int | str) -> str:
    if isinstance(value, str):
        return value
    return f'{float(value):.2f}'


def _get_stage_slug_if_present(pipeline: dict[str, Any], candidate_slug: str) -> str:
    for stage in pipeline.get('stages', []):
        if stage['slug'] == candidate_slug:
            return candidate_slug
    return ''


def _build_default_sync_config(session: Session) -> dict[str, Any]:
    workflow_config = get_quote_workflow_config(session)
    pipelines: list[dict[str, Any]] = []
    for pipeline in workflow_config.get('pipelines', []):
        follow_up_stage_slug = _get_stage_slug_if_present(pipeline, 'follow_up')
        accepted_stage_slug = _get_stage_slug_if_present(pipeline, 'accepted')
        pipelines.append(
            {
                'pipeline_slug': pipeline['slug'],
                'pipeline_name': pipeline['name'],
                'freshbooks_enabled': True,
                'default_currency_code': 'USD',
                'default_terms': '',
                'default_notes': '',
                'follow_up_stage_slug': follow_up_stage_slug,
                'accepted_stage_slug': accepted_stage_slug,
                'auto_move_follow_up_on_sent': bool(follow_up_stage_slug),
                'auto_mark_viewed_from_audit_logs': True,
                'auto_move_accepted_on_acceptance': bool(accepted_stage_slug),
            }
        )
    return {
        'sync_mode': 'dry_run',
        'last_context_refresh_at': None,
        'auto_create_client_if_missing': True,
        'pipelines': pipelines,
    }


def _merge_sync_config(default_config: dict[str, Any], current_config: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(default_config)
    merged.update({key: value for key, value in current_config.items() if key != 'pipelines'})
    current_pipeline_map = {item['pipeline_slug']: item for item in current_config.get('pipelines', [])}
    for pipeline in merged['pipelines']:
        existing = current_pipeline_map.get(pipeline['pipeline_slug'])
        if existing:
            pipeline.update({key: value for key, value in existing.items() if key != 'pipeline_slug'})
    return merged


def ensure_freshbooks_sync_settings(session: Session) -> dict[str, Any]:
    default_config = _build_default_sync_config(session)
    current_config = get_setting(session, FRESHBOOKS_SYNC_SETTING_KEY)
    if not current_config:
        set_setting(
            session,
            FRESHBOOKS_SYNC_SETTING_KEY,
            default_config,
            'Admin editable FreshBooks quote draft sync settings, pipeline level follow up rules, and review-first automation controls.',
        )
        return default_config
    merged = _merge_sync_config(default_config, current_config)
    if merged != current_config:
        set_setting(
            session,
            FRESHBOOKS_SYNC_SETTING_KEY,
            merged,
            'Admin editable FreshBooks quote draft sync settings, pipeline level follow up rules, and review-first automation controls.',
        )
    return merged


def get_freshbooks_sync_settings(session: Session) -> dict[str, Any]:
    return ensure_freshbooks_sync_settings(session)


def get_freshbooks_mapping_summary(session: Session) -> dict[str, Any]:
    config = get_freshbooks_sync_settings(session)
    connection = get_freshbooks_connection_status(config.get('sync_mode', 'dry_run'))
    resolved_account_id = str(config.get('resolved_account_id', '') or '').strip()
    if resolved_account_id:
        connection['effective_account_id'] = resolved_account_id
        connection['has_account_id'] = True
        connection['configured'] = bool(connection['has_access_token'])
        connection['live_write_enabled'] = connection['sync_mode'] == 'live' and bool(connection['has_access_token'])
    estimate_links = list(
        session.exec(
            select(QuoteCaseExternalLink).where(
                QuoteCaseExternalLink.system_slug == 'freshbooks',
                QuoteCaseExternalLink.external_type == 'estimate',
            )
        ).all()
    )
    counts = {
        'draft_prepared_count': 0,
        'sent_estimate_count': 0,
        'viewed_estimate_count': 0,
        'accepted_estimate_count': 0,
        'live_estimate_count': 0,
    }
    for link in estimate_links:
        payload = _safe_payload_load(link.payload_json)
        ui_status = _casefold(payload.get('ui_status') or payload.get('display_status') or payload.get('status_label'))
        if payload.get('placeholder'):
            counts['draft_prepared_count'] += 1
        else:
            counts['live_estimate_count'] += 1
        if ui_status == 'sent':
            counts['sent_estimate_count'] += 1
        if ui_status == 'viewed':
            counts['viewed_estimate_count'] += 1
        if ui_status in {'accepted', 'invoiced'}:
            counts['accepted_estimate_count'] += 1
    return {
        'sync_mode': config.get('sync_mode', 'dry_run'),
        'last_context_refresh_at': config.get('last_context_refresh_at'),
        'pipelines': config.get('pipelines', []),
        'connection': connection,
        **counts,
    }


def refresh_freshbooks_context_from_api(session: Session) -> dict[str, Any]:
    client = get_freshbooks_client()
    if client is None:
        raise ValueError('FreshBooks access token is not configured. Add FRESHBOOKS_ACCESS_TOKEN before refreshing context.')
    config = get_freshbooks_sync_settings(session)
    resolved_account_id = client.account_id or client.resolve_first_account_id()
    updated = deepcopy(config)
    updated['last_context_refresh_at'] = _utcnow().isoformat()
    if resolved_account_id:
        updated['resolved_account_id'] = resolved_account_id
    set_setting(
        session,
        FRESHBOOKS_SYNC_SETTING_KEY,
        updated,
        'Admin editable FreshBooks quote draft sync settings, pipeline level follow up rules, and review-first automation controls.',
    )
    return get_freshbooks_mapping_summary(session)


def _get_pipeline_settings(config: dict[str, Any], pipeline_slug: str) -> dict[str, Any]:
    for pipeline in config.get('pipelines', []):
        if pipeline['pipeline_slug'] == pipeline_slug:
            return pipeline
    raise ValueError(f'No FreshBooks pipeline settings exist for {pipeline_slug}')


def _get_freshbooks_link(session: Session, quote_case_id: int, external_type: str) -> QuoteCaseExternalLink | None:
    return session.exec(
        select(QuoteCaseExternalLink).where(
            QuoteCaseExternalLink.quote_case_id == quote_case_id,
            QuoteCaseExternalLink.system_slug == 'freshbooks',
            QuoteCaseExternalLink.external_type == external_type,
        )
    ).first()


def _upsert_freshbooks_link(
    session: Session,
    *,
    quote_case_id: int,
    external_type: str,
    external_id: str,
    external_label: str = '',
    sync_status: str = 'linked',
    payload: dict[str, Any] | None = None,
    sync_direction: str = 'bidirectional',
) -> QuoteCaseExternalLink:
    link = _get_freshbooks_link(session, quote_case_id, external_type)
    now = _utcnow()
    if not link:
        link = QuoteCaseExternalLink(
            quote_case_id=quote_case_id,
            system_slug='freshbooks',
            external_type=external_type,
            external_id=external_id,
            created_at=now,
        )
        session.add(link)
    link.external_id = external_id
    link.external_label = external_label
    link.sync_status = sync_status
    link.sync_direction = sync_direction
    link.payload_json = dumps(payload or {})
    link.updated_at = now
    session.add(link)
    return link


def link_quote_case_to_freshbooks_client(session: Session, quote_case_id: int, *, client_id: str, client_name: str = '') -> dict[str, Any]:
    case = get_quote_case(session, quote_case_id)
    if not case:
        raise ValueError('Quote case not found')
    link = _upsert_freshbooks_link(
        session,
        quote_case_id=quote_case_id,
        external_type='client',
        external_id=client_id.strip(),
        external_label=client_name.strip(),
        sync_status='linked',
        payload={'client_id': client_id.strip(), 'client_name': client_name.strip()},
    )
    session.commit()
    session.refresh(link)
    return {
        'client_link': link.model_dump(),
        'quote_case': serialize_quote_case(session, case),
    }


def _build_default_estimate_lines(case: QuoteCase, currency_code: str) -> list[dict[str, Any]]:
    description_parts = [part for part in [case.description, f'Quote case {case.quote_number}'] if part]
    return [
        {
            'type': 0,
            'name': case.title,
            'description': ' | '.join(description_parts),
            'qty': 1,
            'unit_cost': {
                'amount': '0.00',
                'code': currency_code,
            },
            'taxName1': '',
            'taxAmount1': 0,
            'taxName2': '',
            'taxAmount2': 0,
        }
    ]


def _normalize_lines(session: Session, lines: list[dict[str, Any]] | None, currency_code: str, case: QuoteCase) -> list[dict[str, Any]]:
    source_lines: list[dict[str, Any]]
    if lines:
        source_lines = lines
    else:
        attached_lines = list_quote_case_heater_package_lines(session, case.id)
        source_lines = attached_lines if attached_lines else _build_default_estimate_lines(case, currency_code)
    normalized: list[dict[str, Any]] = []
    for item in source_lines:
        amount_code = item.get('code') or item.get('currency_code') or currency_code
        unit_cost = item.get('unit_cost', item.get('unit_amount', item.get('amount', '0.00')))
        if isinstance(unit_cost, dict):
            amount = unit_cost.get('amount', '0.00')
            code = unit_cost.get('code', amount_code)
        else:
            amount = unit_cost
            code = amount_code
        normalized.append(
            {
                'type': int(item.get('type', 0)),
                'name': item.get('name', case.title),
                'description': item.get('description', ''),
                'qty': float(item.get('qty', 1)),
                'unit_cost': {
                    'amount': _string_amount(amount),
                    'code': str(code or currency_code),
                },
                'taxName1': item.get('taxName1', ''),
                'taxAmount1': item.get('taxAmount1', 0),
                'taxName2': item.get('taxName2', ''),
                'taxAmount2': item.get('taxAmount2', 0),
            }
        )
    return normalized


def _build_client_payload(case: QuoteCase, organization: str = '', currency_code: str = 'USD') -> dict[str, Any]:
    fname, lname = _split_name(case.requester_name)
    return {
        'fname': fname,
        'lname': lname,
        'email': case.requester_email or None,
        'organization': organization or None,
        'note': case.description or None,
        'mob_phone': case.requester_phone or None,
        'currency_code': currency_code,
        'language': 'en',
    }


def _build_estimate_payload(
    case: QuoteCase,
    *,
    client_id: str,
    currency_code: str,
    lines: list[dict[str, Any]],
    terms: str,
    notes: str,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        'customerid': int(client_id) if str(client_id).isdigit() else client_id,
        'create_date': date.today().isoformat(),
        'currency_code': currency_code,
        'terms': terms,
        'notes': notes,
        'lines': lines,
    }
    if case.requester_email:
        payload['email'] = case.requester_email
    return payload


def _status_labels_from_estimate(estimate: dict[str, Any]) -> tuple[str, str]:
    ui_status = _casefold(estimate.get('ui_status') or estimate.get('display_status'))
    status_code = int(estimate.get('status', 0) or 0)
    if not ui_status:
        mapping = {
            1: 'draft',
            2: 'sent',
            3: 'viewed',
            4: 'replied',
            5: 'accepted',
            6: 'invoiced',
        }
        ui_status = mapping.get(status_code, 'unknown')
    return str(status_code), ui_status


def get_case_freshbooks_summary(session: Session, quote_case_id: int) -> dict[str, Any]:
    case = get_quote_case(session, quote_case_id)
    if not case:
        raise ValueError('Quote case not found')
    config = get_freshbooks_sync_settings(session)
    connection = get_freshbooks_mapping_summary(session)['connection']
    pipeline_settings = _get_pipeline_settings(config, case.pipeline_slug)
    client_link = _get_freshbooks_link(session, quote_case_id, 'client')
    estimate_link = _get_freshbooks_link(session, quote_case_id, 'estimate')
    blockers: list[str] = []
    if not case.requester_email and not client_link:
        blockers.append('Add a requester email or manually link a FreshBooks client before live draft creation.')
    if not pipeline_settings.get('freshbooks_enabled', True):
        blockers.append('FreshBooks sync is disabled for this pipeline in the local config.')
    local_payload = _safe_payload_load(estimate_link.payload_json if estimate_link else '')
    return {
        'quote_case_id': quote_case_id,
        'connection': connection,
        'pipeline_settings': pipeline_settings,
        'client_link': client_link.model_dump() if client_link else None,
        'estimate_link': estimate_link.model_dump() if estimate_link else None,
        'local_estimate_state': {
            'status_code': local_payload.get('status_code', ''),
            'ui_status': local_payload.get('ui_status', ''),
            'prepared_at': local_payload.get('prepared_at'),
            'sent_at': local_payload.get('sent_at'),
            'viewed_at': local_payload.get('viewed_at'),
        },
        'blockers': blockers,
    }


def sync_quote_case_to_freshbooks(
    session: Session,
    quote_case_id: int,
    *,
    lines: list[dict[str, Any]] | None = None,
    note: str = '',
    force_live: bool = False,
    create_client_if_missing: bool = True,
    currency_code: str = 'USD',
    terms: str = '',
    notes: str = '',
    organization: str = '',
) -> dict[str, Any]:
    case = get_quote_case(session, quote_case_id)
    if not case:
        raise ValueError('Quote case not found')

    config = get_freshbooks_sync_settings(session)
    pipeline_settings = _get_pipeline_settings(config, case.pipeline_slug)
    if not pipeline_settings.get('freshbooks_enabled', True):
        raise ValueError('FreshBooks sync is disabled for this pipeline.')

    resolved_currency_code = (currency_code or pipeline_settings.get('default_currency_code') or 'USD').strip() or 'USD'
    resolved_terms = terms if terms != '' else str(pipeline_settings.get('default_terms', ''))
    resolved_notes = notes if notes != '' else str(pipeline_settings.get('default_notes', ''))
    normalized_lines = _normalize_lines(session, lines, resolved_currency_code, case)

    client_link = _get_freshbooks_link(session, quote_case_id, 'client')
    estimate_link = _get_freshbooks_link(session, quote_case_id, 'estimate')

    operations: list[FreshBooksSyncOperation] = []
    client_payload = _build_client_payload(case, organization=organization, currency_code=resolved_currency_code)
    client_id = client_link.external_id if client_link else ''
    if not client_id and create_client_if_missing:
        if case.requester_email:
            operations.append(
                FreshBooksSyncOperation(
                    method='GET',
                    path='/accounting/account/<accountId>/users/clients?search[email]=...',
                    summary='Look for an existing FreshBooks client by exact requester email before creating a new client.',
                    payload={'email': case.requester_email},
                )
            )
        operations.append(
            FreshBooksSyncOperation(
                method='POST',
                path='/accounting/account/<accountId>/users/clients',
                summary='Create a FreshBooks client record if a matching client is not already linked.',
                payload={'client': client_payload},
            )
        )
    estimate_payload = _build_estimate_payload(
        case,
        client_id=client_id or 'pending-client',
        currency_code=resolved_currency_code,
        lines=normalized_lines,
        terms=resolved_terms,
        notes=resolved_notes or note,
    )
    if estimate_link and not _safe_payload_load(estimate_link.payload_json).get('placeholder', False):
        operations.append(
            FreshBooksSyncOperation(
                method='PUT',
                path=f"/accounting/account/<accountId>/estimates/estimates/{estimate_link.external_id}",
                summary='Update the existing FreshBooks estimate draft for this quote case.',
                payload={'estimate': estimate_payload},
            )
        )
    else:
        operations.append(
            FreshBooksSyncOperation(
                method='POST',
                path='/accounting/account/<accountId>/estimates/estimates',
                summary='Create a FreshBooks estimate draft for review before it is sent to the client.',
                payload={'estimate': estimate_payload},
            )
        )

    live_mode_requested = force_live and config.get('sync_mode', 'dry_run') == 'live'
    client = get_freshbooks_client()
    if client is not None and not client.account_id and config.get('resolved_account_id'):
        client.account_id = str(config.get('resolved_account_id'))
    if not live_mode_requested or client is None or not client.account_id:
        prepared_payload = {
            'placeholder': True,
            'ui_status': 'draft',
            'status_code': '1',
            'prepared_at': _utcnow().isoformat(),
            'note': note,
            'estimate': estimate_payload,
            'client': client_payload,
        }
        _upsert_freshbooks_link(
            session,
            quote_case_id=quote_case_id,
            external_type='estimate',
            external_id=estimate_link.external_id if estimate_link else f'pending-draft-{quote_case_id}',
            external_label='FreshBooks draft prepared locally',
            sync_status='draft_prepared',
            payload=prepared_payload,
            sync_direction='outbound',
        )
        case.freshbooks_status = 'draft'
        case.updated_at = _utcnow()
        session.add(case)
        session.commit()
        session.refresh(case)
        return FreshBooksSyncResult(
            mode='dry_run',
            sync_status='draft_prepared',
            message='FreshBooks draft was prepared locally. Live draft creation will run after OAuth token and account id are configured and live mode is enabled.',
            operations=operations,
            external_links=[item.model_dump() for item in list_external_links(session, quote_case_id)],
            quote_case=serialize_quote_case(session, case),
            freshbooks_summary=get_case_freshbooks_summary(session, quote_case_id),
        ).to_dict()

    try:
        if not client_id and create_client_if_missing:
            existing_clients = client.list_clients(email=case.requester_email or None, organization=organization or None)
            if existing_clients:
                matched = existing_clients[0]
                client_id = str(matched.get('id', '') or matched.get('customerid', '')).strip()
                _upsert_freshbooks_link(
                    session,
                    quote_case_id=quote_case_id,
                    external_type='client',
                    external_id=client_id,
                    external_label=matched.get('organization') or f"{matched.get('fname', '')} {matched.get('lname', '')}".strip(),
                    sync_status='linked',
                    payload=matched,
                )
            else:
                created_client = client.create_client(client_payload)
                client_id = str(created_client.get('id', '') or created_client.get('customerid', '')).strip()
                _upsert_freshbooks_link(
                    session,
                    quote_case_id=quote_case_id,
                    external_type='client',
                    external_id=client_id,
                    external_label=created_client.get('organization') or f"{created_client.get('fname', '')} {created_client.get('lname', '')}".strip(),
                    sync_status='linked',
                    payload=created_client,
                )
        if not client_id:
            raise ValueError('FreshBooks client id is required before creating a live estimate draft.')

        estimate_payload = _build_estimate_payload(
            case,
            client_id=client_id,
            currency_code=resolved_currency_code,
            lines=normalized_lines,
            terms=resolved_terms,
            notes=resolved_notes or note,
        )
        if estimate_link and estimate_link.external_id and not _safe_payload_load(estimate_link.payload_json).get('placeholder', False):
            estimate = client.update_estimate(estimate_link.external_id, estimate_payload)
        else:
            estimate = client.create_estimate(estimate_payload)
        estimate_id = str(estimate.get('id', '') or estimate.get('estimateid', '')).strip()
        status_code, ui_status = _status_labels_from_estimate(estimate)
        _upsert_freshbooks_link(
            session,
            quote_case_id=quote_case_id,
            external_type='estimate',
            external_id=estimate_id,
            external_label=estimate.get('estimate_number', 'FreshBooks estimate draft'),
            sync_status='linked',
            payload={
                **estimate,
                'placeholder': False,
                'status_code': status_code,
                'ui_status': ui_status,
                'prepared_at': _utcnow().isoformat(),
            },
        )
        case.freshbooks_status = ui_status or 'draft'
        case.updated_at = _utcnow()
        session.add(case)
        session.commit()
        session.refresh(case)
        return FreshBooksSyncResult(
            mode='live',
            sync_status='draft_created',
            message='FreshBooks estimate draft created or updated successfully.',
            operations=operations,
            external_links=[item.model_dump() for item in list_external_links(session, quote_case_id)],
            quote_case=serialize_quote_case(session, case),
            freshbooks_summary=get_case_freshbooks_summary(session, quote_case_id),
        ).to_dict()
    except FreshBooksAPIError as exc:
        return FreshBooksSyncResult(
            mode='live',
            sync_status='sync_failed',
            message=f'FreshBooks draft sync failed: {exc}',
            operations=operations,
            external_links=[item.model_dump() for item in list_external_links(session, quote_case_id)],
            quote_case=serialize_quote_case(session, case),
            freshbooks_summary=get_case_freshbooks_summary(session, quote_case_id),
        ).to_dict()


def mark_quote_case_freshbooks_sent(session: Session, quote_case_id: int, *, sent_at: datetime | None = None, move_to_follow_up: bool = True) -> dict[str, Any]:
    case = get_quote_case(session, quote_case_id)
    if not case:
        raise ValueError('Quote case not found')
    estimate_link = _get_freshbooks_link(session, quote_case_id, 'estimate')
    if not estimate_link:
        raise ValueError('No FreshBooks estimate is linked to this quote case yet.')
    payload = _safe_payload_load(estimate_link.payload_json)
    payload['ui_status'] = 'sent'
    payload['status_code'] = '2'
    payload['sent_at'] = (sent_at or _utcnow()).isoformat()
    payload['placeholder'] = payload.get('placeholder', True)
    estimate_link.sync_status = 'sent'
    estimate_link.payload_json = dumps(payload)
    estimate_link.updated_at = _utcnow()
    session.add(estimate_link)
    case.freshbooks_status = 'sent'
    case.updated_at = _utcnow()
    session.add(case)

    config = get_freshbooks_sync_settings(session)
    pipeline_settings = _get_pipeline_settings(config, case.pipeline_slug)
    target_stage_slug = pipeline_settings.get('follow_up_stage_slug', '')
    if move_to_follow_up and target_stage_slug and case.stage_slug != target_stage_slug:
        move_quote_case(
            session,
            quote_case_id,
            target_stage_slug=target_stage_slug,
            moved_by='freshbooks_manual',
            move_reason='FreshBooks estimate was marked sent and moved to follow up.',
        )
        case = get_quote_case(session, quote_case_id)
        case.freshbooks_status = 'sent'
        session.add(case)
    session.commit()
    session.refresh(case)
    return {
        'quote_case': serialize_quote_case(session, case),
        'freshbooks_summary': get_case_freshbooks_summary(session, quote_case_id),
    }


def refresh_quote_case_from_freshbooks(session: Session, quote_case_id: int, *, force_live: bool = False) -> dict[str, Any]:
    case = get_quote_case(session, quote_case_id)
    if not case:
        raise ValueError('Quote case not found')
    estimate_link = _get_freshbooks_link(session, quote_case_id, 'estimate')
    if not estimate_link:
        raise ValueError('No FreshBooks estimate is linked to this quote case yet.')
    payload = _safe_payload_load(estimate_link.payload_json)
    if payload.get('placeholder') and not force_live:
        return {
            'quote_case': serialize_quote_case(session, case),
            'freshbooks_summary': get_case_freshbooks_summary(session, quote_case_id),
            'message': 'The FreshBooks draft is only prepared locally right now. Run live refresh after a real estimate id exists.',
        }

    config = get_freshbooks_sync_settings(session)
    client = get_freshbooks_client()
    if client is not None and not client.account_id and config.get('resolved_account_id'):
        client.account_id = str(config.get('resolved_account_id'))
    if client is None or not client.account_id:
        raise ValueError('FreshBooks access token and account id are required for live status refresh.')

    estimate = client.get_estimate(estimate_link.external_id, includes=['audit_logs', 'lines'])
    status_code, ui_status = _status_labels_from_estimate(estimate)
    payload = {
        **estimate,
        'placeholder': False,
        'status_code': status_code,
        'ui_status': ui_status,
        'refreshed_at': _utcnow().isoformat(),
    }
    estimate_link.payload_json = dumps(payload)
    estimate_link.sync_status = 'linked'
    estimate_link.updated_at = _utcnow()
    session.add(estimate_link)

    case.freshbooks_status = ui_status or case.freshbooks_status
    case.updated_at = _utcnow()
    session.add(case)

    config = get_freshbooks_sync_settings(session)
    pipeline_settings = _get_pipeline_settings(config, case.pipeline_slug)

    if ui_status == 'viewed':
        mark_quote_viewed(session, quote_case_id, _utcnow())
        case = get_quote_case(session, quote_case_id)
        case.freshbooks_status = 'viewed'
        session.add(case)
    if ui_status in {'sent', 'viewed'} and pipeline_settings.get('auto_move_follow_up_on_sent'):
        target_stage_slug = pipeline_settings.get('follow_up_stage_slug', '')
        if target_stage_slug and case.stage_slug != target_stage_slug:
            move_quote_case(
                session,
                quote_case_id,
                target_stage_slug=target_stage_slug,
                moved_by='freshbooks_refresh',
                move_reason='FreshBooks estimate status indicates the quote has been sent to the client.',
            )
            case = get_quote_case(session, quote_case_id)
            case.freshbooks_status = ui_status
            session.add(case)
    if ui_status in {'accepted', 'invoiced'} and pipeline_settings.get('auto_move_accepted_on_acceptance'):
        target_stage_slug = pipeline_settings.get('accepted_stage_slug', '')
        if target_stage_slug and case.stage_slug != target_stage_slug:
            move_quote_case(
                session,
                quote_case_id,
                target_stage_slug=target_stage_slug,
                moved_by='freshbooks_refresh',
                move_reason='FreshBooks estimate status indicates the client accepted the estimate.',
            )
            case = get_quote_case(session, quote_case_id)
            case.freshbooks_status = ui_status
            session.add(case)
    session.commit()
    session.refresh(case)
    return {
        'quote_case': serialize_quote_case(session, case),
        'freshbooks_summary': get_case_freshbooks_summary(session, quote_case_id),
        'message': f'FreshBooks estimate status refreshed to {ui_status}.',
    }


def reconcile_freshbooks_payload(session: Session, payload: dict[str, Any]) -> dict[str, Any]:
    event_name = payload.get('name') or payload.get('event') or 'manual'
    object_id = str(payload.get('object_id') or payload.get('estimate_id') or '').strip()
    updated_case_ids: list[int] = []
    if object_id:
        link = session.exec(
            select(QuoteCaseExternalLink).where(
                QuoteCaseExternalLink.system_slug == 'freshbooks',
                QuoteCaseExternalLink.external_type == 'estimate',
                QuoteCaseExternalLink.external_id == object_id,
            )
        ).first()
        if link:
            payload_blob = _safe_payload_load(link.payload_json)
            payload_blob['last_webhook'] = payload
            link.payload_json = dumps(payload_blob)
            link.updated_at = _utcnow()
            session.add(link)
            case = session.get(QuoteCase, link.quote_case_id)
            if case:
                if event_name == 'estimate.sendByEmail':
                    case.freshbooks_status = 'sent'
                    session.add(case)
                updated_case_ids.append(case.id)
    session.commit()
    return {
        'triggering_event': event_name,
        'updated_case_ids': sorted(set(updated_case_ids)),
        'object_id': object_id,
    }


def store_freshbooks_webhook_verifier(session: Session, verifier: str) -> None:
    set_setting(session, FRESHBOOKS_WEBHOOK_VERIFIER_KEY, verifier, 'Verification code originally sent by FreshBooks when registering the webhook callback.')


def get_freshbooks_webhook_verifier(session: Session) -> str:
    return str(get_setting(session, FRESHBOOKS_WEBHOOK_VERIFIER_KEY) or '')


def verify_freshbooks_webhook_signature(session: Session, form_payload: dict[str, Any], signature: str | None) -> bool:
    verifier = get_freshbooks_webhook_verifier(session)
    if not verifier or not signature:
        return False
    serialized = json.dumps({key: str(value) for key, value in form_payload.items()}).encode('utf-8')
    calculated = base64.b64encode(hmac.new(verifier.encode('utf-8'), serialized, hashlib.sha256).digest()).decode('utf-8')
    return hmac.compare_digest(calculated, signature)
