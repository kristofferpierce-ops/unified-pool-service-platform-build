from fastapi.testclient import TestClient

from app.api.main import app


client = TestClient(app)


def _ingest_sms(message_id: str, body: str, phone: str = '+13055550950') -> int:
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
            'occurred_at': '2026-04-19T21:00:00Z',
            'bridge_context': {'source': 'message_sync', 'bridge_db': 'platform_event_outbox'},
        }
    }
    response = client.post('/connectors/ringcentral/events', json=payload)
    assert response.status_code == 200
    return response.json()['materialized']['sms_thread_id']


def test_sms_thread_operator_action_flow():
    thread_id = _ingest_sms('operator-action-msg-1', 'Please follow up on this pool light.', '+13055550951')

    candidates = client.post(f'/front-desk/sms-threads/{thread_id}/candidates')
    assert candidates.status_code == 200
    assert isinstance(candidates.json(), list)

    approval = client.post(
        f'/front-desk/sms-threads/{thread_id}/approve',
        json={
            'chosen_contact_ref': 'manual:customer-1',
            'decided_by': 'pytest',
            'notes': 'Approved during operator action test',
        },
    )
    assert approval.status_code == 200
    assert approval.json()['operator_decision_id']

    task = client.post(
        f'/front-desk/sms-threads/{thread_id}/task',
        json={
            'title': 'Follow up on pool light',
            'assignee_ref': 'operator:front-desk',
            'due_date': '2026-04-20',
        },
    )
    assert task.status_code == 200
    assert task.json()['status'] == 'queued'

    route = client.post(
        '/front-desk/routing-preferences',
        json={
            'phone': '+13055550951',
            'route_mode': 'manual',
            'default_contact_ref': 'manual:customer-1',
            'favorite_refs': ['manual:customer-1'],
            'notes': 'Route to manual customer 1',
        },
    )
    assert route.status_code == 200
    assert route.json()['default_contact_ref'] == 'manual:customer-1'

    detail = client.get(f'/front-desk/sms-threads/{thread_id}')
    assert detail.status_code == 200
    data = detail.json()
    assert data['status'] == 'approved'
    assert data['operator_decisions']
    assert data['tasks']
    assert data['routing_preference']['default_contact_ref'] == 'manual:customer-1'

    summary = client.get('/front-desk/review-action-summary')
    assert summary.status_code == 200
    summary_data = summary.json()
    assert summary_data['operator_decisions_total'] >= 1
    assert summary_data['task_links_total'] >= 1
    assert summary_data['routing_preferences_total'] >= 1
