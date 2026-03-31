from __future__ import annotations

import hashlib
import hmac
import json
from copy import deepcopy
from datetime import UTC, date, datetime
from typing import Any

from sqlmodel import Session, select

from app.connectors.lacrm.client import LACRMAPIError, get_lacrm_client, get_lacrm_connection_status
from app.connectors.lacrm.contracts import LACRMSyncOperation, LACRMSyncResult
from app.models.quote_tables import QuoteCase, QuoteCaseExternalLink, QuoteStageHistory
from app.services.quote_workflow import (
    get_pipeline_config,
    get_quote_case,
    get_quote_workflow_config,
    get_stage_config,
    list_external_links,
    serialize_quote_case,
)
from app.services.system_settings import get_setting, set_setting
from app.utils.serialization import dumps, loads

LACRM_SYNC_SETTING_KEY = 'lacrm_sync_config'
LACRM_WEBHOOK_SECRET_KEY = 'lacrm_webhook_secret'


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _casefold(value: str | None) -> str:
    return (value or '').strip().casefold()


def _build_default_sync_config(session: Session) -> dict[str, Any]:
    workflow = get_quote_workflow_config(session)
    pipelines: list[dict[str, Any]] = []
    for pipeline in workflow.get('pipelines', []):
        pipeline_row = {
            'pipeline_slug': pipeline['slug'],
            'pipeline_name': pipeline['name'],
            'lacrm_pipeline_name': pipeline.get('lacrm_pipeline_name', pipeline['name']),
            'lacrm_pipeline_id': '',
            'stages': [],
        }
        for stage in pipeline.get('stages', []):
            pipeline_row['stages'].append(
                {
                    'stage_slug': stage['slug'],
                    'stage_name': stage['name'],
                    'lacrm_stage_name': stage.get('lacrm_stage_name', stage['name']),
                    'lacrm_status_id': '',
                }
            )
        pipelines.append(pipeline_row)
    return {
        'version': 'platform_integration_block_1b',
        'sync_mode': 'dry_run',
        'auto_create_follow_up_tasks': True,
        'last_mapping_refresh_at': None,
        'pipelines': pipelines,
    }


def _merge_sync_config(default_config: dict[str, Any], existing_config: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(default_config)
    merged['sync_mode'] = existing_config.get('sync_mode', merged['sync_mode'])
    merged['auto_create_follow_up_tasks'] = existing_config.get('auto_create_follow_up_tasks', merged['auto_create_follow_up_tasks'])
    merged['last_mapping_refresh_at'] = existing_config.get('last_mapping_refresh_at')

    existing_pipelines = {item['pipeline_slug']: item for item in existing_config.get('pipelines', [])}
    for pipeline in merged.get('pipelines', []):
        existing_pipeline = existing_pipelines.get(pipeline['pipeline_slug'])
        if not existing_pipeline:
            continue
        pipeline['lacrm_pipeline_name'] = existing_pipeline.get('lacrm_pipeline_name', pipeline['lacrm_pipeline_name'])
        pipeline['lacrm_pipeline_id'] = existing_pipeline.get('lacrm_pipeline_id', pipeline['lacrm_pipeline_id'])
        existing_stages = {stage['stage_slug']: stage for stage in existing_pipeline.get('stages', [])}
        for stage in pipeline.get('stages', []):
            existing_stage = existing_stages.get(stage['stage_slug'])
            if not existing_stage:
                continue
            stage['lacrm_stage_name'] = existing_stage.get('lacrm_stage_name', stage['lacrm_stage_name'])
            stage['lacrm_status_id'] = existing_stage.get('lacrm_status_id', stage['lacrm_status_id'])
    return merged


def ensure_lacrm_sync_settings(session: Session) -> dict[str, Any]:
    default_config = _build_default_sync_config(session)
    current_config = get_setting(session, LACRM_SYNC_SETTING_KEY)
    if not current_config:
        set_setting(
            session,
            LACRM_SYNC_SETTING_KEY,
            default_config,
            'Admin editable LACRM sync map for quote workflow stage alignment, dry run safety, and task orchestration.',
        )
        return default_config
    merged = _merge_sync_config(default_config, current_config)
    if merged != current_config:
        set_setting(
            session,
            LACRM_SYNC_SETTING_KEY,
            merged,
            'Admin editable LACRM sync map for quote workflow stage alignment, dry run safety, and task orchestration.',
        )
    return merged


def get_lacrm_sync_settings(session: Session) -> dict[str, Any]:
    return ensure_lacrm_sync_settings(session)


def get_lacrm_mapping_summary(session: Session) -> dict[str, Any]:
    config = get_lacrm_sync_settings(session)
    mapped_stage_count = 0
    total_stage_count = 0
    mapped_pipeline_count = 0
    pipeline_rows: list[dict[str, Any]] = []
    for pipeline in config.get('pipelines', []):
        stage_rows: list[dict[str, Any]] = []
        if pipeline.get('lacrm_pipeline_id'):
            mapped_pipeline_count += 1
        for stage in pipeline.get('stages', []):
            total_stage_count += 1
            is_mapped = bool(pipeline.get('lacrm_pipeline_id') and stage.get('lacrm_status_id'))
            if is_mapped:
                mapped_stage_count += 1
            stage_rows.append(
                {
                    'stage_slug': stage['stage_slug'],
                    'stage_name': stage['stage_name'],
                    'lacrm_stage_name': stage['lacrm_stage_name'],
                    'lacrm_status_id': stage.get('lacrm_status_id', ''),
                    'is_mapped': is_mapped,
                }
            )
        pipeline_rows.append(
            {
                'pipeline_slug': pipeline['pipeline_slug'],
                'pipeline_name': pipeline['pipeline_name'],
                'lacrm_pipeline_name': pipeline['lacrm_pipeline_name'],
                'lacrm_pipeline_id': pipeline.get('lacrm_pipeline_id', ''),
                'mapped_stage_count': sum(1 for row in stage_rows if row['is_mapped']),
                'total_stage_count': len(stage_rows),
                'stages': stage_rows,
            }
        )
    summary = {
        'sync_mode': config.get('sync_mode', 'dry_run'),
        'auto_create_follow_up_tasks': bool(config.get('auto_create_follow_up_tasks', True)),
        'last_mapping_refresh_at': config.get('last_mapping_refresh_at'),
        'mapped_pipeline_count': mapped_pipeline_count,
        'total_pipeline_count': len(config.get('pipelines', [])),
        'mapped_stage_count': mapped_stage_count,
        'total_stage_count': total_stage_count,
        'pipelines': pipeline_rows,
        'connection': get_lacrm_connection_status(config.get('sync_mode', 'dry_run')),
    }
    return summary


def refresh_lacrm_mapping_from_api(session: Session) -> dict[str, Any]:
    client = get_lacrm_client()
    if client is None:
        raise ValueError('LACRM API key is not configured. Add LACRM_API_KEY before refreshing live mappings.')
    config = get_lacrm_sync_settings(session)
    live_pipelines = client.get_pipelines(include_archived_pipelines=False, include_custom_fields=False, include_hidden_pipelines=False)
    live_by_name = {_casefold(item.get('Name')): item for item in live_pipelines}

    updated = deepcopy(config)
    for pipeline in updated.get('pipelines', []):
        live_pipeline = live_by_name.get(_casefold(pipeline.get('lacrm_pipeline_name')))
        pipeline['lacrm_pipeline_id'] = str(live_pipeline.get('PipelineId', '')) if live_pipeline else ''
        live_statuses = live_pipeline.get('Statuses', []) if live_pipeline else []
        live_status_by_name = {_casefold(item.get('Name')): item for item in live_statuses}
        for stage in pipeline.get('stages', []):
            live_status = live_status_by_name.get(_casefold(stage.get('lacrm_stage_name')))
            stage['lacrm_status_id'] = str(live_status.get('StatusId', '')) if live_status else ''

    updated['last_mapping_refresh_at'] = _utcnow().isoformat()
    set_setting(
        session,
        LACRM_SYNC_SETTING_KEY,
        updated,
        'Admin editable LACRM sync map for quote workflow stage alignment, dry run safety, and task orchestration.',
    )
    return get_lacrm_mapping_summary(session)


def _get_mapping_for_case(config: dict[str, Any], case: QuoteCase) -> tuple[dict[str, Any], dict[str, Any]]:
    for pipeline in config.get('pipelines', []):
        if pipeline['pipeline_slug'] != case.pipeline_slug:
            continue
        for stage in pipeline.get('stages', []):
            if stage['stage_slug'] == case.stage_slug:
                return pipeline, stage
        raise ValueError(f'No LACRM stage mapping exists for {case.pipeline_slug}:{case.stage_slug}')
    raise ValueError(f'No LACRM pipeline mapping exists for {case.pipeline_slug}')


def _find_reverse_mapping(config: dict[str, Any], pipeline_id: str, status_id: str) -> tuple[dict[str, Any], dict[str, Any]] | None:
    for pipeline in config.get('pipelines', []):
        if str(pipeline.get('lacrm_pipeline_id', '')) != str(pipeline_id):
            continue
        for stage in pipeline.get('stages', []):
            if str(stage.get('lacrm_status_id', '')) == str(status_id):
                return pipeline, stage
    return None


def _get_lacrm_link(session: Session, quote_case_id: int, external_type: str) -> QuoteCaseExternalLink | None:
    return session.exec(
        select(QuoteCaseExternalLink).where(
            QuoteCaseExternalLink.quote_case_id == quote_case_id,
            QuoteCaseExternalLink.system_slug == 'lacrm',
            QuoteCaseExternalLink.external_type == external_type,
        )
    ).first()


def _upsert_lacrm_link(
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
    link = _get_lacrm_link(session, quote_case_id, external_type)
    now = _utcnow()
    if not link:
        link = QuoteCaseExternalLink(
            quote_case_id=quote_case_id,
            system_slug='lacrm',
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


def _update_case_sync_state(session: Session, case: QuoteCase, *, sync_status: str, sync_notes: str, mark_synced: bool = False) -> None:
    now = _utcnow()
    case.sync_status = sync_status
    case.sync_notes = sync_notes
    case.updated_at = now
    if mark_synced:
        case.last_synced_at = now
    session.add(case)


def link_quote_case_to_lacrm_contact(session: Session, quote_case_id: int, *, contact_id: str, contact_name: str = '') -> dict[str, Any]:
    case = get_quote_case(session, quote_case_id)
    if not case:
        raise ValueError('Quote case not found')
    link = _upsert_lacrm_link(
        session,
        quote_case_id=quote_case_id,
        external_type='contact',
        external_id=contact_id.strip(),
        external_label=contact_name.strip(),
        sync_status='linked',
        payload={'contact_id': contact_id.strip(), 'contact_name': contact_name.strip()},
    )
    _update_case_sync_state(
        session,
        case,
        sync_status='pending_sync',
        sync_notes='LACRM contact linked locally. Prepare sync to create or update the matching pipeline item.',
        mark_synced=False,
    )
    session.commit()
    session.refresh(link)
    session.refresh(case)
    return {
        'contact_link': link.model_dump(),
        'quote_case': serialize_quote_case(session, case),
    }


def get_case_lacrm_summary(session: Session, quote_case_id: int) -> dict[str, Any]:
    case = get_quote_case(session, quote_case_id)
    if not case:
        raise ValueError('Quote case not found')
    contact_link = _get_lacrm_link(session, quote_case_id, 'contact')
    pipeline_link = _get_lacrm_link(session, quote_case_id, 'pipeline_item')
    task_link = _get_lacrm_link(session, quote_case_id, 'follow_up_task')
    mapping_config = get_lacrm_sync_settings(session)
    pipeline_mapping, stage_mapping = _get_mapping_for_case(mapping_config, case)
    blockers: list[str] = []
    if not contact_link:
        blockers.append('Link the matching LACRM contact id before syncing this case.')
    if not pipeline_mapping.get('lacrm_pipeline_id'):
        blockers.append('The internal pipeline is not mapped to an LACRM pipeline id yet.')
    if not stage_mapping.get('lacrm_status_id'):
        blockers.append('The current stage is not mapped to an LACRM status id yet.')
    return {
        'quote_case_id': quote_case_id,
        'connection': get_lacrm_connection_status(mapping_config.get('sync_mode', 'dry_run')),
        'pipeline_mapping': pipeline_mapping,
        'stage_mapping': stage_mapping,
        'contact_link': contact_link.model_dump() if contact_link else None,
        'pipeline_item_link': pipeline_link.model_dump() if pipeline_link else None,
        'follow_up_task_link': task_link.model_dump() if task_link else None,
        'blockers': blockers,
        'quote_case': serialize_quote_case(session, case),
    }


def _sync_task_needed(case: QuoteCase, sync_config: dict[str, Any]) -> bool:
    return bool(sync_config.get('auto_create_follow_up_tasks', True) and case.follow_up_due_on is not None)


def _build_pipeline_operation(case: QuoteCase, contact_link: QuoteCaseExternalLink, pipeline_mapping: dict[str, Any], stage_mapping: dict[str, Any], pipeline_item_link: QuoteCaseExternalLink | None, note: str) -> LACRMSyncOperation:
    summary = f'{case.quote_number} -> {pipeline_mapping["lacrm_pipeline_name"]} / {stage_mapping["lacrm_stage_name"]}'
    if pipeline_item_link and pipeline_item_link.external_id and not pipeline_item_link.external_id.startswith('dryrun:'):
        return LACRMSyncOperation(
            function='EditPipelineItem',
            parameters={
                'PipelineItemId': pipeline_item_link.external_id,
                'StatusId': stage_mapping['lacrm_status_id'],
                'Note': note,
                'RunStatusAutomation': False,
            },
            summary=f'Update pipeline item for {summary}',
        )
    return LACRMSyncOperation(
        function='CreatePipelineItem',
        parameters={
            'ContactId': contact_link.external_id,
            'PipelineId': pipeline_mapping['lacrm_pipeline_id'],
            'StatusId': stage_mapping['lacrm_status_id'],
            'Note': note,
            'RunStatusAutomation': False,
        },
        summary=f'Create pipeline item for {summary}',
    )


def _build_task_operation(case: QuoteCase, contact_link: QuoteCaseExternalLink, task_link: QuoteCaseExternalLink | None) -> LACRMSyncOperation:
    description = '\n'.join(
        [
            f'Quote case: {case.quote_number}',
            f'Title: {case.title}',
            f'Current stage: {case.stage_slug}',
            f'Requester: {case.requester_name or "Unknown"}',
            f'Phone: {case.requester_phone or "Not set"}',
        ]
    )
    parameters = {
        'Name': f'Follow up {case.quote_number}',
        'DueDate': case.follow_up_due_on.isoformat() if isinstance(case.follow_up_due_on, date) else None,
        'Description': description,
        'ContactId': contact_link.external_id,
    }
    if task_link and task_link.external_id and not task_link.external_id.startswith('dryrun:'):
        parameters['TaskId'] = task_link.external_id
        return LACRMSyncOperation(
            function='EditTask',
            parameters=parameters,
            summary=f'Update follow up task for {case.quote_number}',
        )
    return LACRMSyncOperation(
        function='CreateTask',
        parameters=parameters,
        summary=f'Create follow up task for {case.quote_number}',
    )


def sync_quote_case_to_lacrm(
    session: Session,
    quote_case_id: int,
    *,
    note: str = '',
    force_live: bool = False,
    create_follow_up_task: bool = True,
) -> dict[str, Any]:
    case = get_quote_case(session, quote_case_id)
    if not case:
        raise ValueError('Quote case not found')
    sync_config = get_lacrm_sync_settings(session)
    pipeline_mapping, stage_mapping = _get_mapping_for_case(sync_config, case)
    contact_link = _get_lacrm_link(session, quote_case_id, 'contact')
    pipeline_item_link = _get_lacrm_link(session, quote_case_id, 'pipeline_item')
    follow_up_task_link = _get_lacrm_link(session, quote_case_id, 'follow_up_task')

    blockers: list[str] = []
    if not contact_link:
        blockers.append('No LACRM contact link is stored on this quote case yet.')
    if not pipeline_mapping.get('lacrm_pipeline_id'):
        blockers.append('The selected pipeline is not mapped to an LACRM pipeline id yet.')
    if not stage_mapping.get('lacrm_status_id'):
        blockers.append('The current stage is not mapped to an LACRM status id yet.')

    if blockers:
        next_status = 'pending_contact_link' if not contact_link else 'pending_mapping'
        _update_case_sync_state(session, case, sync_status=next_status, sync_notes=' '.join(blockers), mark_synced=False)
        session.commit()
        session.refresh(case)
        return LACRMSyncResult(
            mode='blocked',
            sync_status=case.sync_status,
            message='Sync could not be prepared until the missing links and mappings are filled in.',
            operations=[],
            external_links=[item.model_dump() for item in list_external_links(session, quote_case_id)],
            quote_case=serialize_quote_case(session, case),
        ).to_dict()

    sync_note = note.strip() or f'Synced from platform quote case {case.quote_number}'
    operations = [_build_pipeline_operation(case, contact_link, pipeline_mapping, stage_mapping, pipeline_item_link, sync_note)]
    task_needed = bool(create_follow_up_task and _sync_task_needed(case, sync_config))
    if task_needed:
        operations.append(_build_task_operation(case, contact_link, follow_up_task_link))

    live_requested = force_live or sync_config.get('sync_mode') == 'live'
    client = get_lacrm_client() if live_requested else None
    if client is None:
        pipeline_external_id = pipeline_item_link.external_id if pipeline_item_link and not pipeline_item_link.external_id.startswith('dryrun:') else f'dryrun:pipeline_item:{quote_case_id}'
        pipeline_link = _upsert_lacrm_link(
            session,
            quote_case_id=quote_case_id,
            external_type='pipeline_item',
            external_id=pipeline_external_id,
            external_label=pipeline_mapping['lacrm_pipeline_name'],
            sync_status='dry_run_ready',
            payload=operations[0].to_dict(),
        )
        if task_needed:
            task_external_id = follow_up_task_link.external_id if follow_up_task_link and not follow_up_task_link.external_id.startswith('dryrun:') else f'dryrun:follow_up_task:{quote_case_id}'
            _upsert_lacrm_link(
                session,
                quote_case_id=quote_case_id,
                external_type='follow_up_task',
                external_id=task_external_id,
                external_label='Quote follow up task',
                sync_status='dry_run_ready',
                payload=operations[1].to_dict(),
            )
        message = 'Dry run sync was prepared. No live LACRM write was sent.'
        if live_requested:
            message = 'Live sync was requested, but no LACRM API key was found. Dry run instructions were saved instead.'
        _update_case_sync_state(session, case, sync_status='dry_run_ready', sync_notes=message, mark_synced=True)
        session.commit()
        session.refresh(case)
        session.refresh(pipeline_link)
        return LACRMSyncResult(
            mode='dry_run',
            sync_status='dry_run_ready',
            message=message,
            operations=operations,
            external_links=[item.model_dump() for item in list_external_links(session, quote_case_id)],
            quote_case=serialize_quote_case(session, case),
        ).to_dict()

    try:
        pipeline_response: dict[str, Any]
        if operations[0].function == 'CreatePipelineItem':
            pipeline_response = client.create_pipeline_item(
                contact_id=operations[0].parameters['ContactId'],
                pipeline_id=operations[0].parameters['PipelineId'],
                status_id=operations[0].parameters['StatusId'],
                note=operations[0].parameters.get('Note', ''),
                run_status_automation=operations[0].parameters.get('RunStatusAutomation', False),
            )
            pipeline_external_id = str(pipeline_response.get('PipelineItemId', ''))
        else:
            client.edit_pipeline_item(
                pipeline_item_id=operations[0].parameters['PipelineItemId'],
                status_id=operations[0].parameters.get('StatusId'),
                note=operations[0].parameters.get('Note', ''),
                run_status_automation=operations[0].parameters.get('RunStatusAutomation', False),
            )
            pipeline_response = {'PipelineItemId': operations[0].parameters['PipelineItemId']}
            pipeline_external_id = operations[0].parameters['PipelineItemId']

        _upsert_lacrm_link(
            session,
            quote_case_id=quote_case_id,
            external_type='pipeline_item',
            external_id=pipeline_external_id,
            external_label=pipeline_mapping['lacrm_pipeline_name'],
            sync_status='linked',
            payload={'last_operation': operations[0].to_dict(), 'last_response': pipeline_response},
        )

        if task_needed:
            task_operation = operations[1]
            if task_operation.function == 'CreateTask':
                task_response = client.create_task(
                    name=task_operation.parameters['Name'],
                    due_date=task_operation.parameters.get('DueDate'),
                    description=task_operation.parameters.get('Description', ''),
                    contact_id=task_operation.parameters.get('ContactId'),
                )
                task_external_id = str(task_response.get('TaskId', ''))
            else:
                client.edit_task(
                    task_id=task_operation.parameters['TaskId'],
                    name=task_operation.parameters.get('Name'),
                    due_date=task_operation.parameters.get('DueDate'),
                    description=task_operation.parameters.get('Description'),
                    contact_id=task_operation.parameters.get('ContactId'),
                )
                task_response = {'TaskId': task_operation.parameters['TaskId']}
                task_external_id = task_operation.parameters['TaskId']
            _upsert_lacrm_link(
                session,
                quote_case_id=quote_case_id,
                external_type='follow_up_task',
                external_id=task_external_id,
                external_label='Quote follow up task',
                sync_status='linked',
                payload={'last_operation': task_operation.to_dict(), 'last_response': task_response},
            )
        _update_case_sync_state(session, case, sync_status='synced', sync_notes='LACRM sync applied successfully.', mark_synced=True)
        session.commit()
        session.refresh(case)
        return LACRMSyncResult(
            mode='live',
            sync_status='synced',
            message='Live LACRM sync completed successfully.',
            operations=operations,
            external_links=[item.model_dump() for item in list_external_links(session, quote_case_id)],
            quote_case=serialize_quote_case(session, case),
        ).to_dict()
    except LACRMAPIError as exc:
        _update_case_sync_state(session, case, sync_status='sync_failed', sync_notes=str(exc), mark_synced=False)
        session.commit()
        session.refresh(case)
        return LACRMSyncResult(
            mode='live',
            sync_status='sync_failed',
            message='Live LACRM sync failed. The error is stored on the quote case for review.',
            operations=operations,
            external_links=[item.model_dump() for item in list_external_links(session, quote_case_id)],
            quote_case=serialize_quote_case(session, case),
        ).to_dict()


def _apply_reconciled_stage(session: Session, case: QuoteCase, target_stage_slug: str, trigger_label: str) -> None:
    if case.stage_slug == target_stage_slug:
        return
    workflow_config = get_quote_workflow_config(session)
    target_stage = get_stage_config(workflow_config, case.pipeline_slug, target_stage_slug)
    previous_stage = case.stage_slug
    now = _utcnow()
    case.stage_slug = target_stage_slug
    case.stage_entered_at = now
    case.updated_at = now
    if target_stage.get('follow_up_after_days') is not None:
        case.follow_up_due_on = date.today() + timedelta(days=int(target_stage['follow_up_after_days']))
    if target_stage.get('freshbooks_status_on_entry'):
        case.freshbooks_status = target_stage['freshbooks_status_on_entry']
    session.add(case)
    session.add(
        QuoteStageHistory(
            quote_case_id=case.id,
            pipeline_slug=case.pipeline_slug,
            from_stage_slug=previous_stage,
            to_stage_slug=target_stage_slug,
            moved_by=trigger_label,
            move_reason='Reconciled from LACRM pipeline status change',
            moved_at=now,
        )
    )


# timedelta imported lazily below to keep the file head readable.
from datetime import timedelta  # noqa: E402


def reconcile_lacrm_payload(session: Session, payload: dict[str, Any]) -> dict[str, Any]:
    config = get_lacrm_sync_settings(session)
    now = _utcnow()
    updated_cases: list[int] = []
    unmatched_pipeline_items: list[str] = []
    deleted_pipeline_items: list[str] = []

    for pipeline_item in payload.get('PipelineItems', []) or []:
        pipeline_item_id = str(pipeline_item.get('PipelineItemId', '')).strip()
        if not pipeline_item_id:
            continue
        link = session.exec(
            select(QuoteCaseExternalLink).where(
                QuoteCaseExternalLink.system_slug == 'lacrm',
                QuoteCaseExternalLink.external_type == 'pipeline_item',
                QuoteCaseExternalLink.external_id == pipeline_item_id,
            )
        ).first()
        if not link:
            unmatched_pipeline_items.append(pipeline_item_id)
            continue
        case = session.get(QuoteCase, link.quote_case_id)
        if not case:
            unmatched_pipeline_items.append(pipeline_item_id)
            continue
        reverse_mapping = _find_reverse_mapping(config, str(pipeline_item.get('PipelineId', '')), str(pipeline_item.get('StatusId', '')))
        if reverse_mapping is None:
            _update_case_sync_state(
                session,
                case,
                sync_status='drift',
                sync_notes='LACRM webhook delivered a pipeline/status id that is not mapped locally yet.',
                mark_synced=True,
            )
            updated_cases.append(case.id)
            continue
        _, stage_mapping = reverse_mapping
        _apply_reconciled_stage(session, case, stage_mapping['stage_slug'], 'lacrm_webhook')
        _update_case_sync_state(
            session,
            case,
            sync_status='synced',
            sync_notes=f"Reconciled from LACRM {payload.get('TriggeringEvent', 'payload')}",
            mark_synced=True,
        )
        link.sync_status = 'linked'
        link.payload_json = dumps({'last_payload': pipeline_item})
        link.updated_at = now
        session.add(link)
        updated_cases.append(case.id)

    for pipeline_item_id in payload.get('PipelineItemIds', []) or []:
        link = session.exec(
            select(QuoteCaseExternalLink).where(
                QuoteCaseExternalLink.system_slug == 'lacrm',
                QuoteCaseExternalLink.external_type == 'pipeline_item',
                QuoteCaseExternalLink.external_id == str(pipeline_item_id),
            )
        ).first()
        if not link:
            continue
        case = session.get(QuoteCase, link.quote_case_id)
        if case:
            _update_case_sync_state(
                session,
                case,
                sync_status='external_deleted',
                sync_notes='The linked LACRM pipeline item was deleted in the CRM and now needs manual review.',
                mark_synced=True,
            )
            updated_cases.append(case.id)
        link.sync_status = 'deleted'
        link.updated_at = now
        session.add(link)
        deleted_pipeline_items.append(str(pipeline_item_id))

    session.commit()
    return {
        'triggering_event': payload.get('TriggeringEvent', 'manual'),
        'updated_case_ids': sorted(set(updated_cases)),
        'unmatched_pipeline_items': unmatched_pipeline_items,
        'deleted_pipeline_items': deleted_pipeline_items,
    }


def store_lacrm_webhook_secret(session: Session, hook_secret: str) -> None:
    set_setting(session, LACRM_WEBHOOK_SECRET_KEY, hook_secret, 'Shared secret returned by the LACRM webhook handshake.')


def get_lacrm_webhook_secret(session: Session) -> str:
    return str(get_setting(session, LACRM_WEBHOOK_SECRET_KEY) or '')


def verify_lacrm_webhook_signature(session: Session, body: bytes, signature: str | None) -> bool:
    secret = get_lacrm_webhook_secret(session)
    if not secret or not signature:
        return False
    calculated = hmac.new(secret.encode('utf-8'), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(calculated, signature)
