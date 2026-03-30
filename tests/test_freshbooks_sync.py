from __future__ import annotations

import base64
import hashlib
import hmac
import json

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.api.main import app
from app.core.database import engine
from app.services.freshbooks_sync import get_freshbooks_sync_settings
from app.services.system_settings import set_setting


client = TestClient(app)


def _set_freshbooks_mode(sync_mode: str = 'dry_run') -> None:
    with Session(engine) as session:
        config = get_freshbooks_sync_settings(session)
        config['sync_mode'] = sync_mode
        set_setting(session, 'freshbooks_sync_config', config, 'Test override for FreshBooks sync settings.')


class _FakeFreshBooksClient:
    account_id = 'ACC123'

    def list_clients(self, *, email: str | None = None, organization: str | None = None, page: int = 1, per_page: int = 15):
        return []

    def create_client(self, client_payload: dict):
        return {
            'id': 501,
            'organization': client_payload.get('organization') or 'Created Company',
            'fname': client_payload.get('fname', ''),
            'lname': client_payload.get('lname', ''),
        }

    def create_estimate(self, estimate_payload: dict):
        return {
            'id': 9001,
            'estimate_number': '000009001',
            'status': 1,
            'ui_status': 'draft',
            **estimate_payload,
        }

    def update_estimate(self, estimate_id: str, estimate_payload: dict):
        return {
            'id': int(estimate_id),
            'estimate_number': '000009001',
            'status': 1,
            'ui_status': 'draft',
            **estimate_payload,
        }

    def get_estimate(self, estimate_id: str, *, includes: list[str] | None = None):
        return {
            'id': int(estimate_id),
            'estimate_number': '000009001',
            'status': 3,
            'ui_status': 'viewed',
            'display_status': 'viewed',
            'audit_logs': [{'event': 'viewed'}],
        }

    def get_identity_info(self):
        return {
            'response': {
                'business_memberships': [
                    {
                        'business': {
                            'account_id': 'ACC123',
                            'id': 42,
                            'name': 'Demo Business',
                        }
                    }
                ]
            }
        }


def test_freshbooks_draft_dry_run_prepares_local_estimate():
    _set_freshbooks_mode('dry_run')
    create_response = client.post(
        '/quote-workflow/cases',
        json={
            'pipeline_slug': 'new_residential_services',
            'title': 'FreshBooks dry run draft case',
            'requester_name': 'Mike Tester',
            'requester_email': 'mike@example.com',
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()

    draft_response = client.post(
        f"/quote-workflow/cases/{created['id']}/freshbooks/draft",
        json={
            'note': 'Prepare local FreshBooks draft only',
            'force_live': False,
            'currency_code': 'USD',
            'organization': 'Tester HOA',
            'lines': [
                {
                    'name': 'Weekly service package',
                    'description': 'Initial draft line',
                    'qty': 1,
                    'amount': 299,
                    'code': 'USD',
                }
            ],
        },
    )
    assert draft_response.status_code == 200
    payload = draft_response.json()
    assert payload['mode'] == 'dry_run'
    assert payload['sync_status'] == 'draft_prepared'
    assert any(link['system_slug'] == 'freshbooks' and link['external_type'] == 'estimate' for link in payload['external_links'])
    assert payload['quote_case']['freshbooks_status'] == 'draft'


def test_freshbooks_live_refresh_moves_case_to_follow_up(monkeypatch):
    _set_freshbooks_mode('live')
    monkeypatch.setattr('app.services.freshbooks_sync.get_freshbooks_client', lambda: _FakeFreshBooksClient())

    create_response = client.post(
        '/quote-workflow/cases',
        json={
            'pipeline_slug': 'new_residential_services',
            'title': 'FreshBooks live draft case',
            'requester_name': 'Sandy Client',
            'requester_email': 'sandy@example.com',
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()

    draft_response = client.post(
        f"/quote-workflow/cases/{created['id']}/freshbooks/draft",
        json={
            'note': 'Create live draft',
            'force_live': True,
            'currency_code': 'USD',
            'organization': 'Sandy Condos',
            'lines': [
                {
                    'name': 'Repair scope',
                    'description': 'Quoted line',
                    'qty': 1,
                    'amount': 1250,
                    'code': 'USD',
                }
            ],
        },
    )
    assert draft_response.status_code == 200
    assert draft_response.json()['sync_status'] == 'draft_created'

    refresh_response = client.post(
        f"/quote-workflow/cases/{created['id']}/freshbooks/refresh",
        json={'force_live': True},
    )
    assert refresh_response.status_code == 200
    refreshed = refresh_response.json()
    assert refreshed['quote_case']['stage_slug'] == 'follow_up'
    assert refreshed['quote_case']['freshbooks_status'] == 'viewed'


def test_freshbooks_webhook_verifier_and_reconcile_round_trip():
    handshake_response = client.post(
        '/quote-workflow/freshbooks/webhook',
        data={'verifier': 'fb-secret-123', 'callback_id': '444'},
    )
    assert handshake_response.status_code == 200
    assert handshake_response.json()['verification_received'] is True

    create_response = client.post(
        '/quote-workflow/cases',
        json={
            'pipeline_slug': 'new_residential_services',
            'title': 'FreshBooks webhook reconcile case',
            'requester_name': 'Webhook Client',
            'requester_email': 'hook@example.com',
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()
    estimate_id = str(5000 + created['id'])

    link_response = client.post(
        f"/quote-workflow/cases/{created['id']}/external-links",
        json={
            'system_slug': 'freshbooks',
            'external_type': 'estimate',
            'external_id': estimate_id,
            'external_label': 'Prepared estimate',
            'sync_status': 'linked',
            'payload': {'ui_status': 'draft', 'status_code': '1'},
        },
    )
    assert link_response.status_code == 200

    form_payload = {'name': 'estimate.sendByEmail', 'object_id': estimate_id}
    serialized = json.dumps({key: str(value) for key, value in form_payload.items()}).encode('utf-8')
    signature = base64.b64encode(hmac.new(b'fb-secret-123', serialized, hashlib.sha256).digest()).decode('utf-8')
    webhook_response = client.post(
        '/quote-workflow/freshbooks/webhook',
        data=form_payload,
        headers={'X-FreshBooks-Hmac-SHA256': signature},
    )
    assert webhook_response.status_code == 200
    assert created['id'] in webhook_response.json()['updated_case_ids']
