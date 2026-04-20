from fastapi.testclient import TestClient

from app.api.main import app


client = TestClient(app)


def _ingest_sms(message_id: str, body: str, phone: str = '+13055551010') -> int:
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
            'occurred_at': '2026-04-20T10:10:00Z',
            'bridge_context': {'source': 'message_sync', 'bridge_db': 'platform_event_outbox'},
        }
    }
    response = client.post('/connectors/ringcentral/events', json=payload)
    assert response.status_code == 200
    return response.json()['materialized']['sms_thread_id']


def test_step10_live_apply_requires_arm_phrase_and_api_key(monkeypatch):
    monkeypatch.setenv('PLATFORM_LACRM_LIVE_WRITE_ENABLED', 'true')
    monkeypatch.delenv('PLATFORM_LACRM_LIVE_WRITE_ARMED', raising=False)
    monkeypatch.delenv('LACRM_API_KEY', raising=False)
    monkeypatch.setenv('PLATFORM_LACRM_LIVE_WRITE_CONFIRMATION_PHRASE', 'WRITE TO LACRM')

    thread_id = _ingest_sms('step10-live-readiness-msg-1', 'Step 10 live readiness test.', '+13055551011')

    # First create dry-run history, which is required before a future live apply can pass readiness.
    dry_run = client.post(
        f'/front-desk/sms-threads/{thread_id}/lacrm-apply',
        json={
            'chosen_contact_ref': 'lacrm_contact:step10-contact-1',
            'include_note': True,
            'include_task': False,
            'operator_note': 'step10 dry run',
            'decided_by': 'pytest',
            'dry_run': True,
            'idempotency_key': 'phase19-step10-dry-run',
        },
    )
    assert dry_run.status_code == 200
    assert dry_run.json()['mode'] == 'dry_run'

    readiness = client.get('/front-desk/lacrm-apply/live-readiness')
    assert readiness.status_code == 200
    readiness_payload = readiness.json()
    assert readiness_payload['safe_default_mode'] == 'dry_run'
    assert readiness_payload['gates']['live_write_enabled'] is True
    assert readiness_payload['gates']['live_write_armed'] is False
    assert readiness_payload['ready_for_live_apply'] is False
    assert any('ARMED' in blocker for blocker in readiness_payload['blockers'])

    blocked = client.post(
        f'/front-desk/sms-threads/{thread_id}/lacrm-apply',
        json={
            'chosen_contact_ref': 'lacrm_contact:step10-contact-1',
            'include_note': True,
            'include_task': False,
            'operator_note': 'step10 blocked live attempt',
            'decided_by': 'pytest',
            'dry_run': False,
            'confirm_live_write': True,
            'live_confirmation_phrase': 'WRITE TO LACRM',
            'idempotency_key': 'phase19-step10-live-blocked',
        },
    )
    assert blocked.status_code == 200
    blocked_payload = blocked.json()
    assert blocked_payload['mode'] == 'blocked'
    assert blocked_payload['results'][0]['status'] == 'blocked'
    assert 'PLATFORM_LACRM_LIVE_WRITE_ARMED' in blocked_payload['live_block_reason']
    assert 'LACRM_API_KEY' in blocked_payload['live_block_reason']

    wrong_phrase = client.get('/front-desk/lacrm-apply/live-readiness?submitted_phrase=WRONG')
    assert wrong_phrase.status_code == 200
    assert wrong_phrase.json()['gates']['confirmation_phrase_matched'] is False
    assert any('phrase' in blocker.lower() for blocker in wrong_phrase.json()['blockers'])
