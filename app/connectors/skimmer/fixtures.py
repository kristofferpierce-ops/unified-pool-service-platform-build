"""Sample Skimmer API payloads, shaped to the documented Skimmer Public API.

Used by SkimmerClient in fixture mode so the connector is fully testable before
live API credentials exist. Field names mirror the real API (camelCase, string
ids, ISO dates) so the normalizer works unchanged when live data arrives.
"""
from __future__ import annotations

SAMPLE: dict[str, list[dict]] = {
    'customers': [
        {
            'id': 'cust-001', 'firstName': 'Mateo', 'lastName': 'Alvarez', 'companyName': '',
            'primaryEmail': 'mateo@example.com', 'mobilePhone': '+13055551201',
            'billingAddress': '18 Palm Ave', 'billingCity': 'Key West', 'billingState': 'FL',
            'billingZip': '33040', 'isInactive': False, 'deleted': False,
            'createdAt': '2025-01-10T15:00:00Z', 'updatedAt': '2026-06-01T12:00:00Z',
        },
        {
            'id': 'cust-002', 'firstName': '', 'lastName': '', 'companyName': 'Sunset Resort HOA',
            'primaryEmail': 'ops@sunsetresort.example', 'mobilePhone': '+13055551302',
            'billingAddress': '900 Ocean Dr', 'billingCity': 'Key West', 'billingState': 'FL',
            'billingZip': '33040', 'isInactive': False, 'deleted': False,
            'createdAt': '2024-08-25T15:00:00Z', 'updatedAt': '2026-05-20T09:00:00Z',
        },
    ],
    'service_locations': [
        {
            'id': 'sl-100', 'customerId': 'cust-001', 'name': 'Alvarez Residence',
            'address': '18 Palm Ave', 'city': 'Key West', 'state': 'FL', 'zip': '33040',
            'latitude': 24.5551, 'longitude': -81.7800, 'deleted': False,
        },
        {
            'id': 'sl-200', 'customerId': 'cust-002', 'name': 'Sunset Resort Main Pool',
            'address': '900 Ocean Dr', 'city': 'Key West', 'state': 'FL', 'zip': '33040',
            'latitude': 24.5460, 'longitude': -81.8000, 'deleted': False,
        },
    ],
    'bodies_of_water': [
        {
            'id': 'bow-100', 'serviceLocationId': 'sl-100', 'name': 'Backyard Pool',
            'gallons': 15000, 'baselineFilterPressure': 18.0, 'notes': '', 'deleted': False,
        },
        {
            'id': 'bow-200', 'serviceLocationId': 'sl-200', 'name': 'Resort Main Pool',
            'gallons': 68000, 'baselineFilterPressure': 22.0, 'notes': 'Commercial vessel', 'deleted': False,
        },
    ],
    'work_orders': [
        {
            'id': 'wo-5001', 'customerId': 'cust-001', 'serviceLocationId': 'sl-100',
            'serviceDate': '2026-06-08T00:00:00Z', 'estimatedMinutes': 30, 'actualMinutes': 34,
            'laborCost': 22.50, 'price': 90.00, 'technician': 'Dana R.',
            'workNeeded': 'Weekly service + balance',
            'chemicalsUsed': [
                {'name': 'Liquid Chlorine 12%', 'quantity': 1.5, 'unit': 'gal'},
                {'name': 'Muriatic Acid', 'quantity': 0.25, 'unit': 'gal'},
            ],
        },
        {
            'id': 'wo-5002', 'customerId': 'cust-001', 'serviceLocationId': 'sl-100',
            'serviceDate': '2026-06-15T00:00:00Z', 'estimatedMinutes': 30, 'actualMinutes': 28,
            'laborCost': 22.50, 'price': 90.00, 'technician': 'Dana R.',
            'workNeeded': 'Weekly service',
            'chemicalsUsed': [
                {'name': 'Liquid Chlorine 12%', 'quantity': 1.25, 'unit': 'gal'},
            ],
        },
        {
            'id': 'wo-5003', 'customerId': 'cust-002', 'serviceLocationId': 'sl-200',
            'serviceDate': '2026-06-09T00:00:00Z', 'estimatedMinutes': 60, 'actualMinutes': 75,
            'laborCost': 45.00, 'price': 240.00, 'technician': 'Priya S.',
            'workNeeded': 'Commercial service + filter check',
            'chemicalsUsed': [
                {'name': 'Liquid Chlorine 12%', 'quantity': 6.0, 'unit': 'gal'},
                {'name': 'Sodium Bicarbonate', 'quantity': 8.0, 'unit': 'lb'},
            ],
        },
    ],
    'routes': [
        {
            'id': 'route-70', 'name': 'Monday South', 'routeDate': '2026-06-08T00:00:00Z',
            'technician': 'Dana R.', 'workOrderIds': ['wo-5001'],
        },
        {
            'id': 'route-71', 'name': 'Tuesday Commercial', 'routeDate': '2026-06-09T00:00:00Z',
            'technician': 'Priya S.', 'workOrderIds': ['wo-5003'],
        },
    ],
}
