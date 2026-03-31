from __future__ import annotations

import json
import os
from dataclasses import asdict
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.connectors.lacrm.contracts import LACRMConnectionStatus

DEFAULT_LACRM_API_BASE_URL = 'https://api.lessannoyingcrm.com/v2/'


class LACRMAPIError(RuntimeError):
    pass


class LACRMClient:
    def __init__(self, api_key: str, api_base_url: str = DEFAULT_LACRM_API_BASE_URL) -> None:
        self.api_key = api_key.strip()
        self.api_base_url = api_base_url.strip() or DEFAULT_LACRM_API_BASE_URL
        if not self.api_base_url.endswith('/'):
            self.api_base_url = f'{self.api_base_url}/'
        if not self.api_key:
            raise ValueError('LACRM API key is required')

    def call(self, function: str, parameters: dict[str, Any] | None = None) -> dict[str, Any] | list[Any]:
        body = json.dumps({'Function': function, 'Parameters': parameters or {}}).encode('utf-8')
        request = Request(
            self.api_base_url,
            data=body,
            headers={
                'Content-Type': 'application/json',
                'Authorization': self.api_key,
            },
            method='POST',
        )
        try:
            with urlopen(request, timeout=30) as response:
                raw = response.read().decode('utf-8') or '{}'
                return json.loads(raw)
        except HTTPError as exc:
            payload = exc.read().decode('utf-8', errors='replace')
            raise LACRMAPIError(f'LACRM HTTP {exc.code}: {payload}') from exc
        except URLError as exc:
            raise LACRMAPIError(f'LACRM connection failed: {exc.reason}') from exc

    def get_user(self) -> dict[str, Any]:
        result = self.call('GetUser')
        return dict(result)

    def get_pipelines(self, *, include_archived_pipelines: bool = False, include_custom_fields: bool = False, include_hidden_pipelines: bool = False) -> list[dict[str, Any]]:
        result = self.call(
            'GetPipelines',
            {
                'IncludeArchivedPipelines': include_archived_pipelines,
                'IncludeCustomFields': include_custom_fields,
                'IncludeHiddenPipelines': include_hidden_pipelines,
            },
        )
        return list(result)

    def get_pipeline_statuses(self, pipeline_id: str | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if pipeline_id:
            params['PipelineId'] = pipeline_id
        result = self.call('GetPipelineStatuses', params)
        return list(result)

    def create_pipeline_item(self, *, contact_id: str, pipeline_id: str, status_id: str, note: str = '', run_status_automation: bool = False) -> dict[str, Any]:
        return dict(
            self.call(
                'CreatePipelineItem',
                {
                    'ContactId': contact_id,
                    'PipelineId': pipeline_id,
                    'StatusId': status_id,
                    'Note': note,
                    'RunStatusAutomation': run_status_automation,
                },
            )
        )

    def edit_pipeline_item(self, *, pipeline_item_id: str, status_id: str | None = None, note: str = '', run_status_automation: bool = False) -> dict[str, Any]:
        parameters: dict[str, Any] = {
            'PipelineItemId': pipeline_item_id,
            'Note': note,
            'RunStatusAutomation': run_status_automation,
        }
        if status_id:
            parameters['StatusId'] = status_id
        result = self.call('EditPipelineItem', parameters)
        return dict(result) if isinstance(result, dict) else {}

    def get_pipeline_item(self, pipeline_item_id: str) -> dict[str, Any]:
        return dict(self.call('GetPipelineItem', {'PipelineItemId': pipeline_item_id}))

    def create_task(self, *, name: str, due_date: str | None = None, assigned_to: str | None = None, description: str = '', contact_id: str | None = None, calendar_id: str | None = None) -> dict[str, Any]:
        parameters: dict[str, Any] = {'Name': name, 'Description': description}
        if due_date:
            parameters['DueDate'] = due_date
        if assigned_to:
            parameters['AssignedTo'] = assigned_to
        if contact_id:
            parameters['ContactId'] = contact_id
        if calendar_id:
            parameters['CalendarId'] = calendar_id
        return dict(self.call('CreateTask', parameters))

    def edit_task(self, *, task_id: str, name: str | None = None, due_date: str | None = None, assigned_to: str | None = None, description: str | None = None, contact_id: str | None = None, calendar_id: str | None = None, is_complete: bool | None = None) -> dict[str, Any]:
        parameters: dict[str, Any] = {'TaskId': task_id}
        if name is not None:
            parameters['Name'] = name
        if due_date is not None:
            parameters['DueDate'] = due_date
        if assigned_to is not None:
            parameters['AssignedTo'] = assigned_to
        if description is not None:
            parameters['Description'] = description
        if contact_id is not None:
            parameters['ContactId'] = contact_id
        if calendar_id is not None:
            parameters['CalendarId'] = calendar_id
        if is_complete is not None:
            parameters['IsComplete'] = is_complete
        result = self.call('EditTask', parameters)
        return dict(result) if isinstance(result, dict) else {}

    def create_webhook(self, *, endpoint_url: str, events: list[str], webhook_scope: str = 'Account') -> dict[str, Any]:
        return dict(
            self.call(
                'CreateWebhook',
                {
                    'EndpointUrl': endpoint_url,
                    'Events': events,
                    'WebhookScope': webhook_scope,
                },
            )
        )


def get_lacrm_client(api_key: str | None = None, api_base_url: str | None = None) -> LACRMClient | None:
    resolved_api_key = (api_key or os.getenv('LACRM_API_KEY', '')).strip()
    if not resolved_api_key:
        return None
    resolved_base_url = (api_base_url or os.getenv('LACRM_API_BASE_URL', DEFAULT_LACRM_API_BASE_URL)).strip() or DEFAULT_LACRM_API_BASE_URL
    return LACRMClient(api_key=resolved_api_key, api_base_url=resolved_base_url)


def get_lacrm_connection_status(sync_mode: str = 'dry_run') -> dict[str, Any]:
    client = get_lacrm_client()
    status = LACRMConnectionStatus(
        api_base_url=(os.getenv('LACRM_API_BASE_URL', DEFAULT_LACRM_API_BASE_URL) or DEFAULT_LACRM_API_BASE_URL).strip(),
        has_api_key=client is not None,
        configured=client is not None,
        live_write_enabled=sync_mode == 'live' and client is not None,
        sync_mode=sync_mode,
    )
    return asdict(status)
