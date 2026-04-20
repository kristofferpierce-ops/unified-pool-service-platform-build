from fastapi.testclient import TestClient

from app.api.main import app
from app.services.front_desk import clean_display_text, text_has_display_encoding_issue


client = TestClient(app)


def test_clean_display_text_repairs_common_mojibake():
    raw = 'This Is what Iâm seeing in work order. Donât record this.'
    cleaned = clean_display_text(raw)
    assert 'â' not in cleaned
    assert 'I’m' in cleaned or "I'm" in cleaned
    assert text_has_display_encoding_issue(raw) is True


def test_text_quality_endpoints_report_display_only_issues():
    body = 'This Is what Iâm seeing in work order, but donât change the raw record.'
    payload = {
        'payload': {
            'event_kind': 'sms',
            'external_id': 'step13-text-quality-msg-1',
            'message_external_id': 'step13-text-quality-msg-1',
            'direction': 'Inbound',
            'body': body,
            'summary': body,
            'transcript': body,
            'external_phone': '+13055551313',
            'internal_phone': '+13055550000',
            'from_phone': '+13055551313',
            'to_phone': '+13055550000',
            'occurred_at': '2026-04-20T13:13:00Z',
            'bridge_context': {'source': 'message_sync', 'bridge_db': 'platform_event_outbox'},
        }
    }
    response = client.post('/connectors/ringcentral/events', json=payload)
    assert response.status_code == 200
    thread_id = response.json()['materialized']['sms_thread_id']

    detail = client.get(f'/front-desk/sms-threads/{thread_id}')
    assert detail.status_code == 200
    detail_payload = detail.json()
    assert detail_payload['text_quality']['summary_has_encoding_issue'] is True
    assert 'â' not in detail_payload['display_summary']
    assert detail_payload['messages'][0]['text_quality']['body_has_encoding_issue'] is True

    summary = client.get('/front-desk/text-quality/summary?sample_limit=5')
    assert summary.status_code == 200
    summary_payload = summary.json()
    assert summary_payload['safe_mode'] == 'display_only_no_raw_mutation'
    assert summary_payload['sms_messages_with_encoding_issues'] >= 1

    samples = client.get('/front-desk/text-quality/samples?kind=sms_messages&only_issues=true&limit=10')
    assert samples.status_code == 200
    sample_payload = samples.json()
    assert sample_payload['total'] >= 1
    assert any('â' in row['raw_preview'] and 'â' not in row['display_preview'] for row in sample_payload['samples'])
