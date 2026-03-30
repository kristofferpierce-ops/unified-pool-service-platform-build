from __future__ import annotations

import hashlib
import hmac
import json

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.api.main import app
from app.core.database import engine
from app.services.lacrm_sync import get_lacrm_sync_settings
from app.services.system_settings import set_setting


client = TestClient(app)


def _set_minimum_mapping() -> None:
    with Session(engine) as session:
        config = get_lacrm_sync_settings(session)
        for pipeline in config['pipelines']:
            if pipeline['pipeline_slug'] == 'new_residential_services':
                pipeline['lacrm_pipeline_id'] = 'pipeline-residential'
                for stage in pipeline['stages']:
                    if stage['stage_slug'] == 'info_costing':
                        stage['lacrm_status_id'] = 'status-info'
                    if stage['stage_slug'] == 'follow_up':
                        stage['lacrm_status_id'] = 'status-follow-up'
        set_setting(session, 'lacrm_sync_config', config, 'Test override for LACRM sync mapping.')


class _FakeLACRMClient:
    def get_pipelines(self, *, include_archived_pipelines: bool = False, include_custom_fields: bool = False, include_hidden_pipelines: bool = False):
        return [
            {
                'PipelineId': 'pipeline-repairs',
                'Name': 'Repairs',
                'Statuses': [
                    {'StatusId': 'repairs-info', 'Name': 'Info + Costing'},
                    {'StatusId': 'repairs-quoting', 'Name': 'Quoting'},
                ],
            },
            {
                'PipelineId': 'pipeline-residential',
                'Name': 'New Residential Services',
                'Statuses': [
                    {'StatusId': 'status-info', 'Name': 'Info + Costing'},
                    {'StatusId': 'status-quoting', 'Name': 'Quoting'},
                    {'StatusId': 'status-follow-up', 'Name': 'Follow Up'},
                    {'StatusId': 'status-accepted', 'Name': 'Accepted'},
                ],
            },
        ]


def test_lacrm_contact_link_and_dry_run_sync():
    _set_minimum_mapping()
    create_response = client.post(
        '/quote-workflow/cases',
        json={
            'pipeline_slug': 'new_residential_services',
            'title': 'Residential weekly service quote for dry run sync',
            'requester_name': 'Mike Tester',
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()

    contact_response = client.post(
        f"/quote-workflow/cases/{created['id']}/lacrm/contact-link",
        json={'contact_id': 'contact-123', 'contact_name': 'Mike Tester'},
    )
    assert contact_response.status_code == 200
    assert contact_response.json()['contact_link']['external_id'] == 'contact-123'

    move_response = client.post(
        f"/quote-workflow/cases/{created['id']}/move",
        json={
            'target_stage_slug': 'follow_up',
            'moved_by': 'test_runner',
            'move_reason': 'Quote is ready for follow up and should generate a dry run task.',
        },
    )
    assert move_response.status_code == 200

    sync_response = client.post(
        f"/quote-workflow/cases/{created['id']}/lacrm/sync",
        json={'note': 'Dry run sync from test', 'force_live': False, 'create_follow_up_task': True},
    )
    assert sync_response.status_code == 200
    payload = sync_response.json()
    assert payload['mode'] == 'dry_run'
    assert payload['sync_status'] == 'dry_run_ready'
    assert any(operation['function'] == 'CreatePipelineItem' for operation in payload['operations'])
    assert any(link['external_type'] == 'follow_up_task' for link in payload['external_links'])


def test_lacrm_mapping_refresh_and_reconcile(monkeypatch):
    monkeypatch.setattr('app.services.lacrm_sync.get_lacrm_client', lambda: _FakeLACRMClient())

    refresh_response = client.post('/quote-workflow/lacrm/mapping/refresh')
    assert refresh_response.status_code == 200
    refreshed = refresh_response.json()
    assert refreshed['mapped_stage_count'] >= 4

    create_response = client.post(
        '/quote-workflow/cases',
        json={
            'pipeline_slug': 'new_residential_services',
            'title': 'Residential quote for webhook reconcile',
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()

    link_response = client.post(
        f"/quote-workflow/cases/{created['id']}/external-links",
        json={
            'system_slug': 'lacrm',
            'external_type': 'pipeline_item',
            'external_id': f"pipeline-item-{created['id']}",
            'external_label': 'Residential services pipeline item',
            'sync_status': 'linked',
            'payload': {},
        },
    )
    assert link_response.status_code == 200

    reconcile_response = client.post(
        '/quote-workflow/lacrm/reconcile',
        json={
            'payload': {
                'TriggeringEvent': 'PipelineItemStatus.Update',
                'PipelineItems': [
                    {
                        'PipelineItemId': f"pipeline-item-{created['id']}",
                        'PipelineId': 'pipeline-residential',
                        'StatusId': 'status-follow-up',
                    }
                ],
            }
        },
    )
    assert reconcile_response.status_code == 200
    assert created['id'] in reconcile_response.json()['updated_case_ids']

    detail_response = client.get(f"/quote-workflow/cases/{created['id']}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail['stage_slug'] == 'follow_up'
    assert detail['sync_status'] == 'synced'


def test_lacrm_webhook_handshake_and_signature_round_trip():
    handshake_response = client.post('/quote-workflow/lacrm/webhook', headers={'X-Hook-Secret': 'shared-secret-123'})
    assert handshake_response.status_code == 200
    assert handshake_response.headers['X-Hook-Secret'] == 'shared-secret-123'

    payload = {'TriggeringEvent': 'PipelineItemStatus.Delete', 'PipelineItemIds': ['missing-pipeline-item']}
    body = json.dumps(payload).encode('utf-8')
    signature = hmac.new(b'shared-secret-123', body, hashlib.sha256).hexdigest()
    webhook_response = client.post('/quote-workflow/lacrm/webhook', data=body, headers={'X-Hook-Signature': signature, 'Content-Type': 'application/json'})
    assert webhook_response.status_code == 200
    assert webhook_response.json()['triggering_event'] == 'PipelineItemStatus.Delete'
