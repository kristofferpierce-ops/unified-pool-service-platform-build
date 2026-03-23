from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from sqlmodel import Session, select

from app.models.quote_tables import QuoteCase, QuoteCaseExternalLink, QuoteStageHistory
from app.services.system_settings import get_setting, set_setting
from app.utils.serialization import dumps, loads

DEFAULT_QUOTE_WORKFLOW_CONFIG: dict[str, Any] = {
    'version': 'platform_integration_block_1a',
    'default_follow_up_days': 3,
    'pipelines': [
        {
            'slug': 'repairs',
            'name': 'Repairs',
            'color': 'blue',
            'default_stage_slug': 'info_costing',
            'stages': [
                {'slug': 'info_costing', 'name': 'Info + Costing', 'lacrm_stage_name': 'Info + Costing', 'stale_after_days': 2, 'allowed_next': ['quoting', 'doh_repairs', 'on_hold', 'closed_unsuccessful']},
                {'slug': 'doh_repairs', 'name': 'DOH Repairs', 'lacrm_stage_name': 'DOH Repairs', 'stale_after_days': 1, 'allowed_next': ['quoting', 'on_hold', 'closed_unsuccessful']},
                {'slug': 'quoting', 'name': 'Quoting', 'lacrm_stage_name': 'Quoting', 'stale_after_days': 2, 'allowed_next': ['estimate_follow_up', 'on_hold', 'closed_unsuccessful']},
                {'slug': 'estimate_follow_up', 'name': 'Estimate Follow Up', 'lacrm_stage_name': 'Estimate Follow Up', 'stale_after_days': 3, 'follow_up_after_days': 3, 'allowed_next': ['deposit_requested', 'parts_needed', 'on_hold', 'closed_unsuccessful'], 'freshbooks_status_on_entry': 'sent', 'track_view_status': True},
                {'slug': 'deposit_requested', 'name': 'Deposit Requested', 'lacrm_stage_name': 'Deposit Requested', 'stale_after_days': 4, 'allowed_next': ['parts_needed', 'on_hold', 'closed_unsuccessful']},
                {'slug': 'parts_needed', 'name': 'Parts Needed', 'lacrm_stage_name': 'Parts Needed', 'stale_after_days': 2, 'allowed_next': ['parts_ordered', 'on_hold', 'closed_unsuccessful']},
                {'slug': 'parts_ordered', 'name': 'Parts Ordered', 'lacrm_stage_name': 'Parts Ordered', 'stale_after_days': 5, 'allowed_next': ['schedule', 'on_hold', 'closed_unsuccessful']},
                {'slug': 'schedule', 'name': 'Schedule', 'lacrm_stage_name': 'Schedule', 'stale_after_days': 3, 'allowed_next': ['receipts_needed', 'job_complete', 'on_hold']},
                {'slug': 'receipts_needed', 'name': 'Receipts Needed', 'lacrm_stage_name': 'Receipts Needed', 'stale_after_days': 3, 'allowed_next': ['job_complete', 'on_hold']},
                {'slug': 'job_complete', 'name': 'Job Complete', 'lacrm_stage_name': 'Job Complete', 'stale_after_days': 7, 'allowed_next': ['closed_successful']},
                {'slug': 'on_hold', 'name': 'On Hold', 'lacrm_stage_name': 'On Hold', 'stale_after_days': 14, 'allowed_next': ['info_costing', 'quoting', 'estimate_follow_up', 'closed_unsuccessful']},
                {'slug': 'closed_unsuccessful', 'name': 'Closed Unsuccessful', 'lacrm_stage_name': 'Closed Unsuccessful', 'is_closed': True, 'stale_after_days': 999, 'allowed_next': []},
                {'slug': 'closed_successful', 'name': 'Closed Successful', 'lacrm_stage_name': 'Closed Successful', 'is_closed': True, 'stale_after_days': 999, 'allowed_next': []},
            ],
        },
        {
            'slug': 'new_commercial_services',
            'name': 'New Commercial Services',
            'color': 'green',
            'default_stage_slug': 'info_costing',
            'stages': [
                {'slug': 'info_costing', 'name': 'Info + Costing', 'lacrm_stage_name': 'Info + Costing', 'stale_after_days': 2, 'allowed_next': ['quoting', 'follow_up', 'closed_unsuccessful']},
                {'slug': 'quoting', 'name': 'Quoting', 'lacrm_stage_name': 'Quoting', 'stale_after_days': 2, 'allowed_next': ['follow_up', 'closed_unsuccessful']},
                {'slug': 'follow_up', 'name': 'Follow Up', 'lacrm_stage_name': 'Follow Up', 'stale_after_days': 3, 'follow_up_after_days': 3, 'allowed_next': ['accepted', 'closed_unsuccessful'], 'freshbooks_status_on_entry': 'sent', 'track_view_status': True},
                {'slug': 'accepted', 'name': 'Accepted', 'lacrm_stage_name': 'Accepted', 'is_closed': True, 'stale_after_days': 999, 'allowed_next': []},
                {'slug': 'closed_unsuccessful', 'name': 'Closed Unsuccessful', 'lacrm_stage_name': 'Closed Unsuccessful', 'is_closed': True, 'stale_after_days': 999, 'allowed_next': []},
            ],
        },
        {
            'slug': 'new_residential_services',
            'name': 'New Residential Services',
            'color': 'pink',
            'default_stage_slug': 'info_costing',
            'stages': [
                {'slug': 'info_costing', 'name': 'Info + Costing', 'lacrm_stage_name': 'Info + Costing', 'stale_after_days': 2, 'allowed_next': ['quoting', 'follow_up', 'closed_unsuccessful']},
                {'slug': 'quoting', 'name': 'Quoting', 'lacrm_stage_name': 'Quoting', 'stale_after_days': 2, 'allowed_next': ['follow_up', 'closed_unsuccessful']},
                {'slug': 'follow_up', 'name': 'Follow Up', 'lacrm_stage_name': 'Follow Up', 'stale_after_days': 3, 'follow_up_after_days': 3, 'allowed_next': ['accepted', 'closed_unsuccessful'], 'freshbooks_status_on_entry': 'sent', 'track_view_status': True},
                {'slug': 'accepted', 'name': 'Accepted', 'lacrm_stage_name': 'Accepted', 'is_closed': True, 'stale_after_days': 999, 'allowed_next': []},
                {'slug': 'closed_unsuccessful', 'name': 'Closed Unsuccessful', 'lacrm_stage_name': 'Closed Unsuccessful', 'is_closed': True, 'stale_after_days': 999, 'allowed_next': []},
            ],
        },
        {
            'slug': 'pool_resurfaces',
            'name': 'Pool Resurfaces',
            'color': 'red',
            'default_stage_slug': 'info_costing',
            'stages': [
                {'slug': 'info_costing', 'name': 'Info + Costing', 'lacrm_stage_name': 'Info + Costing', 'stale_after_days': 2, 'allowed_next': ['quoting', 'answer_required', 'closed_unsuccessful']},
                {'slug': 'quoting', 'name': 'Quoting', 'lacrm_stage_name': 'Quoting', 'stale_after_days': 2, 'allowed_next': ['answer_required', 'deposit_requested', 'closed_unsuccessful']},
                {'slug': 'answer_required', 'name': 'Answer Required', 'lacrm_stage_name': 'Answer?', 'stale_after_days': 3, 'follow_up_after_days': 3, 'allowed_next': ['deposit_requested', 'accepted_scheduled', 'closed_unsuccessful'], 'freshbooks_status_on_entry': 'sent', 'track_view_status': True},
                {'slug': 'deposit_requested', 'name': 'Deposit Requested', 'lacrm_stage_name': 'Deposit Requested', 'stale_after_days': 4, 'allowed_next': ['accepted_scheduled', 'closed_unsuccessful']},
                {'slug': 'accepted_scheduled', 'name': 'Accepted + Scheduled', 'lacrm_stage_name': 'Accepted + Scheduled', 'stale_after_days': 7, 'allowed_next': ['thirty_day_maintenance']},
                {'slug': 'thirty_day_maintenance', 'name': '30 Day Maintenance', 'lacrm_stage_name': '30 Day Maintenance', 'is_closed': True, 'stale_after_days': 999, 'allowed_next': []},
                {'slug': 'closed_unsuccessful', 'name': 'Closed Unsuccessful', 'lacrm_stage_name': 'Closed Unsuccessful', 'is_closed': True, 'stale_after_days': 999, 'allowed_next': []},
            ],
        },
    ],
}


def ensure_quote_workflow_settings(session: Session) -> dict[str, Any]:
    config = get_setting(session, 'quote_workflow_config')
    if config:
        return config
    set_setting(
        session,
        'quote_workflow_config',
        DEFAULT_QUOTE_WORKFLOW_CONFIG,
        'Admin editable quote workflow map for dashboard counts, allowed transitions, follow up timing, and external system status alignment.',
    )
    return DEFAULT_QUOTE_WORKFLOW_CONFIG


def get_quote_workflow_config(session: Session) -> dict[str, Any]:
    return ensure_quote_workflow_settings(session)


def pipeline_map(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {pipeline['slug']: pipeline for pipeline in config.get('pipelines', [])}


def get_pipeline_config(config: dict[str, Any], pipeline_slug: str) -> dict[str, Any]:
    pipeline = pipeline_map(config).get(pipeline_slug)
    if not pipeline:
        raise ValueError(f'Unknown pipeline: {pipeline_slug}')
    return pipeline


def get_stage_config(config: dict[str, Any], pipeline_slug: str, stage_slug: str) -> dict[str, Any]:
    pipeline = get_pipeline_config(config, pipeline_slug)
    for stage in pipeline.get('stages', []):
        if stage['slug'] == stage_slug:
            return stage
    raise ValueError(f'Unknown stage {stage_slug} for pipeline {pipeline_slug}')


def list_stage_options(config: dict[str, Any], pipeline_slug: str) -> list[dict[str, Any]]:
    return list(get_pipeline_config(config, pipeline_slug).get('stages', []))


def _assign_default_follow_up(case: QuoteCase, stage_config: dict[str, Any], config: dict[str, Any]) -> None:
    follow_up_days = stage_config.get('follow_up_after_days')
    if follow_up_days is None:
        return
    case.follow_up_due_on = date.today() + timedelta(days=int(follow_up_days or config.get('default_follow_up_days', 3)))


def create_quote_case(
    session: Session,
    *,
    pipeline_slug: str,
    title: str,
    stage_slug: str | None = None,
    workflow_mode: str = 'quote',
    account_id: int | None = None,
    property_id: int | None = None,
    vessel_id: int | None = None,
    requester_name: str = '',
    requester_phone: str = '',
    requester_email: str = '',
    description: str = '',
    assigned_to: str = '',
) -> QuoteCase:
    config = get_quote_workflow_config(session)
    pipeline = get_pipeline_config(config, pipeline_slug)
    stage_slug = stage_slug or pipeline.get('default_stage_slug')
    stage_config = get_stage_config(config, pipeline_slug, stage_slug)
    now = datetime.utcnow()
    case = QuoteCase(
        pipeline_slug=pipeline_slug,
        stage_slug=stage_slug,
        workflow_mode=workflow_mode,
        account_id=account_id,
        property_id=property_id,
        vessel_id=vessel_id,
        title=title,
        requester_name=requester_name,
        requester_phone=requester_phone,
        requester_email=requester_email,
        description=description,
        assigned_to=assigned_to,
        requested_at=now,
        stage_entered_at=now,
        created_at=now,
        updated_at=now,
    )
    _assign_default_follow_up(case, stage_config, config)
    session.add(case)
    session.commit()
    session.refresh(case)
    if not case.quote_number:
        case.quote_number = f'Q{case.id:06d}'
        session.add(case)
    history = QuoteStageHistory(
        quote_case_id=case.id,
        pipeline_slug=case.pipeline_slug,
        from_stage_slug='',
        to_stage_slug=case.stage_slug,
        moved_by='system',
        move_reason='created',
        moved_at=now,
    )
    session.add(history)
    session.commit()
    session.refresh(case)
    return case


def move_quote_case(
    session: Session,
    quote_case_id: int,
    *,
    target_stage_slug: str,
    moved_by: str = 'system',
    move_reason: str = '',
    sync_status: str | None = None,
    sync_notes: str | None = None,
) -> QuoteCase:
    case = session.get(QuoteCase, quote_case_id)
    if not case:
        raise ValueError('Quote case not found')
    config = get_quote_workflow_config(session)
    current_stage = get_stage_config(config, case.pipeline_slug, case.stage_slug)
    target_stage = get_stage_config(config, case.pipeline_slug, target_stage_slug)
    allowed_next = set(current_stage.get('allowed_next', []))
    if allowed_next and target_stage_slug not in allowed_next:
        raise ValueError(f'Stage {target_stage_slug} is not allowed from {case.stage_slug}')
    previous_stage = case.stage_slug
    now = datetime.utcnow()
    case.stage_slug = target_stage_slug
    case.stage_entered_at = now
    case.updated_at = now
    if 'freshbooks_status_on_entry' in target_stage:
        case.freshbooks_status = target_stage['freshbooks_status_on_entry']
    if target_stage.get('follow_up_after_days') is not None:
        _assign_default_follow_up(case, target_stage, config)
    elif target_stage.get('is_closed'):
        case.follow_up_due_on = None
    if sync_status:
        case.sync_status = sync_status
        case.last_synced_at = now
    if sync_notes:
        case.sync_notes = sync_notes
    session.add(case)
    session.add(QuoteStageHistory(
        quote_case_id=case.id,
        pipeline_slug=case.pipeline_slug,
        from_stage_slug=previous_stage,
        to_stage_slug=target_stage_slug,
        moved_by=moved_by,
        move_reason=move_reason,
        moved_at=now,
    ))
    session.commit()
    session.refresh(case)
    return case


def mark_quote_viewed(session: Session, quote_case_id: int, viewed_at: datetime | None = None) -> QuoteCase:
    case = session.get(QuoteCase, quote_case_id)
    if not case:
        raise ValueError('Quote case not found')
    case.is_viewed = True
    case.last_viewed_at = viewed_at or datetime.utcnow()
    case.updated_at = datetime.utcnow()
    if case.freshbooks_status in {'not_created', 'draft'}:
        case.freshbooks_status = 'viewed'
    session.add(case)
    session.commit()
    session.refresh(case)
    return case


def add_external_link(
    session: Session,
    *,
    quote_case_id: int,
    system_slug: str,
    external_id: str,
    external_type: str = 'record',
    external_label: str = '',
    sync_direction: str = 'bidirectional',
    sync_status: str = 'linked',
    payload: dict[str, Any] | None = None,
) -> QuoteCaseExternalLink:
    link = session.exec(
        select(QuoteCaseExternalLink).where(
            QuoteCaseExternalLink.quote_case_id == quote_case_id,
            QuoteCaseExternalLink.system_slug == system_slug,
            QuoteCaseExternalLink.external_id == external_id,
        )
    ).first()
    now = datetime.utcnow()
    if not link:
        link = QuoteCaseExternalLink(
            quote_case_id=quote_case_id,
            system_slug=system_slug,
            external_id=external_id,
            created_at=now,
        )
        session.add(link)
    link.external_type = external_type
    link.external_label = external_label
    link.sync_direction = sync_direction
    link.sync_status = sync_status
    link.payload_json = dumps(payload or {})
    link.updated_at = now
    case = session.get(QuoteCase, quote_case_id)
    if case:
        case.sync_status = sync_status
        case.last_synced_at = now
        case.updated_at = now
        session.add(case)
    session.commit()
    session.refresh(link)
    return link


def list_quote_cases(
    session: Session,
    *,
    pipeline_slug: str | None = None,
    stage_slug: str | None = None,
    include_closed: bool = True,
    limit: int = 200,
) -> list[QuoteCase]:
    query = select(QuoteCase)
    if pipeline_slug:
        query = query.where(QuoteCase.pipeline_slug == pipeline_slug)
    if stage_slug:
        query = query.where(QuoteCase.stage_slug == stage_slug)
    cases = list(session.exec(query.order_by(QuoteCase.stage_entered_at.desc()).limit(limit)).all())
    if include_closed:
        return cases
    config = get_quote_workflow_config(session)
    filtered: list[QuoteCase] = []
    for case in cases:
        stage = get_stage_config(config, case.pipeline_slug, case.stage_slug)
        if not stage.get('is_closed'):
            filtered.append(case)
    return filtered


def get_quote_case(session: Session, quote_case_id: int) -> QuoteCase | None:
    return session.get(QuoteCase, quote_case_id)


def list_external_links(session: Session, quote_case_id: int) -> list[QuoteCaseExternalLink]:
    return list(
        session.exec(
            select(QuoteCaseExternalLink)
            .where(QuoteCaseExternalLink.quote_case_id == quote_case_id)
            .order_by(QuoteCaseExternalLink.system_slug, QuoteCaseExternalLink.external_type)
        ).all()
    )


def list_stage_history(session: Session, quote_case_id: int) -> list[QuoteStageHistory]:
    return list(
        session.exec(
            select(QuoteStageHistory)
            .where(QuoteStageHistory.quote_case_id == quote_case_id)
            .order_by(QuoteStageHistory.moved_at.desc())
        ).all()
    )


def case_age_days(case: QuoteCase, now: datetime | None = None) -> int:
    now = now or datetime.utcnow()
    return max(0, (now.date() - case.requested_at.date()).days)


def stage_age_days(case: QuoteCase, now: datetime | None = None) -> int:
    now = now or datetime.utcnow()
    return max(0, (now.date() - case.stage_entered_at.date()).days)


def is_case_stale(case: QuoteCase, stage_config: dict[str, Any], now: datetime | None = None) -> bool:
    now = now or datetime.utcnow()
    stale_after = int(stage_config.get('stale_after_days', 999))
    if stage_config.get('is_closed'):
        return False
    return stage_age_days(case, now) >= stale_after


def serialize_quote_case(session: Session, case: QuoteCase, config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or get_quote_workflow_config(session)
    stage = get_stage_config(config, case.pipeline_slug, case.stage_slug)
    payload = case.model_dump()
    payload['age_days'] = case_age_days(case)
    payload['stage_age_days'] = stage_age_days(case)
    payload['is_stale'] = is_case_stale(case, stage)
    payload['pipeline_name'] = get_pipeline_config(config, case.pipeline_slug)['name']
    payload['stage_name'] = stage['name']
    payload['track_view_status'] = bool(stage.get('track_view_status', False))
    return payload


def get_dashboard_summary(session: Session) -> dict[str, Any]:
    config = get_quote_workflow_config(session)
    cases = list_quote_cases(session, limit=1000)
    now = datetime.utcnow()
    totals = {
        'open_cases': 0,
        'stale_cases': 0,
        'follow_ups_due': 0,
        'sent_not_viewed': 0,
    }
    pipeline_cards: list[dict[str, Any]] = []
    for pipeline in config.get('pipelines', []):
        stage_cards: list[dict[str, Any]] = []
        pipeline_cases = [case for case in cases if case.pipeline_slug == pipeline['slug']]
        for stage in pipeline.get('stages', []):
            stage_cases = [case for case in pipeline_cases if case.stage_slug == stage['slug']]
            count = len(stage_cases)
            stale_count = sum(1 for case in stage_cases if is_case_stale(case, stage, now))
            viewed_count = sum(1 for case in stage_cases if case.is_viewed)
            due_count = sum(1 for case in stage_cases if case.follow_up_due_on and case.follow_up_due_on <= now.date())
            sent_not_viewed = sum(
                1 for case in stage_cases if stage.get('track_view_status') and case.freshbooks_status in {'sent', 'viewed'} and not case.is_viewed
            )
            stage_cards.append({
                'stage_slug': stage['slug'],
                'stage_name': stage['name'],
                'count': count,
                'stale_count': stale_count,
                'viewed_count': viewed_count,
                'follow_ups_due': due_count,
                'sent_not_viewed': sent_not_viewed,
                'is_closed': bool(stage.get('is_closed', False)),
                'lacrm_stage_name': stage.get('lacrm_stage_name', stage['name']),
            })
            if not stage.get('is_closed'):
                totals['open_cases'] += count
            totals['stale_cases'] += stale_count
            totals['follow_ups_due'] += due_count
            totals['sent_not_viewed'] += sent_not_viewed
        pipeline_cards.append({
            'pipeline_slug': pipeline['slug'],
            'pipeline_name': pipeline['name'],
            'color': pipeline.get('color', 'gray'),
            'total_cases': len(pipeline_cases),
            'stages': stage_cards,
        })
    return {
        'generated_at': now.isoformat(),
        'totals': totals,
        'pipelines': pipeline_cards,
    }
