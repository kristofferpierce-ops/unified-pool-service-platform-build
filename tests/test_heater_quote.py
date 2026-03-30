from __future__ import annotations

import app.models.heater_quote_tables as _heater_quote_tables  # noqa: F401
import app.models.quote_tables as _quote_tables  # noqa: F401
from sqlmodel import Session, select

from app.core.database import create_db_and_tables, engine
from app.models.quote_tables import QuoteCaseExternalLink
from app.services.heater_quote import (
    attach_heater_candidate_to_quote_case,
    build_heater_package_preview,
    calculate_heater_requirements,
    create_heater_quote_run,
    delete_heater_quote_run,
    ensure_heater_quote_settings,
    get_quote_case_heater_package_workspace,
    list_quote_case_heater_package_lines,
    rank_heater_candidates,
    remove_heater_package_from_quote_case,
    reset_heater_package_lines,
    update_heater_package_lines,
)
from app.services.quote_workflow import create_quote_case

create_db_and_tables()


def test_heater_quote_sizing_from_dimensions_and_heatup_window():
    config = {
        'defaults': {'desired_heatup_hours': 24.0},
        'sizing': {
            'gallons_to_pounds': 8.34,
            'heat_pump_surface_factor': 12.0,
            'wind_rules': [
                {'minimum_mph': 10.0, 'multiplier': 2.0},
                {'minimum_mph': 5.0, 'multiplier': 1.25},
                {'minimum_mph': 0.0, 'multiplier': 1.0},
            ],
            'low_ambient_threshold_f': 55.0,
        },
    }
    summary = calculate_heater_requirements(
        direct_gallons=None,
        shape='rectangle',
        length_ft=30.0,
        width_ft=15.0,
        avg_depth_ft=5.0,
        diameter_ft=0.0,
        current_water_temp_f=70.0,
        target_water_temp_f=84.0,
        ambient_air_temp_f=78.0,
        desired_heatup_hours=24.0,
        wind_mph=5.0,
        covered=False,
        config=config,
    )
    assert summary['volume_gallons'] > 16000
    assert summary['temperature_rise_f'] == 14.0
    assert summary['heatup_btu_per_hr'] > 0
    assert summary['recommended_btu_per_hr'] >= summary['heatup_btu_per_hr']


def test_heater_quote_ranking_prefers_close_capacity_candidates():
    config = {
        'sizing': {
            'ideal_min_ratio': 0.85,
            'ideal_max_ratio': 1.25,
            'viable_min_ratio': 0.70,
            'viable_max_ratio': 1.75,
            'low_ambient_heat_pump_penalty': 20.0,
            'low_ambient_threshold_f': 55.0,
        },
        'heritage': {'vendor_name': 'Heritage Pool Supply'},
    }
    summary = {
        'recommended_btu_per_hr': 200000.0,
        'total_btu_required': 3000000.0,
        'ambient_air_temp_f': 80.0,
        'preferred_heater_kind': 'gas',
    }
    catalog = [
        {'model_name': 'Small Heater', 'sku': 'A', 'heater_kind': 'gas', 'fuel_type': 'natural_gas', 'capacity_btu_per_hr': 120000.0, 'price': 1000.0},
        {'model_name': 'Ideal Heater', 'sku': 'B', 'heater_kind': 'gas', 'fuel_type': 'natural_gas', 'capacity_btu_per_hr': 225000.0, 'price': 1600.0},
        {'model_name': 'Huge Heater', 'sku': 'C', 'heater_kind': 'gas', 'fuel_type': 'natural_gas', 'capacity_btu_per_hr': 500000.0, 'price': 2500.0},
    ]
    candidates = rank_heater_candidates(
        summary=summary,
        catalog=catalog,
        heater_kind_preference='gas',
        fuel_preference='auto',
        unit_count=1,
        config=config,
    )
    assert candidates[0]['model_name'] == 'Ideal Heater'
    assert candidates[0]['recommendation_band'] == 'ideal'


def test_heater_package_preview_builds_equipment_material_and_labor_lines():
    with Session(engine) as session:
        case = create_quote_case(
            session,
            pipeline_slug='new_residential_services',
            title='Heater package preview case',
            requester_name='Preview Owner',
            requester_email='preview@example.com',
        )
        run_payload = create_heater_quote_run(
            session,
            title='Preview package run',
            quote_case_id=case.id,
            direct_gallons=18000.0,
            current_water_temp_f=72.0,
            target_water_temp_f=84.0,
            ambient_air_temp_f=78.0,
            desired_heatup_hours=24.0,
            wind_mph=0.0,
            covered=False,
            heater_kind_preference='gas',
            fuel_preference='auto',
            unit_count=2,
        )
        candidate_id = run_payload['candidates'][0]['id']
        preview = build_heater_package_preview(
            session,
            run_id=run_payload['id'],
            candidate_id=candidate_id,
            package_profile='gas_standard',
            labor_profile='standard',
            include_automation_integration=True,
            misc_materials_amount=125.0,
        )
        assert preview['unit_count'] == 2
        assert preview['package_total'] > 0
        categories = {line['category'] for line in preview['lines']}
        assert 'equipment' in categories
        assert 'labor' in categories
        assert 'misc_materials' in categories



def test_attach_heater_candidate_to_quote_case_creates_external_link():
    with Session(engine) as session:
        case = create_quote_case(
            session,
            pipeline_slug='new_residential_services',
            title='Heater attachment test case',
            requester_name='Case Owner',
            requester_email='owner@example.com',
        )
        settings = {
            'version': 'test',
            'defaults': {'desired_heatup_hours': 24.0, 'unit_count': 2},
            'sizing': {
                'gallons_to_pounds': 8.34,
                'heat_pump_surface_factor': 12.0,
                'wind_rules': [{'minimum_mph': 0.0, 'multiplier': 1.0}],
                'ideal_min_ratio': 0.85,
                'ideal_max_ratio': 1.25,
                'viable_min_ratio': 0.70,
                'viable_max_ratio': 1.75,
                'low_ambient_heat_pump_penalty': 20.0,
                'low_ambient_threshold_f': 55.0,
            },
            'heritage': {
                'sync_mode': 'dry_run',
                'vendor_name': 'Heritage Pool Supply',
                'fallback_catalog': [
                    {
                        'model_name': 'Test Heater',
                        'sku': f'HEAT-{case.id}',
                        'heater_kind': 'gas',
                        'fuel_type': 'natural_gas',
                        'capacity_btu_per_hr': 250000.0,
                        'price': 1800.0,
                        'currency_code': 'USD',
                    }
                ],
            },
        }
        from app.services.system_settings import set_setting
        set_setting(session, 'heater_quote_config', settings, 'test heater quote config')
        run_payload = create_heater_quote_run(
            session,
            title='Attachment test run',
            quote_case_id=case.id,
            direct_gallons=15000.0,
            shape='direct',
            current_water_temp_f=72.0,
            target_water_temp_f=84.0,
            ambient_air_temp_f=78.0,
            desired_heatup_hours=24.0,
            wind_mph=0.0,
            covered=False,
            heater_kind_preference='gas',
            fuel_preference='auto',
            unit_count=2,
        )
        candidate_id = run_payload['candidates'][0]['id']
        attach_result = attach_heater_candidate_to_quote_case(
            session,
            run_id=run_payload['id'],
            candidate_id=candidate_id,
            quote_case_id=case.id,
            package_profile='gas_standard',
            labor_profile='standard',
            include_automation_integration=True,
        )
        assert attach_result['external_link']['system_slug'] == 'heater_quote'
        assert attach_result['prepared_line']['qty'] == 2
        assert attach_result['prepared_line']['amount'] == 1800.0
        assert len(attach_result['prepared_lines']) >= 3
        assert attach_result['package_summary']['package_total'] > 0
        attached_links = list(
            session.exec(
                select(QuoteCaseExternalLink).where(
                    QuoteCaseExternalLink.quote_case_id == case.id,
                    QuoteCaseExternalLink.system_slug == 'heater_quote',
                )
            ).all()
        )
        assert attached_links



def test_default_settings_seed_starter_fallback_catalog():
    with Session(engine) as session:
        from app.services.system_settings import set_setting
        set_setting(session, 'heater_quote_config', {'version': 'legacy', 'defaults': {}, 'heritage': {'fallback_catalog': []}}, 'legacy empty config')
        config = ensure_heater_quote_settings(session)
        assert config['heritage']['fallback_catalog']
        assert config['defaults']['unit_count'] == 1



def test_delete_heater_quote_run_removes_run_candidates_and_links():
    with Session(engine) as session:
        case = create_quote_case(
            session,
            pipeline_slug='new_residential_services',
            title='Heater delete test case',
            requester_name='Delete Owner',
            requester_email='delete@example.com',
        )
        run_payload = create_heater_quote_run(
            session,
            title='Delete test run',
            quote_case_id=case.id,
            direct_gallons=18000.0,
            current_water_temp_f=75.0,
            target_water_temp_f=85.0,
            ambient_air_temp_f=80.0,
            desired_heatup_hours=24.0,
            heater_kind_preference='gas',
            fuel_preference='auto',
            unit_count=1,
        )
        attach_heater_candidate_to_quote_case(
            session,
            run_id=run_payload['id'],
            candidate_id=run_payload['candidates'][0]['id'],
            quote_case_id=case.id,
        )
        result = delete_heater_quote_run(session, run_payload['id'])
        assert result['deleted_run_id'] == run_payload['id']
        assert result['deleted_candidate_count'] >= 1
        remaining_links = list(session.exec(select(QuoteCaseExternalLink).where(QuoteCaseExternalLink.system_slug == 'heater_quote')).all())
        assert all(not link.external_id.startswith(f"{run_payload['id']}:") for link in remaining_links)


def test_quote_case_heater_package_workspace_summarizes_attached_packages():
    with Session(engine) as session:
        case = create_quote_case(
            session,
            pipeline_slug='new_residential_services',
            title='Heater workspace summary case',
            requester_name='Workspace Owner',
            requester_email='workspace@example.com',
        )
        run_payload = create_heater_quote_run(
            session,
            title='Workspace summary run',
            quote_case_id=case.id,
            direct_gallons=16000.0,
            current_water_temp_f=72.0,
            target_water_temp_f=84.0,
            ambient_air_temp_f=78.0,
            desired_heatup_hours=24.0,
            heater_kind_preference='gas',
            fuel_preference='auto',
            unit_count=1,
        )
        attach_heater_candidate_to_quote_case(
            session,
            run_id=run_payload['id'],
            candidate_id=run_payload['candidates'][0]['id'],
            quote_case_id=case.id,
            package_profile='gas_standard',
            labor_profile='standard',
        )
        workspace = get_quote_case_heater_package_workspace(session, case.id)
        assert workspace['package_count'] == 1
        assert workspace['grand_total'] > 0
        assert workspace['packages'][0]['package_summary']['line_count'] >= 1
        assert workspace['packages'][0]['prepared_lines']


def test_replace_existing_heater_package_keeps_only_new_attachment():
    with Session(engine) as session:
        from app.services.system_settings import set_setting

        case = create_quote_case(
            session,
            pipeline_slug='new_residential_services',
            title='Heater replace package case',
            requester_name='Replace Owner',
            requester_email='replace@example.com',
        )
        settings = {
            'version': 'test',
            'defaults': {'desired_heatup_hours': 24.0, 'unit_count': 1},
            'sizing': {
                'gallons_to_pounds': 8.34,
                'heat_pump_surface_factor': 12.0,
                'wind_rules': [{'minimum_mph': 0.0, 'multiplier': 1.0}],
                'ideal_min_ratio': 0.85,
                'ideal_max_ratio': 1.25,
                'viable_min_ratio': 0.70,
                'viable_max_ratio': 1.75,
                'low_ambient_heat_pump_penalty': 20.0,
                'low_ambient_threshold_f': 55.0,
            },
            'heritage': {
                'sync_mode': 'dry_run',
                'vendor_name': 'Heritage Pool Supply',
                'fallback_catalog': [
                    {
                        'model_name': 'Test Heater A',
                        'sku': f'HEAT-A-{case.id}',
                        'heater_kind': 'gas',
                        'fuel_type': 'natural_gas',
                        'capacity_btu_per_hr': 250000.0,
                        'price': 1800.0,
                        'currency_code': 'USD',
                    },
                    {
                        'model_name': 'Test Heater B',
                        'sku': f'HEAT-B-{case.id}',
                        'heater_kind': 'gas',
                        'fuel_type': 'natural_gas',
                        'capacity_btu_per_hr': 399000.0,
                        'price': 2600.0,
                        'currency_code': 'USD',
                    },
                ],
            },
        }
        set_setting(session, 'heater_quote_config', settings, 'test heater quote config replace')
        run_payload = create_heater_quote_run(
            session,
            title='Replace run',
            quote_case_id=case.id,
            direct_gallons=14000.0,
            current_water_temp_f=72.0,
            target_water_temp_f=84.0,
            ambient_air_temp_f=78.0,
            desired_heatup_hours=24.0,
            heater_kind_preference='gas',
            fuel_preference='auto',
            unit_count=1,
        )
        first_candidate = run_payload['candidates'][0]['id']
        second_candidate = run_payload['candidates'][1]['id']
        attach_heater_candidate_to_quote_case(
            session,
            run_id=run_payload['id'],
            candidate_id=first_candidate,
            quote_case_id=case.id,
        )
        replace_result = attach_heater_candidate_to_quote_case(
            session,
            run_id=run_payload['id'],
            candidate_id=second_candidate,
            quote_case_id=case.id,
            replace_existing=True,
        )
        assert replace_result['removed_existing_count'] == 1
        workspace = get_quote_case_heater_package_workspace(session, case.id)
        assert workspace['package_count'] == 1
        assert workspace['packages'][0]['candidate']['model_name'] == 'Test Heater B'


def test_remove_heater_package_from_quote_case_clears_workspace():
    with Session(engine) as session:
        case = create_quote_case(
            session,
            pipeline_slug='new_residential_services',
            title='Heater remove package case',
            requester_name='Remove Owner',
            requester_email='remove@example.com',
        )
        run_payload = create_heater_quote_run(
            session,
            title='Remove package run',
            quote_case_id=case.id,
            direct_gallons=15000.0,
            current_water_temp_f=74.0,
            target_water_temp_f=84.0,
            ambient_air_temp_f=80.0,
            desired_heatup_hours=24.0,
            heater_kind_preference='gas',
            fuel_preference='auto',
            unit_count=1,
        )
        attach_heater_candidate_to_quote_case(
            session,
            run_id=run_payload['id'],
            candidate_id=run_payload['candidates'][0]['id'],
            quote_case_id=case.id,
        )
        workspace = get_quote_case_heater_package_workspace(session, case.id)
        link_id = workspace['packages'][0]['external_link_id']
        remove_result = remove_heater_package_from_quote_case(session, quote_case_id=case.id, external_link_id=link_id)
        assert remove_result['removed_external_link_id'] == link_id
        assert remove_result['workspace']['package_count'] == 0



def test_update_heater_package_lines_persists_quote_case_overrides():
    with Session(engine) as session:
        case = create_quote_case(
            session,
            pipeline_slug='new_residential_services',
            title='Heater package override case',
            requester_name='Override Owner',
            requester_email='override@example.com',
        )
        run_payload = create_heater_quote_run(
            session,
            title='Override run',
            quote_case_id=case.id,
            direct_gallons=15000.0,
            current_water_temp_f=73.0,
            target_water_temp_f=84.0,
            ambient_air_temp_f=79.0,
            desired_heatup_hours=24.0,
            heater_kind_preference='gas',
            fuel_preference='auto',
            unit_count=1,
        )
        attach_heater_candidate_to_quote_case(
            session,
            run_id=run_payload['id'],
            candidate_id=run_payload['candidates'][0]['id'],
            quote_case_id=case.id,
            package_profile='gas_standard',
            labor_profile='standard',
        )
        workspace = get_quote_case_heater_package_workspace(session, case.id)
        link_id = workspace['packages'][0]['external_link_id']
        update_result = update_heater_package_lines(
            session,
            quote_case_id=case.id,
            external_link_id=link_id,
            edited_lines=[
                {'name': 'Edited heater equipment', 'description': 'Custom equipment package', 'qty': 1, 'amount': 2400.0, 'category': 'equipment'},
                {'name': 'Edited labor', 'description': 'Custom labor package', 'qty': 1, 'amount': 950.0, 'category': 'labor'},
            ],
            edited_by='tester',
        )
        workspace = update_result['package_workspace']
        assert workspace['package_count'] == 1
        assert workspace['packages'][0]['has_overrides'] is True
        line_names = {line['name'] for line in workspace['packages'][0]['prepared_lines']}
        assert 'Edited heater equipment' in line_names
        assert 'Edited labor' in line_names
        attached_lines = list_quote_case_heater_package_lines(session, case.id)
        assert any(line['name'] == 'Edited heater equipment' for line in attached_lines)



def test_reset_heater_package_lines_restores_original_attachment_lines():
    with Session(engine) as session:
        case = create_quote_case(
            session,
            pipeline_slug='new_residential_services',
            title='Heater package reset case',
            requester_name='Reset Owner',
            requester_email='reset@example.com',
        )
        run_payload = create_heater_quote_run(
            session,
            title='Reset run',
            quote_case_id=case.id,
            direct_gallons=15500.0,
            current_water_temp_f=72.0,
            target_water_temp_f=84.0,
            ambient_air_temp_f=79.0,
            desired_heatup_hours=24.0,
            heater_kind_preference='gas',
            fuel_preference='auto',
            unit_count=1,
        )
        attach_heater_candidate_to_quote_case(
            session,
            run_id=run_payload['id'],
            candidate_id=run_payload['candidates'][0]['id'],
            quote_case_id=case.id,
            package_profile='gas_standard',
            labor_profile='standard',
        )
        original_workspace = get_quote_case_heater_package_workspace(session, case.id)
        link_id = original_workspace['packages'][0]['external_link_id']
        original_names = [line['name'] for line in original_workspace['packages'][0]['prepared_lines']]
        update_heater_package_lines(
            session,
            quote_case_id=case.id,
            external_link_id=link_id,
            edited_lines=[
                {'name': 'Edited one-off line', 'description': 'Temporary edit', 'qty': 1, 'amount': 500.0, 'category': 'misc_materials'},
            ],
            edited_by='tester',
        )
        reset_result = reset_heater_package_lines(session, quote_case_id=case.id, external_link_id=link_id)
        workspace = reset_result['package_workspace']
        assert workspace['packages'][0]['has_overrides'] is False
        restored_names = [line['name'] for line in workspace['packages'][0]['prepared_lines']]
        assert restored_names == original_names
