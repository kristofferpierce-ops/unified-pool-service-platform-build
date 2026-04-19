from fastapi.testclient import TestClient

from app.api.main import app


client = TestClient(app)


def test_bridge_direct_sms_payload_ingests_and_dedupes():
    payload = {
        'payload': {
            'event': '/restapi/v1.0/account/~/extension/~/message-store/instant?type=SMS',
            'uuid': 'bridge-direct-sms-1',
            'timestamp': '2026-04-19T13:30:00Z',
            'body': {
                'id': 'bridge-msg-1',
                'type': 'SMS',
                'direction': 'Inbound',
                'subject': 'Today text from 99 Sample Ave.',
                'from': {'phoneNumber': '+13055550199', 'name': 'Pat'},
                'to': [{'phoneNumber': '+13055550000'}],
                'creationTime': '2026-04-19T13:30:00Z',
            },
            'bridge_context': {'source': 'message_sync'},
        }
    }

    first = client.post('/connectors/ringcentral/events', json=payload)
    assert first.status_code == 200
    assert first.json()['normalized_payload']['event_kind'] == 'sms'
    assert first.json()['normalized_payload']['external_phone'] == '+13055550199'
    assert first.json()['materialized']['sms_message_id']

    second = client.post('/connectors/ringcentral/events', json=payload)
    assert second.status_code == 200
    assert second.json()['materialized']['deduped'] is True


def test_bridge_telephony_parties_payload_ingests_call():
    payload = {
        'payload': {
            'event': '/restapi/v1.0/account/~/extension/~/telephony/sessions',
            'uuid': 'bridge-call-1',
            'body': {
                'telephonySessionId': 'session-bridge-call-1',
                'eventTime': '2026-04-19T13:35:00Z',
                'direction': 'Inbound',
                'parties': [
                    {
                        'from': {'phoneNumber': '+13055550200', 'name': 'Jordan'},
                        'to': {'phoneNumber': '+13055550000', 'extensionId': '101'},
                        'extensionId': '101',
                    }
                ],
                'sessionStatus': {'code': 'Disconnected'},
            },
        }
    }

    response = client.post('/connectors/ringcentral/events', json=payload)
    assert response.status_code == 200
    normalized = response.json()['normalized_payload']
    assert normalized['event_kind'] == 'call'
    assert normalized['telephony_session_id'] == 'session-bridge-call-1'
    assert normalized['external_phone'] == '+13055550200'
    assert normalized['internal_phone'] == '+13055550000'
