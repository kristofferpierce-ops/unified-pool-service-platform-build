from fastapi.testclient import TestClient

from app.api.main import app
from app.services.front_desk import clean_display_text


client = TestClient(app)


def _ingest_sms(message_id: str, body: str, phone: str = '+13055550999') -> dict:
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
            'occurred_at': '2026-04-19T20:00:00Z',
            'bridge_context': {'source': 'message_sync', 'bridge_db': 'platform_event_outbox'},
        }
    }
    response = client.post('/connectors/ringcentral/events', json=payload)
    assert response.status_code == 200
    return response.json()


def test_clean_display_text_repairs_common_mojibake():
    assert clean_display_text('I donât see it') == 'I don’t see it'


def test_sms_thread_review_list_and_detail():
    ingested = _ingest_sms('review-parity-msg-1', 'I donât see the pool light turn on.', '+13055550901')
    thread_id = ingested['materialized']['sms_thread_id']

    listing = client.get('/front-desk/sms-threads', params={'external_phone': '+13055550901', 'limit': 5})
    assert listing.status_code == 200
    rows = listing.json()['threads']
    assert rows
    assert rows[0]['message_count'] >= 1
    assert rows[0]['source'] == 'message_sync'

    detail = client.get(f'/front-desk/sms-threads/{thread_id}')
    assert detail.status_code == 200
    body = detail.json()
    assert body['id'] == thread_id
    assert body['messages']
    assert body['messages'][0]['display_body'] == 'I don’t see the pool light turn on.'
    assert body['provenance']['bridge_context']['bridge_db'] == 'platform_event_outbox'


def test_bridge_review_summary_endpoint():
    _ingest_sms('review-summary-msg-1', 'Summary endpoint check', '+13055550902')
    response = client.get('/front-desk/bridge-review-summary')
    assert response.status_code == 200
    data = response.json()
    assert data['sms_threads_total'] >= 1
    assert data['sms_messages_total'] >= 1
    assert isinstance(data['latest_threads'], list)
