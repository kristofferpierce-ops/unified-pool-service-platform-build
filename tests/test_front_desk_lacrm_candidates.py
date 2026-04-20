from fastapi.testclient import TestClient

from app.api.main import app


client = TestClient(app)


def _ingest_sms(message_id: str, body: str, phone: str = '+13055550970') -> int:
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
            'occurred_at': '2026-04-19T22:45:00Z',
            'bridge_context': {'source': 'message_sync', 'bridge_db': 'platform_event_outbox'},
        }
    }
    response = client.post('/connectors/ringcentral/events', json=payload)
    assert response.status_code == 200
    return response.json()['materialized']['sms_thread_id']


def test_lacrm_search_without_api_key_is_safe():
    response = client.get('/front-desk/lacrm/search?q=Mike&limit=3')
    assert response.status_code == 200
    data = response.json()
    assert data['mode'] in {'not_configured', 'live_search', 'error'}
    assert 'contacts' in data


def test_sms_thread_lacrm_candidate_import_with_sample_contact():
    thread_id = _ingest_sms('lacrm-candidate-msg-1', 'Mike at 123 Palm Ave needs a call back.', '+13055550971')
    response = client.post(
        f'/front-desk/sms-threads/{thread_id}/lacrm-candidates',
        json={
            'search_terms': 'Mike Palm',
            'limit': 5,
            'store': True,
            'sample_contacts': [
                {
                    'ContactId': 'lacrm-test-123',
                    'Name': 'Mike Palm',
                    'CompanyName': 'Palm Ave House',
                    'Phone': '+13055550971',
                    'Email': 'mike@example.test',
                }
            ],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data['count'] == 1
    assert data['candidates'][0]['ref'] == 'lacrm_contact:lacrm-test-123'
    assert data['candidates'][0]['score'] >= 0.9

    detail = client.get(f'/front-desk/sms-threads/{thread_id}')
    assert detail.status_code == 200
    candidates = detail.json()['candidates']
    assert any(candidate['contact_ref'] == 'lacrm_contact:lacrm-test-123' for candidate in candidates)

    preview = client.post(
        f'/front-desk/sms-threads/{thread_id}/lacrm-apply-preview',
        json={
            'chosen_contact_ref': 'lacrm_contact:lacrm-test-123',
            'include_note': True,
            'include_task': False,
            'dry_run': True,
        },
    )
    assert preview.status_code == 200
    assert preview.json()['contact_id'] == 'lacrm-test-123'
