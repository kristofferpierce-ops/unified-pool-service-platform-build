"""Normalize raw Skimmer payloads into source-neutral canonical dicts.

Pure functions (no DB) so they are trivially testable and unaffected by whether
the data came from fixtures or the live API.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any


def _s(value: Any) -> str:
    return str(value).strip() if value is not None else ''


def _f(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_date(value: Any) -> date | None:
    text = _s(value)
    if not text:
        return None
    text = text.replace('Z', '+00:00')
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        for fmt in ('%Y-%m-%d', '%m/%d/%Y'):
            try:
                return datetime.strptime(text[:10], fmt).date()
            except ValueError:
                continue
    return None


def normalize_customer(raw: dict) -> dict:
    first, last, company = _s(raw.get('firstName')), _s(raw.get('lastName')), _s(raw.get('companyName'))
    display = company or f'{first} {last}'.strip() or _s(raw.get('id'))
    return {
        'external_id': _s(raw.get('id')),
        'display_name': display,
        'company_name': company,
        'email': _s(raw.get('primaryEmail')),
        'phone': _s(raw.get('mobilePhone')),
        'address': _s(raw.get('billingAddress')),
        'city': _s(raw.get('billingCity')),
        'state': _s(raw.get('billingState')),
        'zip': _s(raw.get('billingZip')),
        'inactive': bool(raw.get('isInactive') or raw.get('deleted')),
    }


def normalize_service_location(raw: dict) -> dict:
    return {
        'external_id': _s(raw.get('id')),
        'customer_external_id': _s(raw.get('customerId')),
        'name': _s(raw.get('name')) or _s(raw.get('address')),
        'address': _s(raw.get('address')),
        'city': _s(raw.get('city')),
        'state': _s(raw.get('state')),
        'zip': _s(raw.get('zip')),
        'latitude': _f(raw.get('latitude')),
        'longitude': _f(raw.get('longitude')),
    }


def normalize_body_of_water(raw: dict) -> dict:
    return {
        'external_id': _s(raw.get('id')),
        'service_location_external_id': _s(raw.get('serviceLocationId')),
        'name': _s(raw.get('name')) or 'Pool',
        'gallons': _f(raw.get('gallons')),
        'baseline_filter_pressure': _f(raw.get('baselineFilterPressure')),
    }


def normalize_chemical(raw: dict) -> dict:
    return {
        'name': _s(raw.get('name')),
        'quantity': _f(raw.get('quantity')),
        'unit': _s(raw.get('unit')),
    }


def normalize_work_order(raw: dict) -> dict:
    minutes_actual = raw.get('actualMinutes')
    minutes = _f(minutes_actual) if minutes_actual not in (None, '') else _f(raw.get('estimatedMinutes'))
    return {
        'external_id': _s(raw.get('id')),
        'customer_external_id': _s(raw.get('customerId')),
        'service_location_external_id': _s(raw.get('serviceLocationId')),
        'service_date': parse_date(raw.get('serviceDate')),
        'estimated_minutes': _f(raw.get('estimatedMinutes')),
        'actual_minutes': minutes,
        'labor_cost': _f(raw.get('laborCost')),
        'price': _f(raw.get('price')),
        'technician': _s(raw.get('technician')),
        'work_needed': _s(raw.get('workNeeded')),
        'chemicals': [normalize_chemical(c) for c in (raw.get('chemicalsUsed') or []) if isinstance(c, dict)],
    }


def normalize_route(raw: dict) -> dict:
    return {
        'external_id': _s(raw.get('id')),
        'name': _s(raw.get('name')),
        'route_date': parse_date(raw.get('routeDate')),
        'technician': _s(raw.get('technician')),
        'work_order_external_ids': [_s(x) for x in (raw.get('workOrderIds') or [])],
    }


NORMALIZERS = {
    'customer': normalize_customer,
    'service_location': normalize_service_location,
    'body_of_water': normalize_body_of_water,
    'work_order': normalize_work_order,
    'route': normalize_route,
}
