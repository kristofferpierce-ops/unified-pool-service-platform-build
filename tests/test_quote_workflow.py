from fastapi.testclient import TestClient

from app.api.main import app


client = TestClient(app)


def test_quote_workflow_case_create_move_and_dashboard():
    create_response = client.post(
        '/quote-workflow/cases',
        json={
            'pipeline_slug': 'new_residential_services',
            'title': 'Quote for 123 Palm Ave weekly service',
            'requester_name': 'Mike Tester',
            'requester_phone': '+13055551212',
            'requester_email': 'mike@example.com',
            'description': 'Customer requested weekly service and startup chemistry pricing.',
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()
    assert created['stage_slug'] == 'info_costing'
    assert created['quote_number'].startswith('Q')

    move_response = client.post(
        f"/quote-workflow/cases/{created['id']}/move",
        json={
            'target_stage_slug': 'quoting',
            'moved_by': 'test_runner',
            'move_reason': 'Pricing worksheet started',
        },
    )
    assert move_response.status_code == 200
    moved = move_response.json()
    assert moved['stage_slug'] == 'quoting'

    follow_up_response = client.post(
        f"/quote-workflow/cases/{created['id']}/move",
        json={
            'target_stage_slug': 'follow_up',
            'moved_by': 'test_runner',
            'move_reason': 'Draft estimate sent',
        },
    )
    assert follow_up_response.status_code == 200
    follow_up = follow_up_response.json()
    assert follow_up['freshbooks_status'] == 'sent'
    assert follow_up['follow_up_due_on'] is not None

    viewed_response = client.post(f"/quote-workflow/cases/{created['id']}/viewed", json={})
    assert viewed_response.status_code == 200
    viewed = viewed_response.json()
    assert viewed['is_viewed'] is True
    assert viewed['last_viewed_at'] is not None

    dashboard_response = client.get('/quote-workflow/dashboard')
    assert dashboard_response.status_code == 200
    dashboard = dashboard_response.json()
    assert 'totals' in dashboard
    assert any(item['pipeline_slug'] == 'new_residential_services' for item in dashboard['pipelines'])


def test_quote_workflow_invalid_stage_move_rejected():
    create_response = client.post(
        '/quote-workflow/cases',
        json={
            'pipeline_slug': 'repairs',
            'title': 'Repair quote for invalid transition test',
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()

    move_response = client.post(
        f"/quote-workflow/cases/{created['id']}/move",
        json={
            'target_stage_slug': 'parts_ordered',
            'moved_by': 'test_runner',
            'move_reason': 'Should fail because ordering cannot happen directly from intake',
        },
    )
    assert move_response.status_code == 400
    assert 'not allowed' in move_response.json()['detail']
