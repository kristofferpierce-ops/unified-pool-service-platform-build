from fastapi.testclient import TestClient

from app.api.main import app


client = TestClient(app)


def _ingest_sms(message_id: str, body: str, phone: str = '+13055550980') -> int:
    payload = {
        'payload': {
            'event_kind': 'sms',
            'external_id': message_id,
            'message_external_id': message_id,
            'direction': 'Inbound',
            'body': body,
            'summary': body,
            'transcript': body,
            'external_phone': phone,
            'internal_phone': '+13055550000',
            'from_phone': phone,
            'to_phone': '+13055550000',
            'occurred_at': '2026-04-19T23:10:00Z',
            'bridge_context': {'source': 'message_sync', 'bridge_db': 'platform_event_outbox'},
        }
    }
    response = client.post('/connectors/ringcentral/events', json=payload)
    assert response.status_code == 200
    return response.json()['materialized']['sms_thread_id']


def test_lacrm_apply_audit_endpoints_track_dry_run_action():
    thread_id = _ingest_sms('lacrm-apply-audit-msg-1', 'Apply audit test message.', '+13055550981')
    response = client.post(
        f'/front-desk/sms-threads/{thread_id}/lacrm-apply',
        json={
            'chosen_contact_ref': 'lacrm_contact:audit-test-123',
            'include_note': True,
            'include_task': False,
            'operator_note': 'audit test',
            'decided_by': 'pytest',
            'dry_run': True,
            'idempotency_key': 'phase19-step9-audit-test',
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert result['mode'] == 'dry_run'
    action_id = result['results'][0]['crm_apply_action_id']

    actions = client.get(f'/front-desk/lacrm-apply/actions?status=dry_run&sms_thread_id={thread_id}')
    assert actions.status_code == 200
    action_payload = actions.json()
    assert action_payload['total'] >= 1
    assert any(row['id'] == action_id for row in action_payload['actions'])

    detail = client.get(f'/front-desk/lacrm-apply/actions/{action_id}')
    assert detail.status_code == 200
    assert detail.json()['idempotency_key'].startswith('phase19-step9-audit-test')
    assert detail.json()['sms_thread']['id'] == thread_id

    readiness = client.get('/front-desk/lacrm-apply/readiness')
    assert readiness.status_code == 200
    readiness_payload = readiness.json()
    assert readiness_payload['safe_default_mode'] == 'dry_run'
    assert readiness_payload['dry_run_total'] >= 1
    assert 'blockers' in readiness_payload

    export = client.get('/front-desk/lacrm-apply/export?status=dry_run&limit=25')
    assert export.status_code == 200
    assert any(row['id'] == action_id for row in export.json()['rows'])
