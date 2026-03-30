from __future__ import annotations

from datetime import datetime
from math import pi
from typing import Any

from sqlmodel import Session, select

from app.connectors.heritage.client import HeritageAPIError, get_heritage_client, get_heritage_connection_status
from app.models.heater_quote_tables import HeaterQuoteCandidate, HeaterQuoteRun
from app.models.quote_tables import QuoteCaseExternalLink
from app.services.quote_workflow import add_external_link, get_quote_case, serialize_quote_case
from app.services.system_settings import get_setting, set_setting
from app.utils.serialization import dumps, loads

DEFAULT_HEATER_QUOTE_CONFIG: dict[str, Any] = {
    'version': 'platform_block_2a1_heater_quote',
    'defaults': {
        'shape': 'direct',
        'desired_heatup_hours': 24.0,
        'heater_kind_preference': 'auto',
        'fuel_preference': 'auto',
        'unit_count': 1,
    },
    'sizing': {
        'gallons_to_pounds': 8.34,
        'heat_pump_surface_factor': 12.0,
        'wind_rules': [
            {'minimum_mph': 10.0, 'multiplier': 2.0},
            {'minimum_mph': 5.0, 'multiplier': 1.25},
            {'minimum_mph': 0.0, 'multiplier': 1.0},
        ],
        'ideal_min_ratio': 0.85,
        'ideal_max_ratio': 1.25,
        'viable_min_ratio': 0.70,
        'viable_max_ratio': 1.75,
        'low_ambient_heat_pump_penalty': 20.0,
        'low_ambient_threshold_f': 55.0,
    },
    'package_profiles': {
        'gas_standard': {
            'label': 'Gas standard install',
            'applies_to': ['gas'],
            'default_options': {
                'include_bypass_kit': True,
                'include_pad_kit': True,
                'include_gas_allowance': True,
                'include_electrical_allowance': False,
                'include_automation_integration': False,
                'include_startup_visit': True,
            },
            'line_items': {
                'bypass_kit': {'name': 'PVC bypass and union kit', 'description': 'Unions, bypass plumbing, and tie-in materials for heater install.', 'amount': 185.0, 'qty_mode': 'per_system'},
                'pad_kit': {'name': 'Heater equipment pad / stand kit', 'description': 'Equipment base materials for level heater placement.', 'amount': 180.0, 'qty_mode': 'per_system'},
                'gas_allowance': {'name': 'Gas piping allowance', 'description': 'Allowance for local gas tie-in materials and fittings.', 'amount': 650.0, 'qty_mode': 'per_system'},
                'automation_integration': {'name': 'Automation integration allowance', 'description': 'Low-voltage integration and heater enable wiring into existing controls.', 'amount': 350.0, 'qty_mode': 'per_system'},
                'startup_visit': {'name': 'Startup and commissioning visit', 'description': 'Final start-up, combustion or flow check, and staff walk-through.', 'amount': 295.0, 'qty_mode': 'per_system'},
            },
        },
        'heat_pump_standard': {
            'label': 'Heat pump standard install',
            'applies_to': ['heat_pump', 'heat_cool', 'heat_chill'],
            'default_options': {
                'include_bypass_kit': True,
                'include_pad_kit': True,
                'include_gas_allowance': False,
                'include_electrical_allowance': True,
                'include_automation_integration': False,
                'include_startup_visit': True,
            },
            'line_items': {
                'bypass_kit': {'name': 'PVC bypass and union kit', 'description': 'Unions, bypass plumbing, and tie-in materials for heater install.', 'amount': 185.0, 'qty_mode': 'per_system'},
                'pad_kit': {'name': 'Heater equipment pad / stand kit', 'description': 'Equipment base materials for level heater placement.', 'amount': 220.0, 'qty_mode': 'per_system'},
                'electrical_allowance': {'name': 'Electrical allowance', 'description': 'Allowance for disconnect, whip, breaker, and basic high-voltage tie-in.', 'amount': 725.0, 'qty_mode': 'per_system'},
                'automation_integration': {'name': 'Automation integration allowance', 'description': 'Low-voltage integration and heater enable wiring into existing controls.', 'amount': 350.0, 'qty_mode': 'per_system'},
                'startup_visit': {'name': 'Startup and commissioning visit', 'description': 'Final start-up, flow verification, and operator walk-through.', 'amount': 295.0, 'qty_mode': 'per_system'},
            },
        },
    },
    'labor_profiles': {
        'standard': {'label': 'Standard access', 'labor_rate': 125.0, 'base_hours': 2.0, 'hours_per_unit': 8.0},
        'simple_swap': {'label': 'Simple swap', 'labor_rate': 125.0, 'base_hours': 1.0, 'hours_per_unit': 5.0},
        'tight_access': {'label': 'Tight access / difficult install', 'labor_rate': 135.0, 'base_hours': 3.0, 'hours_per_unit': 10.0},
    },
    'heritage': {
        'sync_mode': 'dry_run',
        'vendor_name': 'Heritage Pool Supply',
        'fallback_catalog': [
            {
                'vendor_name': 'Fallback Planning Catalog',
                'brand_name': 'Planning',
                'model_name': 'Planning Gas Heater 250K',
                'sku': 'PLAN-GAS-250',
                'heater_kind': 'gas',
                'fuel_type': 'natural_gas',
                'capacity_btu_per_hr': 250000.0,
                'price': None,
                'currency_code': 'USD',
                'availability_status': 'planning only',
                'branch_name': '',
            },
            {
                'vendor_name': 'Fallback Planning Catalog',
                'brand_name': 'Planning',
                'model_name': 'Planning Gas Heater 399K',
                'sku': 'PLAN-GAS-399',
                'heater_kind': 'gas',
                'fuel_type': 'natural_gas',
                'capacity_btu_per_hr': 399000.0,
                'price': None,
                'currency_code': 'USD',
                'availability_status': 'planning only',
                'branch_name': '',
            },
            {
                'vendor_name': 'Fallback Planning Catalog',
                'brand_name': 'Planning',
                'model_name': 'Planning Heat Pump 110K',
                'sku': 'PLAN-HP-110',
                'heater_kind': 'heat_pump',
                'fuel_type': 'electric',
                'capacity_btu_per_hr': 110000.0,
                'price': None,
                'currency_code': 'USD',
                'availability_status': 'planning only',
                'branch_name': '',
            },
            {
                'vendor_name': 'Fallback Planning Catalog',
                'brand_name': 'Planning',
                'model_name': 'Planning Heat Pump 140K',
                'sku': 'PLAN-HP-140',
                'heater_kind': 'heat_pump',
                'fuel_type': 'electric',
                'capacity_btu_per_hr': 140000.0,
                'price': None,
                'currency_code': 'USD',
                'availability_status': 'planning only',
                'branch_name': '',
            },
            {
                'vendor_name': 'Fallback Planning Catalog',
                'brand_name': 'Planning',
                'model_name': 'Planning Heat and Cool 140K',
                'sku': 'PLAN-HC-140',
                'heater_kind': 'heat_cool',
                'fuel_type': 'electric',
                'capacity_btu_per_hr': 140000.0,
                'price': None,
                'currency_code': 'USD',
                'availability_status': 'planning only',
                'branch_name': '',
            },
        ],
        'notes': 'Live Heritage pricing needs a normalized catalog feed or configured catalog URL plus account id and API key. Until then, the tool uses a starter planning catalog so the module still returns recommendation bands instead of an empty result.',
    },
}


def _merge_heater_quote_config(config: dict[str, Any] | None) -> dict[str, Any]:
    merged = loads(dumps(DEFAULT_HEATER_QUOTE_CONFIG), {})
    if isinstance(config, dict):
        merged.update({key: value for key, value in config.items() if key not in {'defaults', 'sizing', 'heritage', 'package_profiles', 'labor_profiles'}})
        merged['defaults'].update(config.get('defaults') or {})
        merged['sizing'].update(config.get('sizing') or {})
        merged['heritage'].update(config.get('heritage') or {})
        for key, value in (config.get('package_profiles') or {}).items():
            if isinstance(value, dict):
                base_profile = merged['package_profiles'].get(key, {}) if isinstance(merged.get('package_profiles', {}).get(key), dict) else {}
                merged.setdefault('package_profiles', {})[key] = {**base_profile, **value}
        for key, value in (config.get('labor_profiles') or {}).items():
            if isinstance(value, dict):
                base_labor = merged['labor_profiles'].get(key, {}) if isinstance(merged.get('labor_profiles', {}).get(key), dict) else {}
                merged.setdefault('labor_profiles', {})[key] = {**base_labor, **value}
    merged['defaults'].setdefault('unit_count', 1)
    if not isinstance(merged['heritage'].get('fallback_catalog'), list) or not merged['heritage'].get('fallback_catalog'):
        merged['heritage']['fallback_catalog'] = DEFAULT_HEATER_QUOTE_CONFIG['heritage']['fallback_catalog']
    merged.setdefault('package_profiles', DEFAULT_HEATER_QUOTE_CONFIG['package_profiles'])
    merged.setdefault('labor_profiles', DEFAULT_HEATER_QUOTE_CONFIG['labor_profiles'])
    merged['version'] = DEFAULT_HEATER_QUOTE_CONFIG['version']
    return merged



def ensure_heater_quote_settings(session: Session) -> dict[str, Any]:
    config = get_setting(session, 'heater_quote_config')
    merged = _merge_heater_quote_config(config)
    if config != merged:
        set_setting(
            session,
            'heater_quote_config',
            merged,
            'Admin editable heater quote configuration for sizing heuristics, Heritage catalog sync mode, and fallback catalog items.',
        )
    return merged



def get_heater_quote_settings(session: Session) -> dict[str, Any]:
    return ensure_heater_quote_settings(session)



def _shape_multiplier(shape: str) -> float:
    normalized = (shape or 'direct').strip().lower()
    if normalized in {'oval', 'ellipse'}:
        return pi / 4.0
    if normalized in {'circle', 'round'}:
        return pi / 4.0
    return 1.0



def calculate_volume_gallons(
    *,
    direct_gallons: float | None,
    shape: str,
    length_ft: float,
    width_ft: float,
    avg_depth_ft: float,
    diameter_ft: float,
) -> float:
    if direct_gallons and direct_gallons > 0:
        return float(direct_gallons)
    normalized = (shape or 'direct').strip().lower()
    if normalized in {'circle', 'round'} and diameter_ft > 0 and avg_depth_ft > 0:
        radius_ft = diameter_ft / 2.0
        volume_cuft = pi * radius_ft * radius_ft * avg_depth_ft
        return volume_cuft * 7.48
    if length_ft > 0 and width_ft > 0 and avg_depth_ft > 0:
        volume_cuft = length_ft * width_ft * avg_depth_ft * _shape_multiplier(normalized)
        return volume_cuft * 7.48
    return 0.0



def calculate_surface_area_sqft(
    *,
    shape: str,
    length_ft: float,
    width_ft: float,
    diameter_ft: float,
    direct_gallons: float | None = None,
) -> float:
    normalized = (shape or 'direct').strip().lower()
    if normalized in {'circle', 'round'} and diameter_ft > 0:
        radius_ft = diameter_ft / 2.0
        return pi * radius_ft * radius_ft
    if length_ft > 0 and width_ft > 0:
        return length_ft * width_ft * _shape_multiplier(normalized)
    if direct_gallons and direct_gallons > 0:
        estimated_depth = 4.5
        return max(0.0, float(direct_gallons) / (7.48 * estimated_depth))
    return 0.0



def get_wind_multiplier(config: dict[str, Any], wind_mph: float) -> float:
    for rule in sorted(config.get('sizing', {}).get('wind_rules', []), key=lambda item: item.get('minimum_mph', 0), reverse=True):
        if wind_mph >= float(rule.get('minimum_mph', 0)):
            return float(rule.get('multiplier', 1.0))
    return 1.0



def calculate_heater_requirements(
    *,
    direct_gallons: float | None,
    shape: str,
    length_ft: float,
    width_ft: float,
    avg_depth_ft: float,
    diameter_ft: float,
    current_water_temp_f: float,
    target_water_temp_f: float,
    ambient_air_temp_f: float,
    desired_heatup_hours: float,
    wind_mph: float,
    covered: bool,
    config: dict[str, Any],
) -> dict[str, Any]:
    volume_gallons = calculate_volume_gallons(
        direct_gallons=direct_gallons,
        shape=shape,
        length_ft=length_ft,
        width_ft=width_ft,
        avg_depth_ft=avg_depth_ft,
        diameter_ft=diameter_ft,
    )
    surface_area_sqft = calculate_surface_area_sqft(
        shape=shape,
        length_ft=length_ft,
        width_ft=width_ft,
        diameter_ft=diameter_ft,
        direct_gallons=direct_gallons,
    )
    temperature_rise_f = max(0.0, float(target_water_temp_f) - float(current_water_temp_f))
    gallons_to_pounds = float(config.get('sizing', {}).get('gallons_to_pounds', 8.34))
    total_btu_required = volume_gallons * gallons_to_pounds * temperature_rise_f
    desired_hours = max(1.0, float(desired_heatup_hours or config.get('defaults', {}).get('desired_heatup_hours', 24.0)))
    heatup_btu_per_hr = total_btu_required / desired_hours if total_btu_required > 0 else 0.0
    maintenance_btu_per_hr = surface_area_sqft * temperature_rise_f * float(config.get('sizing', {}).get('heat_pump_surface_factor', 12.0))
    maintenance_btu_per_hr *= get_wind_multiplier(config, float(wind_mph or 0.0))
    recommended_btu_per_hr = max(heatup_btu_per_hr, maintenance_btu_per_hr)
    preferred_heater_kind = 'heat_pump'
    recommendation_note = 'Heat pump style sizing is reasonable when maintaining pool temperature over longer time windows.'
    if desired_hours <= 12 or ambient_air_temp_f < float(config.get('sizing', {}).get('low_ambient_threshold_f', 55.0)):
        preferred_heater_kind = 'gas'
        recommendation_note = 'A gas heater is often the better fit for fast heat-up targets or cooler ambient conditions.'
    if covered:
        recommendation_note += ' A pool cover should reduce heat loss during use, but this estimate stays conservative and does not discount the BTU target automatically.'
    return {
        'shape': shape,
        'volume_gallons': round(volume_gallons, 2),
        'surface_area_sqft': round(surface_area_sqft, 2),
        'temperature_rise_f': round(temperature_rise_f, 2),
        'ambient_air_temp_f': float(ambient_air_temp_f),
        'desired_heatup_hours': desired_hours,
        'wind_mph': float(wind_mph or 0.0),
        'covered': bool(covered),
        'total_btu_required': round(total_btu_required, 2),
        'heatup_btu_per_hr': round(heatup_btu_per_hr, 2),
        'maintenance_btu_per_hr': round(maintenance_btu_per_hr, 2),
        'recommended_btu_per_hr': round(recommended_btu_per_hr, 2),
        'preferred_heater_kind': preferred_heater_kind,
        'recommendation_note': recommendation_note,
        'wind_multiplier': round(get_wind_multiplier(config, float(wind_mph or 0.0)), 2),
    }



def _safe_load(blob: str | None) -> dict[str, Any]:
    if not blob:
        return {}
    loaded = loads(blob, {})
    return loaded if isinstance(loaded, dict) else {}



def _load_catalog_from_settings(config: dict[str, Any]) -> list[dict[str, Any]]:
    catalog = config.get('heritage', {}).get('fallback_catalog', [])
    return [item for item in catalog if isinstance(item, dict)]



def _load_catalog_from_heritage(config: dict[str, Any]) -> tuple[list[dict[str, Any]], str, list[str]]:
    heritage_config = config.get('heritage', {})
    sync_mode = str(heritage_config.get('sync_mode', 'dry_run') or 'dry_run')
    notes: list[str] = []
    if sync_mode != 'live':
        catalog = _load_catalog_from_settings(config)
        mode = 'fallback_catalog' if catalog else 'no_catalog'
        if not catalog:
            notes.append('Heritage live sync is not enabled, so the tool used only the local fallback catalog.')
        return catalog, mode, notes
    client = get_heritage_client()
    if client is None:
        catalog = _load_catalog_from_settings(config)
        mode = 'fallback_catalog' if catalog else 'no_catalog'
        notes.append('Heritage live sync is enabled in settings, but the required account id or API key was not found in environment variables.')
        return catalog, mode, notes
    try:
        catalog = client.fetch_catalog()
        if catalog:
            return catalog, 'heritage_live', notes
        notes.append('Heritage live sync returned no catalog items.')
    except HeritageAPIError as exc:
        notes.append(str(exc))
    catalog = _load_catalog_from_settings(config)
    mode = 'fallback_catalog' if catalog else 'no_catalog'
    if catalog:
        notes.append('The tool fell back to the local heater catalog because live Heritage catalog loading did not succeed.')
    return catalog, mode, notes



def _score_candidate(
    *,
    required_btu_per_hr: float,
    preferred_heater_kind: str,
    ambient_air_temp_f: float,
    config: dict[str, Any],
    candidate: dict[str, Any],
) -> tuple[float, str]:
    capacity = float(candidate.get('capacity_btu_per_hr') or 0)
    if capacity <= 0 or required_btu_per_hr <= 0:
        return 0.0, 'review'
    ratio = capacity / required_btu_per_hr
    sizing = config.get('sizing', {})
    ideal_min = float(sizing.get('ideal_min_ratio', 0.85))
    ideal_max = float(sizing.get('ideal_max_ratio', 1.25))
    viable_min = float(sizing.get('viable_min_ratio', 0.70))
    viable_max = float(sizing.get('viable_max_ratio', 1.75))
    if ratio < viable_min:
        band = 'underpowered'
    elif ratio < ideal_min:
        band = 'close_but_small'
    elif ratio <= ideal_max:
        band = 'ideal'
    elif ratio <= viable_max:
        band = 'viable_oversized'
    else:
        band = 'oversized'
    score = max(0.0, 100.0 - abs(ratio - 1.0) * 100.0)
    heater_kind = str(candidate.get('heater_kind') or '').strip().lower()
    fuel_type = str(candidate.get('fuel_type') or '').strip().lower()
    if preferred_heater_kind == 'gas' and (heater_kind == 'gas' or fuel_type in {'gas', 'natural_gas', 'propane'}):
        score += 8.0
    if preferred_heater_kind == 'heat_pump' and heater_kind in {'heat_pump', 'heat_cool', 'heat_chill'}:
        score += 8.0
    low_ambient_threshold = float(sizing.get('low_ambient_threshold_f', 55.0))
    if ambient_air_temp_f < low_ambient_threshold and heater_kind in {'heat_pump', 'heat_cool', 'heat_chill'}:
        score -= float(sizing.get('low_ambient_heat_pump_penalty', 20.0))
    if candidate.get('price') in (None, ''):
        score -= 5.0
    return round(score, 2), band



def rank_heater_candidates(
    *,
    summary: dict[str, Any],
    catalog: list[dict[str, Any]],
    heater_kind_preference: str,
    fuel_preference: str,
    unit_count: int,
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    preferred_heater_kind = heater_kind_preference if heater_kind_preference not in {'', 'auto'} else summary.get('preferred_heater_kind', 'auto')
    required_btu_per_hr = float(summary.get('recommended_btu_per_hr') or 0)
    total_btu_required = float(summary.get('total_btu_required') or 0)
    candidates: list[dict[str, Any]] = []
    for raw_candidate in catalog:
        heater_kind = str(raw_candidate.get('heater_kind') or '').strip().lower()
        fuel_type = str(raw_candidate.get('fuel_type') or '').strip().lower()
        if heater_kind and heater_kind not in {'gas', 'heat_pump', 'heat_cool', 'heat_chill'}:
            continue
        if heater_kind_preference not in {'', 'auto'} and heater_kind and heater_kind_preference != heater_kind:
            continue
        if fuel_preference not in {'', 'auto'} and fuel_type and fuel_preference != fuel_type:
            continue
        unit_count = max(1, int(unit_count or 1))
        capacity = float(raw_candidate.get('capacity_btu_per_hr') or 0)
        package_capacity = capacity * unit_count
        scored_candidate = {**raw_candidate, 'capacity_btu_per_hr': package_capacity}
        fit_score, band = _score_candidate(
            required_btu_per_hr=required_btu_per_hr,
            preferred_heater_kind=preferred_heater_kind,
            ambient_air_temp_f=float(summary.get('ambient_air_temp_f') or 0.0),
            config=config,
            candidate=scored_candidate,
        )
        total_price = (float(raw_candidate.get('price')) * unit_count) if raw_candidate.get('price') not in (None, '') else None
        estimated_heatup_hours = round(total_btu_required / package_capacity, 2) if package_capacity > 0 and total_btu_required > 0 else 0.0
        candidate = {
            'vendor_name': raw_candidate.get('vendor_name') or config.get('heritage', {}).get('vendor_name', 'Heritage Pool Supply'),
            'brand_name': raw_candidate.get('brand_name', ''),
            'model_name': raw_candidate.get('model_name') or raw_candidate.get('name') or raw_candidate.get('sku') or 'Unknown heater',
            'sku': raw_candidate.get('sku', ''),
            'heater_kind': heater_kind,
            'fuel_type': fuel_type,
            'unit_count': unit_count,
            'per_unit_capacity_btu_per_hr': capacity,
            'capacity_btu_per_hr': package_capacity,
            'per_unit_price': float(raw_candidate.get('price')) if raw_candidate.get('price') not in (None, '') else None,
            'price': total_price,
            'currency_code': raw_candidate.get('currency_code') or 'USD',
            'availability_status': raw_candidate.get('availability_status', ''),
            'branch_name': raw_candidate.get('branch_name', ''),
            'fit_score': fit_score,
            'recommendation_band': band,
            'estimated_heatup_hours': estimated_heatup_hours,
            'payload': {**raw_candidate, 'unit_count': unit_count, 'per_unit_capacity_btu_per_hr': capacity, 'package_capacity_btu_per_hr': package_capacity, 'per_unit_price': float(raw_candidate.get('price')) if raw_candidate.get('price') not in (None, '') else None, 'package_price': total_price},
        }
        candidates.append(candidate)
    candidates.sort(key=lambda item: (-float(item.get('fit_score') or 0), float(item.get('price') or 0) if item.get('price') not in (None, '') else float('inf')))
    for index, candidate in enumerate(candidates, start=1):
        candidate['rank_order'] = index
    return candidates



def create_heater_quote_run(
    session: Session,
    *,
    title: str = '',
    quote_case_id: int | None = None,
    direct_gallons: float | None = None,
    shape: str = 'direct',
    length_ft: float = 0.0,
    width_ft: float = 0.0,
    avg_depth_ft: float = 0.0,
    diameter_ft: float = 0.0,
    current_water_temp_f: float = 0.0,
    target_water_temp_f: float = 0.0,
    ambient_air_temp_f: float = 0.0,
    desired_heatup_hours: float = 24.0,
    wind_mph: float = 0.0,
    covered: bool = False,
    heater_kind_preference: str = 'auto',
    fuel_preference: str = 'auto',
    unit_count: int = 1,
) -> dict[str, Any]:
    if quote_case_id is not None and get_quote_case(session, quote_case_id) is None:
        raise ValueError('Quote case not found')
    config = get_heater_quote_settings(session)
    normalized_unit_count = max(1, int(unit_count or config.get('defaults', {}).get('unit_count', 1) or 1))
    summary = calculate_heater_requirements(
        direct_gallons=direct_gallons,
        shape=shape,
        length_ft=length_ft,
        width_ft=width_ft,
        avg_depth_ft=avg_depth_ft,
        diameter_ft=diameter_ft,
        current_water_temp_f=current_water_temp_f,
        target_water_temp_f=target_water_temp_f,
        ambient_air_temp_f=ambient_air_temp_f,
        desired_heatup_hours=desired_heatup_hours,
        wind_mph=wind_mph,
        covered=covered,
        config=config,
    )
    catalog, source_mode, notes = _load_catalog_from_heritage(config)
    summary['unit_count'] = normalized_unit_count
    summary['per_unit_target_btu_per_hr'] = round(float(summary.get('recommended_btu_per_hr') or 0) / normalized_unit_count, 2)
    if normalized_unit_count > 1:
        summary['recommendation_note'] += f' This scenario is being evaluated as {normalized_unit_count} identical heater units working together in parallel.'
    candidates = rank_heater_candidates(
        summary=summary,
        catalog=catalog,
        heater_kind_preference=heater_kind_preference,
        fuel_preference=fuel_preference,
        unit_count=normalized_unit_count,
        config=config,
    )
    now = datetime.utcnow()
    run = HeaterQuoteRun(
        quote_case_id=quote_case_id,
        title=title,
        shape=shape,
        heater_kind_preference=heater_kind_preference,
        fuel_preference=fuel_preference,
        volume_gallons=float(summary['volume_gallons']),
        surface_area_sqft=float(summary['surface_area_sqft']),
        current_water_temp_f=float(current_water_temp_f),
        target_water_temp_f=float(target_water_temp_f),
        ambient_air_temp_f=float(ambient_air_temp_f),
        desired_heatup_hours=float(summary['desired_heatup_hours']),
        wind_mph=float(wind_mph or 0.0),
        covered=bool(covered),
        total_btu_required=float(summary['total_btu_required']),
        maintenance_btu_per_hr=float(summary['maintenance_btu_per_hr']),
        heatup_btu_per_hr=float(summary['heatup_btu_per_hr']),
        recommended_btu_per_hr=float(summary['recommended_btu_per_hr']),
        source_mode=source_mode,
        summary_json=dumps({'summary': summary, 'notes': notes}),
        created_at=now,
        updated_at=now,
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    stored_candidates: list[HeaterQuoteCandidate] = []
    for candidate in candidates:
        stored = HeaterQuoteCandidate(
            run_id=run.id,
            rank_order=int(candidate['rank_order']),
            recommendation_band=str(candidate['recommendation_band']),
            vendor_name=str(candidate.get('vendor_name') or ''),
            brand_name=str(candidate.get('brand_name') or ''),
            model_name=str(candidate.get('model_name') or ''),
            sku=str(candidate.get('sku') or ''),
            heater_kind=str(candidate.get('heater_kind') or ''),
            fuel_type=str(candidate.get('fuel_type') or ''),
            capacity_btu_per_hr=float(candidate.get('capacity_btu_per_hr') or 0),
            estimated_heatup_hours=float(candidate.get('estimated_heatup_hours') or 0),
            price=float(candidate['price']) if candidate.get('price') not in (None, '') else None,
            currency_code=str(candidate.get('currency_code') or 'USD'),
            availability_status=str(candidate.get('availability_status') or ''),
            branch_name=str(candidate.get('branch_name') or ''),
            fit_score=float(candidate.get('fit_score') or 0),
            payload_json=dumps(candidate.get('payload') or {}),
            created_at=now,
        )
        session.add(stored)
        stored_candidates.append(stored)
    session.commit()
    for stored in stored_candidates:
        session.refresh(stored)
    return serialize_heater_quote_run(session, run.id)



def list_heater_quote_runs(session: Session, *, limit: int = 50) -> list[dict[str, Any]]:
    runs = list(session.exec(select(HeaterQuoteRun).order_by(HeaterQuoteRun.created_at.desc()).limit(limit)).all())
    return [serialize_heater_quote_run(session, run.id, include_candidates=False) for run in runs]



def get_heater_quote_run(session: Session, run_id: int) -> HeaterQuoteRun | None:
    return session.get(HeaterQuoteRun, run_id)



def list_heater_quote_candidates(session: Session, run_id: int) -> list[HeaterQuoteCandidate]:
    return list(session.exec(select(HeaterQuoteCandidate).where(HeaterQuoteCandidate.run_id == run_id).order_by(HeaterQuoteCandidate.rank_order)).all())



def serialize_heater_quote_run(session: Session, run_id: int, *, include_candidates: bool = True) -> dict[str, Any]:
    run = get_heater_quote_run(session, run_id)
    if run is None:
        raise ValueError('Heater quote run not found')
    payload = run.model_dump()
    summary_payload = _safe_load(run.summary_json)
    payload['summary'] = summary_payload.get('summary', {})
    payload['notes'] = summary_payload.get('notes', [])
    if include_candidates:
        payload['candidates'] = [
            {
                **candidate.model_dump(),
                'payload': _safe_load(candidate.payload_json),
            }
            for candidate in list_heater_quote_candidates(session, run_id)
        ]
    if run.quote_case_id:
        case = get_quote_case(session, run.quote_case_id)
        if case is not None:
            payload['quote_case'] = serialize_quote_case(session, case)
    return payload



def _default_package_profile_key(candidate_payload: dict[str, Any], config: dict[str, Any]) -> str:
    heater_kind = str(candidate_payload.get('heater_kind') or '').strip().lower()
    if heater_kind in {'heat_pump', 'heat_cool', 'heat_chill'}:
        return 'heat_pump_standard'
    return 'gas_standard'



def _line_template(profile: dict[str, Any], slug: str) -> dict[str, Any]:
    return (profile.get('line_items') or {}).get(slug, {}) if isinstance(profile, dict) else {}



def build_heater_package_preview(
    session: Session,
    *,
    run_id: int,
    candidate_id: int,
    package_profile: str = 'auto',
    labor_profile: str = 'standard',
    include_bypass_kit: bool | None = None,
    include_pad_kit: bool | None = None,
    include_gas_allowance: bool | None = None,
    include_electrical_allowance: bool | None = None,
    include_automation_integration: bool | None = None,
    include_startup_visit: bool | None = None,
    misc_materials_amount: float = 0.0,
    labor_rate_override: float | None = None,
) -> dict[str, Any]:
    run = get_heater_quote_run(session, run_id)
    if run is None:
        raise ValueError('Heater quote run not found')
    candidate = session.get(HeaterQuoteCandidate, candidate_id)
    if candidate is None or candidate.run_id != run_id:
        raise ValueError('Heater quote candidate not found')

    config = get_heater_quote_settings(session)
    summary_payload = _safe_load(run.summary_json)
    run_summary = summary_payload.get('summary', {}) if isinstance(summary_payload, dict) else {}
    candidate_payload = _safe_load(candidate.payload_json)
    unit_count = int(candidate_payload.get('unit_count') or run_summary.get('unit_count') or 1)
    currency_code = candidate.currency_code or 'USD'
    per_unit_price = candidate_payload.get('per_unit_price')
    if per_unit_price in (None, ''):
        per_unit_price = float(candidate.price or 0) / max(1, unit_count) if candidate.price not in (None, '') else 0.0
    else:
        per_unit_price = float(per_unit_price)

    profile_key = package_profile if package_profile not in {'', 'auto'} else _default_package_profile_key(candidate_payload or candidate.model_dump(), config)
    package_profiles = config.get('package_profiles', {}) if isinstance(config.get('package_profiles'), dict) else {}
    profile = package_profiles.get(profile_key)
    if not isinstance(profile, dict):
        raise ValueError(f'Unknown heater package profile: {profile_key}')
    labor_profiles = config.get('labor_profiles', {}) if isinstance(config.get('labor_profiles'), dict) else {}
    labor = labor_profiles.get(labor_profile)
    if not isinstance(labor, dict):
        raise ValueError(f'Unknown labor profile: {labor_profile}')

    defaults = profile.get('default_options') or {}
    options = {
        'include_bypass_kit': defaults.get('include_bypass_kit', True) if include_bypass_kit is None else bool(include_bypass_kit),
        'include_pad_kit': defaults.get('include_pad_kit', True) if include_pad_kit is None else bool(include_pad_kit),
        'include_gas_allowance': defaults.get('include_gas_allowance', False) if include_gas_allowance is None else bool(include_gas_allowance),
        'include_electrical_allowance': defaults.get('include_electrical_allowance', False) if include_electrical_allowance is None else bool(include_electrical_allowance),
        'include_automation_integration': defaults.get('include_automation_integration', False) if include_automation_integration is None else bool(include_automation_integration),
        'include_startup_visit': defaults.get('include_startup_visit', True) if include_startup_visit is None else bool(include_startup_visit),
    }

    lines: list[dict[str, Any]] = []
    equipment_line = {
        'name': candidate.model_name,
        'description': f"{candidate.brand_name} heater equipment package recommendation from heater quote run {run.id}.",
        'qty': unit_count,
        'amount': round(per_unit_price, 2),
        'code': currency_code,
        'category': 'equipment',
    }
    lines.append(equipment_line)

    def _append_template(slug: str, enabled: bool) -> None:
        if not enabled:
            return
        template = _line_template(profile, slug)
        if not template:
            return
        qty_mode = str(template.get('qty_mode') or 'per_system')
        qty = unit_count if qty_mode == 'per_unit' else 1
        lines.append({
            'name': template.get('name', slug.replace('_', ' ').title()),
            'description': template.get('description', ''),
            'qty': qty,
            'amount': round(float(template.get('amount') or 0), 2),
            'code': currency_code,
            'category': slug,
        })

    _append_template('bypass_kit', options['include_bypass_kit'])
    _append_template('pad_kit', options['include_pad_kit'])
    _append_template('gas_allowance', options['include_gas_allowance'])
    _append_template('electrical_allowance', options['include_electrical_allowance'])
    _append_template('automation_integration', options['include_automation_integration'])
    _append_template('startup_visit', options['include_startup_visit'])

    labor_rate = float(labor_rate_override) if labor_rate_override not in (None, 0, 0.0, '') else float(labor.get('labor_rate') or 0)
    labor_hours = float(labor.get('base_hours') or 0) + float(labor.get('hours_per_unit') or 0) * unit_count
    if labor_hours > 0 and labor_rate > 0:
        lines.append({
            'name': f"Labor - {labor.get('label', labor_profile)}",
            'description': 'Labor allowance generated from the selected heater install profile.',
            'qty': round(labor_hours, 2),
            'amount': round(labor_rate, 2),
            'code': currency_code,
            'category': 'labor',
        })

    if float(misc_materials_amount or 0) > 0:
        lines.append({
            'name': 'Miscellaneous materials allowance',
            'description': 'Additional field-adjustable allowance for fittings, wire, fasteners, or small install consumables.',
            'qty': 1,
            'amount': round(float(misc_materials_amount), 2),
            'code': currency_code,
            'category': 'misc_materials',
        })

    package_total = round(sum(float(item.get('qty') or 0) * float(item.get('amount') or 0) for item in lines), 2)
    return {
        'package_profile': profile_key,
        'package_profile_label': profile.get('label', profile_key),
        'labor_profile': labor_profile,
        'labor_profile_label': labor.get('label', labor_profile),
        'options': options,
        'unit_count': unit_count,
        'currency_code': currency_code,
        'package_total': package_total,
        'lines': lines,
        'candidate': {
            'id': candidate.id,
            'model_name': candidate.model_name,
            'brand_name': candidate.brand_name,
            'sku': candidate.sku,
            'recommendation_band': candidate.recommendation_band,
            'price': candidate.price,
            'per_unit_price': per_unit_price,
            'capacity_btu_per_hr': candidate.capacity_btu_per_hr,
        },
        'run_summary': run_summary,
    }



def _list_quote_case_heater_links(session: Session, quote_case_id: int) -> list[QuoteCaseExternalLink]:
    return list(
        session.exec(
            select(QuoteCaseExternalLink).where(
                QuoteCaseExternalLink.quote_case_id == quote_case_id,
                QuoteCaseExternalLink.system_slug == 'heater_quote',
            ).order_by(QuoteCaseExternalLink.created_at)
        ).all()
    )


def _line_total(line: dict[str, Any]) -> float:
    try:
        return round(float(line.get('qty') or 0) * float(line.get('amount') or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def _serialize_heater_package_link(link: QuoteCaseExternalLink) -> dict[str, Any]:
    payload = _safe_load(link.payload_json)
    lines = payload.get('prepared_lines') or []
    if not isinstance(lines, list) or not lines:
        single = payload.get('prepared_line')
        lines = [single] if isinstance(single, dict) else []
    normalized_lines = [item for item in lines if isinstance(item, dict)]
    equipment_total = round(sum(_line_total(item) for item in normalized_lines if str(item.get('category') or '') == 'equipment'), 2)
    labor_total = round(sum(_line_total(item) for item in normalized_lines if str(item.get('category') or '') == 'labor'), 2)
    materials_total = round(sum(_line_total(item) for item in normalized_lines if str(item.get('category') or '') not in {'equipment', 'labor'}), 2)
    grand_total = round(equipment_total + labor_total + materials_total, 2)
    package_summary = payload.get('package_summary') if isinstance(payload.get('package_summary'), dict) else {}
    currency_code = str(package_summary.get('currency_code') or payload.get('candidate', {}).get('currency_code') or 'USD')
    return {
        'external_link_id': link.id,
        'external_id': link.external_id,
        'external_label': link.external_label,
        'attached_at': link.created_at.isoformat() if link.created_at else '',
        'updated_at': link.updated_at.isoformat() if link.updated_at else '',
        'candidate': payload.get('candidate') if isinstance(payload.get('candidate'), dict) else {},
        'package_summary': {
            **package_summary,
            'equipment_total': equipment_total,
            'labor_total': labor_total,
            'materials_total': materials_total,
            'grand_total': grand_total,
            'currency_code': currency_code,
            'line_count': len(normalized_lines),
        },
        'prepared_lines': normalized_lines,
        'attached_by': payload.get('attached_by', ''),
    }


def get_quote_case_heater_package_workspace(session: Session, quote_case_id: int) -> dict[str, Any]:
    packages = [_serialize_heater_package_link(link) for link in _list_quote_case_heater_links(session, quote_case_id)]
    currency_code = next((pkg.get('package_summary', {}).get('currency_code') for pkg in packages if pkg.get('package_summary', {}).get('currency_code')), 'USD')
    equipment_total = round(sum(float(pkg.get('package_summary', {}).get('equipment_total') or 0) for pkg in packages), 2)
    labor_total = round(sum(float(pkg.get('package_summary', {}).get('labor_total') or 0) for pkg in packages), 2)
    materials_total = round(sum(float(pkg.get('package_summary', {}).get('materials_total') or 0) for pkg in packages), 2)
    grand_total = round(sum(float(pkg.get('package_summary', {}).get('grand_total') or 0) for pkg in packages), 2)
    return {
        'quote_case_id': quote_case_id,
        'package_count': len(packages),
        'currency_code': currency_code,
        'equipment_total': equipment_total,
        'labor_total': labor_total,
        'materials_total': materials_total,
        'grand_total': grand_total,
        'packages': packages,
    }


def list_quote_case_heater_package_lines(session: Session, quote_case_id: int) -> list[dict[str, Any]]:
    prepared_lines: list[dict[str, Any]] = []
    for package in get_quote_case_heater_package_workspace(session, quote_case_id).get('packages', []):
        lines = package.get('prepared_lines') or []
        prepared_lines.extend([item for item in lines if isinstance(item, dict)])
    return prepared_lines


def remove_heater_package_from_quote_case(session: Session, *, quote_case_id: int, external_link_id: int) -> dict[str, Any]:
    case = get_quote_case(session, quote_case_id)
    if case is None:
        raise ValueError('Quote case not found')
    link = session.get(QuoteCaseExternalLink, external_link_id)
    if link is None or link.quote_case_id != quote_case_id or link.system_slug != 'heater_quote':
        raise ValueError('Attached heater package not found')
    removed_external_id = link.external_id
    session.delete(link)
    session.commit()
    return {
        'removed_external_link_id': external_link_id,
        'removed_external_id': removed_external_id,
        'quote_case_id': quote_case_id,
        'workspace': get_quote_case_heater_package_workspace(session, quote_case_id),
    }


def attach_heater_candidate_to_quote_case(
    session: Session,
    *,
    run_id: int,
    candidate_id: int,
    quote_case_id: int,
    attached_by: str = 'operator',
    package_profile: str = 'auto',
    labor_profile: str = 'standard',
    include_bypass_kit: bool | None = None,
    include_pad_kit: bool | None = None,
    include_gas_allowance: bool | None = None,
    include_electrical_allowance: bool | None = None,
    include_automation_integration: bool | None = None,
    include_startup_visit: bool | None = None,
    misc_materials_amount: float = 0.0,
    labor_rate_override: float | None = None,
    replace_existing: bool = False,
) -> dict[str, Any]:
    run = get_heater_quote_run(session, run_id)
    if run is None:
        raise ValueError('Heater quote run not found')
    candidate = session.get(HeaterQuoteCandidate, candidate_id)
    if candidate is None or candidate.run_id != run_id:
        raise ValueError('Heater quote candidate not found')
    case = get_quote_case(session, quote_case_id)
    if case is None:
        raise ValueError('Quote case not found')

    removed_existing_count = 0
    if replace_existing:
        existing_links = _list_quote_case_heater_links(session, quote_case_id)
        removed_existing_count = len(existing_links)
        for existing_link in existing_links:
            session.delete(existing_link)
        if existing_links:
            session.commit()

    package_preview = build_heater_package_preview(
        session,
        run_id=run_id,
        candidate_id=candidate_id,
        package_profile=package_profile,
        labor_profile=labor_profile,
        include_bypass_kit=include_bypass_kit,
        include_pad_kit=include_pad_kit,
        include_gas_allowance=include_gas_allowance,
        include_electrical_allowance=include_electrical_allowance,
        include_automation_integration=include_automation_integration,
        include_startup_visit=include_startup_visit,
        misc_materials_amount=misc_materials_amount,
        labor_rate_override=labor_rate_override,
    )
    candidate_payload = _safe_load(candidate.payload_json)
    link = add_external_link(
        session,
        quote_case_id=quote_case_id,
        system_slug='heater_quote',
        external_type='candidate',
        external_id=f'{run_id}:{candidate_id}',
        external_label=candidate.model_name,
        sync_direction='local_only',
        sync_status='attached',
        payload={
            'attached_by': attached_by,
            'run_summary': package_preview['run_summary'],
            'candidate': {
                'vendor_name': candidate.vendor_name,
                'brand_name': candidate.brand_name,
                'model_name': candidate.model_name,
                'sku': candidate.sku,
                'heater_kind': candidate.heater_kind,
                'fuel_type': candidate.fuel_type,
                'unit_count': package_preview['unit_count'],
                'per_unit_capacity_btu_per_hr': candidate_payload.get('per_unit_capacity_btu_per_hr') or candidate.capacity_btu_per_hr,
                'capacity_btu_per_hr': candidate.capacity_btu_per_hr,
                'estimated_heatup_hours': candidate.estimated_heatup_hours,
                'per_unit_price': package_preview['candidate']['per_unit_price'],
                'price': candidate.price,
                'currency_code': candidate.currency_code,
                'availability_status': candidate.availability_status,
                'branch_name': candidate.branch_name,
                'fit_score': candidate.fit_score,
                'recommendation_band': candidate.recommendation_band,
            },
            'package_summary': {
                'package_profile': package_preview['package_profile'],
                'labor_profile': package_preview['labor_profile'],
                'package_total': package_preview['package_total'],
                'currency_code': package_preview['currency_code'],
                'options': package_preview['options'],
            },
            'prepared_line': package_preview['lines'][0] if package_preview['lines'] else {},
            'prepared_lines': package_preview['lines'],
            'source_payload': candidate_payload,
        },
    )
    return {
        'run': serialize_heater_quote_run(session, run_id),
        'quote_case': serialize_quote_case(session, case),
        'external_link': link.model_dump(),
        'prepared_line': package_preview['lines'][0] if package_preview['lines'] else {},
        'prepared_lines': package_preview['lines'],
        'package_summary': {
            'package_profile': package_preview['package_profile'],
            'labor_profile': package_preview['labor_profile'],
            'package_total': package_preview['package_total'],
            'currency_code': package_preview['currency_code'],
            'options': package_preview['options'],
        },
        'removed_existing_count': removed_existing_count,
        'package_workspace': get_quote_case_heater_package_workspace(session, quote_case_id),
    }



def delete_heater_quote_run(session: Session, run_id: int) -> dict[str, Any]:
    run = get_heater_quote_run(session, run_id)
    if run is None:
        raise ValueError('Heater quote run not found')
    candidates = list_heater_quote_candidates(session, run_id)
    links = list(
        session.exec(
            select(QuoteCaseExternalLink).where(
                QuoteCaseExternalLink.system_slug == 'heater_quote',
                QuoteCaseExternalLink.external_id.like(f'{run_id}:%'),
            )
        ).all()
    )
    candidate_count = len(candidates)
    link_count = len(links)
    for candidate in candidates:
        session.delete(candidate)
    for link in links:
        session.delete(link)
    session.delete(run)
    session.commit()
    return {
        'deleted_run_id': run_id,
        'deleted_candidate_count': candidate_count,
        'deleted_external_link_count': link_count,
    }



def get_heater_quote_dashboard_summary(session: Session) -> dict[str, Any]:
    config = get_heater_quote_settings(session)
    connection = get_heritage_connection_status(str(config.get('heritage', {}).get('sync_mode', 'dry_run') or 'dry_run'))
    runs = list(session.exec(select(HeaterQuoteRun).order_by(HeaterQuoteRun.created_at.desc())).all())
    candidates = list(session.exec(select(HeaterQuoteCandidate)).all())
    attached_candidate_count = len(
        list(
            session.exec(
                select(QuoteCaseExternalLink).where(QuoteCaseExternalLink.system_slug == 'heater_quote')
            ).all()
        )
    )
    return {
        'generated_at': datetime.utcnow().isoformat(),
        'total_runs': len(runs),
        'candidate_count': len(candidates),
        'heritage_connection': connection,
        'source_modes': {
            'heritage_live': sum(1 for run in runs if run.source_mode == 'heritage_live'),
            'fallback_catalog': sum(1 for run in runs if run.source_mode == 'fallback_catalog'),
            'no_catalog': sum(1 for run in runs if run.source_mode == 'no_catalog'),
        },
        'recent_runs': [serialize_heater_quote_run(session, run.id, include_candidates=False) for run in runs[:10]],
        'attached_candidate_count': attached_candidate_count,
        'settings': config,
    }
