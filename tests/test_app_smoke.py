from fastapi.testclient import TestClient

from app.api.main import app


client = TestClient(app)


def test_health():
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


def test_bootstrap_and_sources():
    bootstrap = client.post('/admin/bootstrap')
    assert bootstrap.status_code == 200
    response = client.get('/connectors/sources')
    assert response.status_code == 200
    slugs = {item['slug'] for item in response.json()}
    assert 'ringcentral' in slugs
    assert 'lacrm' in slugs


def test_ringcentral_sms_ingest_and_queue():
    payload = {
        'payload': {
            'event': '/restapi/v1.0/account/~/extension/~/message-store/instant?type=SMS',
            'body': {
                'event': '/restapi/v1.0/account/~/extension/~/message-store/instant?type=SMS',
                'message': {
                    'id': 'msg-test-1',
                    'direction': 'Inbound',
                    'subject': 'Hi this is Mike at 123 Palm Ave.',
                    'from': {'phoneNumber': '+13055551212', 'name': 'Mike'},
                    'to': [{'phoneNumber': '+13055550000'}],
                    'creationTime': '2026-03-18T16:30:00+00:00',
                },
            },
        }
    }
    ingested = client.post('/connectors/ringcentral/events', json=payload)
    assert ingested.status_code == 200
    queue = client.get('/front-desk/queue')
    assert queue.status_code == 200
    assert isinstance(queue.json()['sms_threads'], list)
