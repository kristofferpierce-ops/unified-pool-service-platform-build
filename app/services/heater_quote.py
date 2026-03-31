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
    'selector_scoring': {
        'compatibility_base': 100.0,
        'issue_penalty': 30.0,
        'warning_penalty': 6.0,
        'price_weight': 18.0,
        'branch_bonus': 8.0,
        'branch_miss_penalty': 4.0,
    },

}


DEFAULT_EQUIPMENT_PACKAGE_TEMPLATE_CONFIG: dict[str, Any] = {
    'version': 'platform_block_2e_equipment_package_families',
    'templates': [],
}

DEFAULT_EQUIPMENT_FAMILY_BUILDER_CONFIG: dict[str, Any] = {
    'version': 'platform_block_2f_family_package_builders',
    'labor_profiles': {
        'standard': {'label': 'Standard install', 'labor_rate': 125.0, 'base_hours': 1.5, 'hours_per_unit': 3.0},
        'simple_swap': {'label': 'Simple swap', 'labor_rate': 125.0, 'base_hours': 1.0, 'hours_per_unit': 2.0},
        'complex': {'label': 'Complex install', 'labor_rate': 135.0, 'base_hours': 2.5, 'hours_per_unit': 4.0},
    },
    'families': {
        'pump': {
            'label': 'Pump package builder',
            'default_profile': 'variable_speed_upgrade',
            'default_labor_profile': 'standard',
            'profiles': {
                'variable_speed_upgrade': {
                    'label': 'Variable speed upgrade',
                    'default_equipment_name': 'Variable speed pump',
                    'equipment_description': 'Pump equipment allowance from the selected equipment family builder.',
                    'default_options': {
                        'include_plumbing_kit': True,
                        'include_pad_kit': True,
                        'include_electrical_allowance': True,
                        'include_startup_visit': True,
                        'include_controller_integration': False,
                    },
                    'option_labels': {
                        'include_plumbing_kit': 'Include plumbing kit',
                        'include_pad_kit': 'Include pad / stand allowance',
                        'include_electrical_allowance': 'Include electrical allowance',
                        'include_startup_visit': 'Include startup visit',
                        'include_controller_integration': 'Include controller integration',
                    },
                    'line_items': {
                        'plumbing_kit': {'name': 'Pump union and plumbing kit', 'description': 'Unions, fittings, and tie-in materials for pump replacement.', 'amount': 165.0, 'qty_mode': 'per_system', 'category': 'misc_materials'},
                        'pad_kit': {'name': 'Pump pad / base allowance', 'description': 'Pad materials or shimming allowance for a clean pump install.', 'amount': 140.0, 'qty_mode': 'per_system', 'category': 'misc_materials'},
                        'electrical_allowance': {'name': 'Pump electrical allowance', 'description': 'Basic whip, disconnect, breaker, or reconnect allowance.', 'amount': 325.0, 'qty_mode': 'per_system', 'category': 'misc_materials'},
                        'startup_visit': {'name': 'Pump startup visit', 'description': 'Programming, priming, and start-up verification.', 'amount': 165.0, 'qty_mode': 'per_system', 'category': 'misc_materials'},
                        'controller_integration': {'name': 'Automation integration allowance', 'description': 'Variable speed schedule setup with existing controls.', 'amount': 285.0, 'qty_mode': 'per_system', 'category': 'misc_materials'},
                    },
                },
                'single_speed_swap': {
                    'label': 'Single speed swap',
                    'default_equipment_name': 'Replacement pump',
                    'equipment_description': 'Pump equipment allowance from the selected equipment family builder.',
                    'default_options': {
                        'include_plumbing_kit': True,
                        'include_pad_kit': False,
                        'include_electrical_allowance': False,
                        'include_startup_visit': True,
                        'include_controller_integration': False,
                    },
                    'option_labels': {
                        'include_plumbing_kit': 'Include plumbing kit',
                        'include_pad_kit': 'Include pad / stand allowance',
                        'include_electrical_allowance': 'Include electrical allowance',
                        'include_startup_visit': 'Include startup visit',
                        'include_controller_integration': 'Include controller integration',
                    },
                    'line_items': {
                        'plumbing_kit': {'name': 'Pump union and plumbing kit', 'description': 'Unions, fittings, and tie-in materials for pump replacement.', 'amount': 145.0, 'qty_mode': 'per_system', 'category': 'misc_materials'},
                        'pad_kit': {'name': 'Pump pad / base allowance', 'description': 'Pad materials or shimming allowance for a clean pump install.', 'amount': 120.0, 'qty_mode': 'per_system', 'category': 'misc_materials'},
                        'electrical_allowance': {'name': 'Pump electrical allowance', 'description': 'Basic reconnect allowance when required.', 'amount': 180.0, 'qty_mode': 'per_system', 'category': 'misc_materials'},
                        'startup_visit': {'name': 'Pump startup visit', 'description': 'Prime, pressure, and flow verification.', 'amount': 145.0, 'qty_mode': 'per_system', 'category': 'misc_materials'},
                        'controller_integration': {'name': 'Automation integration allowance', 'description': 'Basic controller reconnect allowance.', 'amount': 185.0, 'qty_mode': 'per_system', 'category': 'misc_materials'},
                    },
                },
            },
        },
        'filter': {
            'label': 'Filter package builder',
            'default_profile': 'cartridge_replacement',
            'default_labor_profile': 'standard',
            'profiles': {
                'cartridge_replacement': {
                    'label': 'Cartridge filter replacement',
                    'default_equipment_name': 'Cartridge filter body',
                    'equipment_description': 'Filter equipment allowance from the selected equipment family builder.',
                    'default_options': {
                        'include_plumbing_kit': True,
                        'include_pad_kit': True,
                        'include_startup_visit': True,
                        'include_media_charge': False,
                    },
                    'option_labels': {
                        'include_plumbing_kit': 'Include plumbing kit',
                        'include_pad_kit': 'Include pad / stand allowance',
                        'include_startup_visit': 'Include startup visit',
                        'include_media_charge': 'Include media charge',
                    },
                    'line_items': {
                        'plumbing_kit': {'name': 'Filter plumbing and union kit', 'description': 'Plumbing materials for filter changeout and reconnection.', 'amount': 185.0, 'qty_mode': 'per_system', 'category': 'misc_materials'},
                        'pad_kit': {'name': 'Filter pad / base allowance', 'description': 'Pad materials or stand allowance for filter install.', 'amount': 155.0, 'qty_mode': 'per_system', 'category': 'misc_materials'},
                        'startup_visit': {'name': 'Filter startup visit', 'description': 'Pressure, flow, and air-relief verification.', 'amount': 150.0, 'qty_mode': 'per_system', 'category': 'misc_materials'},
                        'media_charge': {'name': 'Filter media allowance', 'description': 'Allowance for sand, glass, or DE media when applicable.', 'amount': 220.0, 'qty_mode': 'per_system', 'category': 'misc_materials'},
                    },
                },
                'sand_filter_replacement': {
                    'label': 'Sand filter replacement',
                    'default_equipment_name': 'Sand filter body',
                    'equipment_description': 'Filter equipment allowance from the selected equipment family builder.',
                    'default_options': {
                        'include_plumbing_kit': True,
                        'include_pad_kit': True,
                        'include_startup_visit': True,
                        'include_media_charge': True,
                    },
                    'option_labels': {
                        'include_plumbing_kit': 'Include plumbing kit',
                        'include_pad_kit': 'Include pad / stand allowance',
                        'include_startup_visit': 'Include startup visit',
                        'include_media_charge': 'Include media charge',
                    },
                    'line_items': {
                        'plumbing_kit': {'name': 'Filter plumbing and union kit', 'description': 'Plumbing materials for filter changeout and reconnection.', 'amount': 195.0, 'qty_mode': 'per_system', 'category': 'misc_materials'},
                        'pad_kit': {'name': 'Filter pad / base allowance', 'description': 'Pad materials or stand allowance for filter install.', 'amount': 165.0, 'qty_mode': 'per_system', 'category': 'misc_materials'},
                        'startup_visit': {'name': 'Filter startup visit', 'description': 'Pressure, flow, and air-relief verification.', 'amount': 165.0, 'qty_mode': 'per_system', 'category': 'misc_materials'},
                        'media_charge': {'name': 'Filter media allowance', 'description': 'Allowance for sand or glass media.', 'amount': 260.0, 'qty_mode': 'per_system', 'category': 'misc_materials'},
                    },
                },
            },
        },
        'salt_system': {
            'label': 'Salt system package builder',
            'default_profile': 'salt_conversion',
            'default_labor_profile': 'standard',
            'profiles': {
                'salt_conversion': {
                    'label': 'Salt conversion package',
                    'default_equipment_name': 'Salt cell and power center',
                    'equipment_description': 'Salt system equipment allowance from the selected equipment family builder.',
                    'default_options': {
                        'include_plumbing_kit': True,
                        'include_electrical_allowance': True,
                        'include_salt_charge': True,
                        'include_startup_visit': True,
                        'include_controller_integration': False,
                    },
                    'option_labels': {
                        'include_plumbing_kit': 'Include plumbing kit',
                        'include_electrical_allowance': 'Include electrical allowance',
                        'include_salt_charge': 'Include startup salt allowance',
                        'include_startup_visit': 'Include startup visit',
                        'include_controller_integration': 'Include controller integration',
                    },
                    'line_items': {
                        'plumbing_kit': {'name': 'Salt cell plumbing kit', 'description': 'Cell unions, bypass, and plumbing materials.', 'amount': 125.0, 'qty_mode': 'per_system', 'category': 'misc_materials'},
                        'electrical_allowance': {'name': 'Salt electrical allowance', 'description': 'Power center feed, disconnect, and tie-in allowance.', 'amount': 260.0, 'qty_mode': 'per_system', 'category': 'misc_materials'},
                        'salt_charge': {'name': 'Startup salt allowance', 'description': 'Startup salt and initial balance allowance.', 'amount': 185.0, 'qty_mode': 'per_system', 'category': 'misc_materials'},
                        'startup_visit': {'name': 'Salt startup visit', 'description': 'Startup, salinity verification, and customer handoff.', 'amount': 185.0, 'qty_mode': 'per_system', 'category': 'misc_materials'},
                        'controller_integration': {'name': 'Automation integration allowance', 'description': 'Enable and schedule salt system through existing controls.', 'amount': 225.0, 'qty_mode': 'per_system', 'category': 'misc_materials'},
                    },
                },
                'cell_replacement': {
                    'label': 'Salt cell replacement',
                    'default_equipment_name': 'Replacement salt cell',
                    'equipment_description': 'Salt system equipment allowance from the selected equipment family builder.',
                    'default_options': {
                        'include_plumbing_kit': False,
                        'include_electrical_allowance': False,
                        'include_salt_charge': False,
                        'include_startup_visit': True,
                        'include_controller_integration': False,
                    },
                    'option_labels': {
                        'include_plumbing_kit': 'Include plumbing kit',
                        'include_electrical_allowance': 'Include electrical allowance',
                        'include_salt_charge': 'Include startup salt allowance',
                        'include_startup_visit': 'Include startup visit',
                        'include_controller_integration': 'Include controller integration',
                    },
                    'line_items': {
                        'plumbing_kit': {'name': 'Salt cell union allowance', 'description': 'Union or adaptor allowance for cell swap.', 'amount': 80.0, 'qty_mode': 'per_system', 'category': 'misc_materials'},
                        'electrical_allowance': {'name': 'Salt electrical allowance', 'description': 'Power center reconnect allowance.', 'amount': 150.0, 'qty_mode': 'per_system', 'category': 'misc_materials'},
                        'salt_charge': {'name': 'Startup salt allowance', 'description': 'Top-off salt allowance when needed.', 'amount': 95.0, 'qty_mode': 'per_system', 'category': 'misc_materials'},
                        'startup_visit': {'name': 'Salt startup visit', 'description': 'Startup and output verification.', 'amount': 145.0, 'qty_mode': 'per_system', 'category': 'misc_materials'},
                        'controller_integration': {'name': 'Automation integration allowance', 'description': 'Reconnect salt cell controls to automation.', 'amount': 175.0, 'qty_mode': 'per_system', 'category': 'misc_materials'},
                    },
                },
            },
        },
        'automation': {
            'label': 'Automation package builder',
            'default_profile': 'panel_upgrade',
            'default_labor_profile': 'complex',
            'profiles': {
                'panel_upgrade': {
                    'label': 'Automation panel upgrade',
                    'default_equipment_name': 'Automation control panel',
                    'equipment_description': 'Automation package allowance from the selected equipment family builder.',
                    'default_options': {
                        'include_electrical_allowance': True,
                        'include_relay_pack': True,
                        'include_actuator_pack': True,
                        'include_controller_integration': True,
                        'include_startup_visit': True,
                    },
                    'option_labels': {
                        'include_electrical_allowance': 'Include electrical allowance',
                        'include_relay_pack': 'Include relay / expansion allowance',
                        'include_actuator_pack': 'Include actuator allowance',
                        'include_controller_integration': 'Include programming / integration allowance',
                        'include_startup_visit': 'Include startup visit',
                    },
                    'line_items': {
                        'electrical_allowance': {'name': 'Automation electrical allowance', 'description': 'Breaker, feeders, disconnect, and tie-in allowance.', 'amount': 340.0, 'qty_mode': 'per_system', 'category': 'misc_materials'},
                        'relay_pack': {'name': 'Relay / expansion allowance', 'description': 'Relay module or expansion board allowance.', 'amount': 420.0, 'qty_mode': 'per_system', 'category': 'misc_materials'},
                        'actuator_pack': {'name': 'Actuator allowance', 'description': 'Valve actuator allowance for automation package.', 'amount': 220.0, 'qty_mode': 'per_system', 'category': 'misc_materials'},
                        'controller_integration': {'name': 'Programming and integration allowance', 'description': 'Controller setup, schedule programming, and equipment integration.', 'amount': 375.0, 'qty_mode': 'per_system', 'category': 'misc_materials'},
                        'startup_visit': {'name': 'Automation startup visit', 'description': 'On-site programming verification and customer walkthrough.', 'amount': 225.0, 'qty_mode': 'per_system', 'category': 'misc_materials'},
                    },
                },
                'automation_addon': {
                    'label': 'Automation add-on package',
                    'default_equipment_name': 'Automation add-on kit',
                    'equipment_description': 'Automation package allowance from the selected equipment family builder.',
                    'default_options': {
                        'include_electrical_allowance': False,
                        'include_relay_pack': True,
                        'include_actuator_pack': True,
                        'include_controller_integration': True,
                        'include_startup_visit': True,
                    },
                    'option_labels': {
                        'include_electrical_allowance': 'Include electrical allowance',
                        'include_relay_pack': 'Include relay / expansion allowance',
                        'include_actuator_pack': 'Include actuator allowance',
                        'include_controller_integration': 'Include programming / integration allowance',
                        'include_startup_visit': 'Include startup visit',
                    },
                    'line_items': {
                        'electrical_allowance': {'name': 'Automation electrical allowance', 'description': 'Basic tie-in allowance when required.', 'amount': 220.0, 'qty_mode': 'per_system', 'category': 'misc_materials'},
                        'relay_pack': {'name': 'Relay / expansion allowance', 'description': 'Relay module or expansion board allowance.', 'amount': 260.0, 'qty_mode': 'per_system', 'category': 'misc_materials'},
                        'actuator_pack': {'name': 'Actuator allowance', 'description': 'Valve actuator allowance for automation package.', 'amount': 220.0, 'qty_mode': 'per_system', 'category': 'misc_materials'},
                        'controller_integration': {'name': 'Programming and integration allowance', 'description': 'Controller setup and equipment integration.', 'amount': 265.0, 'qty_mode': 'per_system', 'category': 'misc_materials'},
                        'startup_visit': {'name': 'Automation startup visit', 'description': 'On-site verification and walkthrough.', 'amount': 185.0, 'qty_mode': 'per_system', 'category': 'misc_materials'},
                    },
                },
            },
        },
    },
}

DEFAULT_EQUIPMENT_FAMILY_WIZARD_CONFIG: dict[str, Any] = {
    'version': 'platform_block_2g_builder_input_wizards',
    'families': {
        'pump': {
            'label': 'Pump input wizard',
            'default_template_name': 'Pump package template',
            'fields': [
                {'name': 'pump_style', 'label': 'Pump style', 'type': 'enum', 'options': ['variable_speed', 'single_speed'], 'default': 'variable_speed'},
                {'name': 'horsepower', 'label': 'Horsepower', 'type': 'float', 'default': 3.0, 'step': 0.5, 'minimum': 0.5},
                {'name': 'voltage', 'label': 'Voltage', 'type': 'enum', 'options': ['230V', '208-230V', '115V'], 'default': '230V'},
                {'name': 'plumbing_size_in', 'label': 'Plumbing size (in)', 'type': 'float', 'default': 2.0, 'step': 0.5, 'minimum': 1.0},
                {'name': 'union_size_in', 'label': 'Union size (in)', 'type': 'float', 'default': 2.0, 'step': 0.5, 'minimum': 1.0},
                {'name': 'automation_integration', 'label': 'Automation integration', 'type': 'bool', 'default': True},
            ],
        },
        'filter': {
            'label': 'Filter input wizard',
            'default_template_name': 'Filter package template',
            'fields': [
                {'name': 'filter_style', 'label': 'Filter style', 'type': 'enum', 'options': ['cartridge', 'sand'], 'default': 'cartridge'},
                {'name': 'filter_area_sqft', 'label': 'Filter area (sqft)', 'type': 'float', 'default': 420.0, 'step': 20.0, 'minimum': 100.0},
                {'name': 'tank_diameter_in', 'label': 'Tank diameter (in)', 'type': 'float', 'default': 30.0, 'step': 1.0, 'minimum': 18.0},
                {'name': 'target_flow_gpm', 'label': 'Target flow (GPM)', 'type': 'float', 'default': 75.0, 'step': 5.0, 'minimum': 10.0},
                {'name': 'include_media_charge', 'label': 'Include media charge', 'type': 'bool', 'default': True},
            ],
        },
        'salt_system': {
            'label': 'Salt system input wizard',
            'default_template_name': 'Salt system package template',
            'fields': [
                {'name': 'system_mode', 'label': 'Salt system mode', 'type': 'enum', 'options': ['conversion', 'cell_replacement'], 'default': 'conversion'},
                {'name': 'pool_gallons', 'label': 'Pool gallons', 'type': 'float', 'default': 15000.0, 'step': 500.0, 'minimum': 1000.0},
                {'name': 'oversize_factor', 'label': 'Oversize factor', 'type': 'float', 'default': 1.5, 'step': 0.1, 'minimum': 1.0},
                {'name': 'automation_compatible', 'label': 'Automation compatible', 'type': 'bool', 'default': False},
                {'name': 'include_startup_salt', 'label': 'Include startup salt', 'type': 'bool', 'default': True},
            ],
        },
        'automation': {
            'label': 'Automation input wizard',
            'default_template_name': 'Automation package template',
            'fields': [
                {'name': 'panel_family', 'label': 'Panel family', 'type': 'enum', 'options': ['Jandy', 'Pentair', 'Hayward', 'Generic'], 'default': 'Generic'},
                {'name': 'relay_count', 'label': 'Relay count', 'type': 'int', 'default': 4, 'step': 1, 'minimum': 1},
                {'name': 'valve_count', 'label': 'Valve count', 'type': 'int', 'default': 2, 'step': 1, 'minimum': 0},
                {'name': 'body_count', 'label': 'Body count', 'type': 'int', 'default': 1, 'step': 1, 'minimum': 1},
                {'name': 'include_heater_integration', 'label': 'Include heater integration', 'type': 'bool', 'default': True},
                {'name': 'include_salt_integration', 'label': 'Include salt integration', 'type': 'bool', 'default': False},
                {'name': 'include_wifi_bridge', 'label': 'Include Wi-Fi / app bridge', 'type': 'bool', 'default': True},
            ],
        },
    },
}


DEFAULT_EQUIPMENT_SELECTOR_CATALOG: dict[str, Any] = {
    'version': 'platform_block_2h_catalog_selectors',
    'families': {
        'pump': {
            'label': 'Pump selector catalog',
            'compatibility_fields': [
                {'name': 'voltage', 'label': 'Voltage', 'type': 'enum', 'options': ['115V', '208-230V', '230V'], 'default': '230V'},
                {'name': 'plumbing_size_in', 'label': 'Plumbing size (in)', 'type': 'float', 'default': 2.0, 'step': 0.5, 'minimum': 1.0},
                {'name': 'speed_type', 'label': 'Speed type', 'type': 'enum', 'options': ['single_speed', 'variable_speed'], 'default': 'variable_speed'},
            ],
            'items': [
                {
                    'item_slug': 'pump-vs-3hp-230',
                    'label': '3 HP Variable Speed Pump 230V',
                    'equipment_name': '3 HP Variable Speed Pump',
                    'default_unit_price': 2450.0,
                    'branch_price_overlays': {'Key West': 2595.0, 'Miami': 2395.0, 'Marathon': 2495.0},
                    'builder_profile': 'variable_speed_upgrade',
                    'builder_options': {'include_controller_integration': True},
                    'selector_tags': {'voltage': '230V', 'speed_type': 'variable_speed', 'min_plumbing_size_in': 2.0},
                },
                {
                    'item_slug': 'pump-single-1hp-115',
                    'label': '1 HP Single Speed Pump 115V',
                    'equipment_name': '1 HP Single Speed Pump',
                    'default_unit_price': 925.0,
                    'branch_price_overlays': {'Key West': 975.0, 'Miami': 899.0},
                    'builder_profile': 'single_speed_swap',
                    'builder_options': {'include_controller_integration': False},
                    'selector_tags': {'voltage': '115V', 'speed_type': 'single_speed', 'min_plumbing_size_in': 1.5},
                },
            ],
        },
        'filter': {
            'label': 'Filter selector catalog',
            'compatibility_fields': [
                {'name': 'filter_style', 'label': 'Filter style', 'type': 'enum', 'options': ['cartridge', 'sand'], 'default': 'cartridge'},
                {'name': 'target_flow_gpm', 'label': 'Target flow (GPM)', 'type': 'float', 'default': 80.0, 'step': 5.0, 'minimum': 10.0},
            ],
            'items': [
                {
                    'item_slug': 'filter-cartridge-425',
                    'label': '425 sqft Cartridge Filter',
                    'equipment_name': '425 sqft Cartridge Filter',
                    'default_unit_price': 1650.0,
                    'branch_price_overlays': {'Key West': 1710.0, 'Miami': 1610.0},
                    'builder_profile': 'cartridge_replacement',
                    'builder_options': {'include_media_charge': False},
                    'selector_tags': {'filter_style': 'cartridge', 'max_flow_gpm': 100.0},
                },
                {
                    'item_slug': 'filter-sand-30',
                    'label': '30 in Sand Filter',
                    'equipment_name': '30 in Sand Filter',
                    'default_unit_price': 1550.0,
                    'branch_price_overlays': {'Key West': 1625.0, 'Miami': 1495.0},
                    'builder_profile': 'sand_filter_replacement',
                    'builder_options': {'include_media_charge': True},
                    'selector_tags': {'filter_style': 'sand', 'max_flow_gpm': 90.0},
                },
            ],
        },
        'salt_system': {
            'label': 'Salt system selector catalog',
            'compatibility_fields': [
                {'name': 'pool_gallons', 'label': 'Pool gallons', 'type': 'float', 'default': 18000.0, 'step': 500.0, 'minimum': 1000.0},
                {'name': 'automation_compatible', 'label': 'Automation compatible', 'type': 'bool', 'default': False},
            ],
            'items': [
                {
                    'item_slug': 'salt-cell-25k',
                    'label': 'Replacement Salt Cell rated for 25,000 gal',
                    'equipment_name': 'Replacement Salt Cell rated for 25,000 gal',
                    'default_unit_price': 999.0,
                    'branch_price_overlays': {'Key West': 1045.0, 'Miami': 979.0},
                    'builder_profile': 'cell_replacement',
                    'builder_options': {'include_salt_charge': False, 'include_controller_integration': False},
                    'selector_tags': {'max_pool_gallons': 25000.0, 'automation_required': False},
                },
                {
                    'item_slug': 'salt-system-40k-auto',
                    'label': 'Salt System rated for 40,000 gal with automation support',
                    'equipment_name': 'Salt System rated for 40,000 gal',
                    'default_unit_price': 1895.0,
                    'branch_price_overlays': {'Key West': 1965.0, 'Miami': 1845.0},
                    'builder_profile': 'salt_conversion',
                    'builder_options': {'include_salt_charge': True, 'include_controller_integration': True},
                    'selector_tags': {'max_pool_gallons': 40000.0, 'automation_required': True},
                },
            ],
        },
        'automation': {
            'label': 'Automation selector catalog',
            'compatibility_fields': [
                {'name': 'relay_count', 'label': 'Relay count needed', 'type': 'int', 'default': 4, 'step': 1, 'minimum': 1},
                {'name': 'body_count', 'label': 'Body count', 'type': 'int', 'default': 1, 'step': 1, 'minimum': 1},
                {'name': 'include_heater_integration', 'label': 'Include heater integration', 'type': 'bool', 'default': True},
                {'name': 'include_salt_integration', 'label': 'Include salt integration', 'type': 'bool', 'default': False},
            ],
            'items': [
                {
                    'item_slug': 'automation-4relay',
                    'label': '4 Relay Automation Panel',
                    'equipment_name': '4 Relay Automation Panel',
                    'default_unit_price': 1895.0,
                    'branch_price_overlays': {'Key West': 1975.0, 'Miami': 1845.0},
                    'builder_profile': 'automation_addon',
                    'builder_options': {'include_relay_pack': False, 'include_actuator_pack': True, 'include_controller_integration': True},
                    'selector_tags': {'minimum_relays': 4, 'minimum_bodies': 1, 'heater_support': True, 'salt_support': False},
                },
                {
                    'item_slug': 'automation-8relay',
                    'label': '8 Relay Dual Body Automation Panel',
                    'equipment_name': '8 Relay Dual Body Automation Panel',
                    'default_unit_price': 2895.0,
                    'branch_price_overlays': {'Key West': 2995.0, 'Miami': 2795.0},
                    'builder_profile': 'panel_upgrade',
                    'builder_options': {'include_relay_pack': True, 'include_actuator_pack': True, 'include_controller_integration': True},
                    'selector_tags': {'minimum_relays': 8, 'minimum_bodies': 2, 'heater_support': True, 'salt_support': True},
                },
            ],
        },
    },
}



def get_equipment_family_builder_catalog(session: Session | None = None) -> dict[str, Any]:
    return loads(dumps(DEFAULT_EQUIPMENT_FAMILY_BUILDER_CONFIG), {})


def get_equipment_family_builder_wizard_catalog(session: Session | None = None) -> dict[str, Any]:
    return loads(dumps(DEFAULT_EQUIPMENT_FAMILY_WIZARD_CONFIG), {})

def get_equipment_selector_catalog(session: Session | None = None) -> dict[str, Any]:
    return loads(dumps(DEFAULT_EQUIPMENT_SELECTOR_CATALOG), {})




def _resolve_equipment_selector_family(package_kind: str) -> dict[str, Any]:
    catalog = get_equipment_selector_catalog()
    families = catalog.get('families', {}) if isinstance(catalog.get('families'), dict) else {}
    normalized_kind = _normalize_template_package_kind(package_kind)
    family = families.get(normalized_kind)
    if not isinstance(family, dict):
        raise ValueError('Unsupported equipment selector family')
    return family


def _normalize_equipment_selector_context(package_kind: str, compatibility_context: dict[str, Any] | None) -> dict[str, Any]:
    family = _resolve_equipment_selector_family(package_kind)
    incoming = compatibility_context if isinstance(compatibility_context, dict) else {}
    normalized: dict[str, Any] = {}
    for field in family.get('compatibility_fields', []):
        if not isinstance(field, dict):
            continue
        name = str(field.get('name') or '').strip()
        if not name:
            continue
        field_type = str(field.get('type') or 'text')
        default = field.get('default')
        raw_value = incoming.get(name, default)
        if field_type == 'bool':
            normalized[name] = bool(raw_value)
        elif field_type == 'int':
            try:
                normalized[name] = int(raw_value)
            except (TypeError, ValueError):
                normalized[name] = int(default or 0)
        elif field_type == 'float':
            try:
                normalized[name] = float(raw_value)
            except (TypeError, ValueError):
                normalized[name] = float(default or 0.0)
        else:
            normalized[name] = str(raw_value or default or '').strip()
    return normalized


def _resolve_equipment_selector_item(package_kind: str, item_slug: str) -> tuple[dict[str, Any], dict[str, Any], str]:
    family = _resolve_equipment_selector_family(package_kind)
    normalized_kind = _normalize_template_package_kind(package_kind)
    item_slug = str(item_slug or '').strip()
    items = family.get('items', []) if isinstance(family.get('items'), list) else []
    for item in items:
        if isinstance(item, dict) and str(item.get('item_slug') or '') == item_slug:
            return family, item, normalized_kind
    raise ValueError('Equipment selector item not found')


def evaluate_equipment_selector_compatibility(package_kind: str, item_slug: str, compatibility_context: dict[str, Any] | None = None) -> dict[str, Any]:
    family, item, normalized_kind = _resolve_equipment_selector_item(package_kind, item_slug)
    context = _normalize_equipment_selector_context(normalized_kind, compatibility_context)
    tags = item.get('selector_tags', {}) if isinstance(item.get('selector_tags'), dict) else {}
    issues: list[str] = []
    warnings: list[str] = []

    if normalized_kind == 'pump':
        expected_voltage = str(tags.get('voltage') or '').strip()
        if expected_voltage and str(context.get('voltage') or '') != expected_voltage:
            issues.append(f"Requires {expected_voltage}, but selector context is {context.get('voltage') or 'unspecified'}.")
        expected_speed = str(tags.get('speed_type') or '').strip()
        if expected_speed and str(context.get('speed_type') or '') != expected_speed:
            issues.append(f"Requires {expected_speed.replace('_', ' ')}, but selector context is {str(context.get('speed_type') or 'unspecified').replace('_', ' ')}.")
        min_plumbing = float(tags.get('min_plumbing_size_in') or 0)
        if float(context.get('plumbing_size_in') or 0) < min_plumbing:
            issues.append(f"Needs at least {min_plumbing:g} in plumbing, but selector context is {float(context.get('plumbing_size_in') or 0):g} in.")

    elif normalized_kind == 'filter':
        expected_style = str(tags.get('filter_style') or '').strip()
        if expected_style and str(context.get('filter_style') or '') != expected_style:
            issues.append(f"Designed for {expected_style} applications, but selector context is {context.get('filter_style') or 'unspecified'}.")
        max_flow = float(tags.get('max_flow_gpm') or 0)
        target_flow = float(context.get('target_flow_gpm') or 0)
        if max_flow and target_flow > max_flow:
            issues.append(f"Target flow {target_flow:g} GPM exceeds selector limit of {max_flow:g} GPM.")
        elif max_flow and target_flow > max_flow * 0.9:
            warnings.append(f"Target flow {target_flow:g} GPM is close to the selector limit of {max_flow:g} GPM.")

    elif normalized_kind == 'salt_system':
        max_gallons = float(tags.get('max_pool_gallons') or 0)
        pool_gallons = float(context.get('pool_gallons') or 0)
        if max_gallons and pool_gallons > max_gallons:
            issues.append(f"Pool {pool_gallons:,.0f} gal exceeds selector rating of {max_gallons:,.0f} gal.")
        if bool(tags.get('automation_required')) and not bool(context.get('automation_compatible')):
            issues.append('Selector item requires automation-compatible installation.')

    elif normalized_kind == 'automation':
        min_relays = int(tags.get('minimum_relays') or 0)
        relay_count = int(context.get('relay_count') or 0)
        if min_relays and relay_count < min_relays:
            issues.append(f"Needs at least {min_relays} relays, but selector context is {relay_count}.")
        min_bodies = int(tags.get('minimum_bodies') or 0)
        body_count = int(context.get('body_count') or 0)
        if min_bodies and body_count < min_bodies:
            issues.append(f"Needs at least {min_bodies} body circuits, but selector context is {body_count}.")
        if bool(context.get('include_heater_integration')) and not bool(tags.get('heater_support', False)):
            issues.append('Selector item does not support heater integration.')
        if bool(context.get('include_salt_integration')) and not bool(tags.get('salt_support', False)):
            issues.append('Selector item does not support salt integration.')

    return {
        'package_kind': normalized_kind,
        'item_slug': str(item.get('item_slug') or ''),
        'item_label': str(item.get('label') or item.get('equipment_name') or ''),
        'compatible': not issues,
        'issues': issues,
        'warnings': warnings,
        'normalized_context': context,
    }




def _normalize_branch_name(branch_name: str | None) -> str:
    return str(branch_name or '').strip().lower()


def _resolve_selector_branch_price(item: dict[str, Any], preferred_branch: str = '') -> dict[str, Any]:
    default_unit_price = round(float(item.get('default_unit_price') or 0.0), 2)
    overlays = item.get('branch_price_overlays', {}) if isinstance(item.get('branch_price_overlays'), dict) else {}
    preferred = str(preferred_branch or '').strip()
    if preferred:
        for branch_name, raw_price in overlays.items():
            if _normalize_branch_name(branch_name) == _normalize_branch_name(preferred):
                try:
                    price = round(float(raw_price or 0.0), 2)
                except (TypeError, ValueError):
                    price = default_unit_price
                return {
                    'effective_unit_price': price,
                    'default_unit_price': default_unit_price,
                    'price_source': f'branch_overlay:{branch_name}',
                    'branch_name': str(branch_name),
                    'preferred_branch': preferred,
                    'branch_price_overlays': {str(k): round(float(v or 0.0), 2) for k, v in overlays.items()},
                }
    return {
        'effective_unit_price': default_unit_price,
        'default_unit_price': default_unit_price,
        'price_source': 'default_catalog',
        'branch_name': '',
        'preferred_branch': preferred,
        'branch_price_overlays': {str(k): round(float(v or 0.0), 2) for k, v in overlays.items()},
    }


def score_equipment_selector_candidates(
    session: Session,
    *,
    package_kind: str,
    compatibility_context: dict[str, Any] | None = None,
    preferred_branch: str = '',
    limit: int = 10,
) -> dict[str, Any]:
    family = _resolve_equipment_selector_family(package_kind)
    normalized_kind = _normalize_template_package_kind(package_kind)
    items = [item for item in family.get('items', []) if isinstance(item, dict)]
    context = _normalize_equipment_selector_context(normalized_kind, compatibility_context)
    config = ensure_heater_quote_settings(session)
    scoring = config.get('selector_scoring', {}) if isinstance(config.get('selector_scoring'), dict) else {}
    compatibility_base = float(scoring.get('compatibility_base') or 100.0)
    issue_penalty = float(scoring.get('issue_penalty') or 30.0)
    warning_penalty = float(scoring.get('warning_penalty') or 6.0)
    price_weight = float(scoring.get('price_weight') or 18.0)
    branch_bonus_value = float(scoring.get('branch_bonus') or 8.0)
    branch_miss_penalty = float(scoring.get('branch_miss_penalty') or 4.0)

    raw_candidates: list[dict[str, Any]] = []
    prices: list[float] = []
    for item in items:
        compatibility = evaluate_equipment_selector_compatibility(normalized_kind, str(item.get('item_slug') or ''), context)
        price_info = _resolve_selector_branch_price(item, preferred_branch)
        effective_price = float(price_info.get('effective_unit_price') or 0.0)
        if effective_price > 0:
            prices.append(effective_price)
        raw_candidates.append({
            'item': item,
            'compatibility': compatibility,
            'price_info': price_info,
            'effective_unit_price': effective_price,
        })

    if prices:
        min_price = min(prices)
        max_price = max(prices)
    else:
        min_price = 0.0
        max_price = 0.0

    candidates: list[dict[str, Any]] = []
    for entry in raw_candidates:
        item = entry['item']
        compatibility = entry['compatibility']
        price_info = entry['price_info']
        compatible = bool(compatibility.get('compatible'))
        issue_count = len(compatibility.get('issues', []))
        warning_count = len(compatibility.get('warnings', []))
        compatibility_score = max(0.0, compatibility_base - issue_penalty * issue_count - warning_penalty * warning_count)
        if prices and max_price > min_price:
            price_score = round(((max_price - entry['effective_unit_price']) / (max_price - min_price)) * price_weight, 2)
        elif prices:
            price_score = round(price_weight / 2.0, 2)
        else:
            price_score = 0.0
        if preferred_branch:
            if str(price_info.get('price_source') or '').startswith('branch_overlay:'):
                branch_score = branch_bonus_value
            else:
                branch_score = -branch_miss_penalty
        else:
            branch_score = 0.0
        total_score = round(compatibility_score + price_score + branch_score, 2)
        selector_item = {
            'item_slug': str(item.get('item_slug') or ''),
            'label': str(item.get('label') or ''),
            'equipment_name': str(item.get('equipment_name') or item.get('label') or ''),
            'default_unit_price': float(item.get('default_unit_price') or 0.0),
            'effective_unit_price': float(price_info.get('effective_unit_price') or 0.0),
            'price_source': str(price_info.get('price_source') or 'default_catalog'),
            'branch_name': str(price_info.get('branch_name') or ''),
            'preferred_branch': str(price_info.get('preferred_branch') or ''),
            'branch_price_overlays': price_info.get('branch_price_overlays', {}),
            'builder_profile': str(item.get('builder_profile') or ''),
        }
        candidates.append({
            'selector_item': selector_item,
            'compatible': compatible,
            'issues': compatibility.get('issues', []),
            'warnings': compatibility.get('warnings', []),
            'normalized_context': compatibility.get('normalized_context', {}),
            'score': total_score,
            'score_breakdown': {
                'compatibility_score': round(compatibility_score, 2),
                'price_score': round(price_score, 2),
                'branch_score': round(branch_score, 2),
            },
            'recommendation_reason': (
                'Compatible and best scored for the selected context.' if compatible else 'Lower-ranked because of compatibility issues.'
            ),
        })

    candidates.sort(
        key=lambda item: (
            0 if item['compatible'] else 1,
            -float(item.get('score') or 0.0),
            float(item.get('selector_item', {}).get('effective_unit_price') or 0.0),
            str(item.get('selector_item', {}).get('label') or ''),
        )
    )
    for idx, candidate in enumerate(candidates, start=1):
        candidate['rank_order'] = idx
        candidate['recommended'] = idx == 1
        candidate['recommendation_band'] = 'recommended' if idx == 1 and candidate['compatible'] else ('review' if candidate['compatible'] else 'incompatible')
    limited = candidates[: max(1, int(limit or 10))]
    return {
        'package_kind': normalized_kind,
        'family_label': str(family.get('label') or normalized_kind.replace('_', ' ').title()),
        'preferred_branch': str(preferred_branch or ''),
        'normalized_context': context,
        'candidate_count': len(candidates),
        'compatible_count': sum(1 for item in candidates if item['compatible']),
        'recommended_item_slug': limited[0]['selector_item']['item_slug'] if limited else '',
        'candidates': limited,
    }


def build_equipment_package_template_from_selector_preview(
    session: Session,
    *,
    package_kind: str,
    item_slug: str,
    quantity: int = 1,
    saved_by: str = 'operator',
    template_name: str = '',
    template_description: str = '',
    labor_profile: str | None = None,
    compatibility_context: dict[str, Any] | None = None,
    preferred_branch: str = '',
    misc_materials_amount: float = 0.0,
) -> dict[str, Any]:
    family, item, normalized_kind = _resolve_equipment_selector_item(package_kind, item_slug)
    rankings = score_equipment_selector_candidates(
        session,
        package_kind=normalized_kind,
        compatibility_context=compatibility_context,
        preferred_branch=preferred_branch,
        limit=10,
    )
    selected_ranking = next((entry for entry in rankings.get('candidates', []) if entry.get('selector_item', {}).get('item_slug') == str(item.get('item_slug') or '')), None)
    compatibility = selected_ranking.get('normalized_context') if isinstance(selected_ranking, dict) else None
    compatibility_result = evaluate_equipment_selector_compatibility(normalized_kind, item_slug, compatibility_context)
    selector_item = selected_ranking.get('selector_item', {}) if isinstance(selected_ranking, dict) else _resolve_selector_branch_price(item, preferred_branch)
    effective_unit_price = float(selector_item.get('effective_unit_price') or item.get('default_unit_price') or 0)
    preview = build_equipment_package_template_from_builder_preview(
        session,
        package_kind=normalized_kind,
        builder_profile=str(item.get('builder_profile') or ''),
        equipment_name=str(item.get('equipment_name') or item.get('label') or 'Equipment').strip(),
        equipment_unit_price=effective_unit_price,
        quantity=quantity,
        saved_by=saved_by,
        template_description=(template_description or str(item.get('label') or '')).strip(),
        labor_profile=labor_profile,
        misc_materials_amount=misc_materials_amount,
        **(item.get('builder_options') if isinstance(item.get('builder_options'), dict) else {}),
    )
    preview['selector_item'] = {
        'item_slug': str(item.get('item_slug') or ''),
        'label': str(item.get('label') or ''),
        'equipment_name': str(item.get('equipment_name') or ''),
        'default_unit_price': float(item.get('default_unit_price') or 0),
        'effective_unit_price': effective_unit_price,
        'price_source': str(selector_item.get('price_source') or 'default_catalog'),
        'branch_name': str(selector_item.get('branch_name') or ''),
        'preferred_branch': str(selector_item.get('preferred_branch') or preferred_branch or ''),
        'builder_profile': str(item.get('builder_profile') or ''),
    }
    preview['selector_scoring'] = {
        'score': float(selected_ranking.get('score') or 0) if isinstance(selected_ranking, dict) else 0.0,
        'score_breakdown': selected_ranking.get('score_breakdown', {}) if isinstance(selected_ranking, dict) else {},
        'recommendation_rank': int(selected_ranking.get('rank_order') or 0) if isinstance(selected_ranking, dict) else 0,
        'recommended': bool(selected_ranking.get('recommended')) if isinstance(selected_ranking, dict) else False,
    }
    preview['selector_recommendations'] = rankings
    preview['compatibility'] = compatibility_result
    preview['suggested_template_name'] = template_name or f"{str(item.get('label') or family.get('label') or normalized_kind.title()).strip()} template"
    return preview


def create_equipment_package_template_from_selector(
    session: Session,
    *,
    template_name: str,
    package_kind: str,
    item_slug: str,
    quantity: int = 1,
    saved_by: str = 'operator',
    template_description: str = '',
    labor_profile: str | None = None,
    compatibility_context: dict[str, Any] | None = None,
    preferred_branch: str = '',
    misc_materials_amount: float = 0.0,
) -> dict[str, Any]:
    preview = build_equipment_package_template_from_selector_preview(
        session,
        package_kind=package_kind,
        item_slug=item_slug,
        quantity=quantity,
        saved_by=saved_by,
        template_name=template_name,
        template_description=template_description,
        labor_profile=labor_profile,
        compatibility_context=compatibility_context,
        preferred_branch=preferred_branch,
        misc_materials_amount=misc_materials_amount,
    )
    compatibility = preview.get('compatibility', {}) if isinstance(preview.get('compatibility'), dict) else {}
    if not bool(compatibility.get('compatible')):
        joined = '; '.join(str(item) for item in compatibility.get('issues', []) if str(item).strip()) or 'Selected catalog item is incompatible.'
        raise ValueError(joined)
    existing = _get_equipment_package_templates(session)
    template_slug = _next_available_template_slug(existing, _slugify_template_name(template_name or f"{preview['package_kind']}-selector-package"))
    now_iso = datetime.utcnow().isoformat()
    selector_item = preview.get('selector_item', {}) if isinstance(preview.get('selector_item'), dict) else {}
    template = {
        'template_slug': template_slug,
        'template_name': str(template_name or preview.get('suggested_template_name') or f"{preview['package_kind']} selector template").strip(),
        'package_kind': preview['package_kind'],
        'saved_by': saved_by,
        'created_at': now_iso,
        'updated_at': now_iso,
        'source_quote_case_id': None,
        'source_external_link_id': None,
        'candidate': {},
        'package_summary': preview['package_summary'],
        'prepared_lines': preview['prepared_lines'],
        'original_prepared_lines': preview['prepared_lines'],
        'template_description': template_description,
        'selector_item': selector_item,
        'compatibility_context': compatibility.get('normalized_context', {}),
        'selector_scoring': preview.get('selector_scoring', {}),
        'selector_preferred_branch': str(preview.get('selector_item', {}).get('preferred_branch') or preferred_branch or ''),
        'builder_profile': preview.get('builder_profile', ''),
        'builder_profile_label': preview.get('builder_profile_label', ''),
    }
    templates = existing + [template]
    set_setting(
        session,
        'equipment_package_templates',
        {'version': DEFAULT_EQUIPMENT_PACKAGE_TEMPLATE_CONFIG['version'], 'templates': templates},
        'Reusable equipment package templates saved from attached quote packages and later applied back into quote cases.',
    )
    return {
        'saved_template': template,
        'template_summary': get_equipment_package_template_summary(session),
        'selector_preview': preview,
    }

def _resolve_equipment_family_builder_wizard(package_kind: str) -> dict[str, Any]:
    catalog = get_equipment_family_builder_wizard_catalog()
    families = catalog.get('families', {}) if isinstance(catalog.get('families'), dict) else {}
    normalized_kind = _normalize_template_package_kind(package_kind)
    family = families.get(normalized_kind)
    if not isinstance(family, dict):
        raise ValueError('Unsupported equipment package wizard family')
    return family


def _normalize_equipment_family_wizard_inputs(package_kind: str, wizard_inputs: dict[str, Any] | None) -> dict[str, Any]:
    family = _resolve_equipment_family_builder_wizard(package_kind)
    incoming = wizard_inputs if isinstance(wizard_inputs, dict) else {}
    normalized: dict[str, Any] = {}
    for field in family.get('fields', []):
        if not isinstance(field, dict):
            continue
        name = str(field.get('name') or '').strip()
        if not name:
            continue
        field_type = str(field.get('type') or 'text')
        default = field.get('default')
        raw_value = incoming.get(name, default)
        if field_type == 'bool':
            normalized[name] = bool(raw_value)
        elif field_type == 'int':
            try:
                normalized[name] = int(raw_value)
            except (TypeError, ValueError):
                normalized[name] = int(default or 0)
        elif field_type == 'float':
            try:
                normalized[name] = float(raw_value)
            except (TypeError, ValueError):
                normalized[name] = float(default or 0.0)
        else:
            normalized[name] = str(raw_value or default or '').strip()
    return normalized


def _derive_builder_parameters_from_wizard(package_kind: str, wizard_inputs: dict[str, Any]) -> dict[str, Any]:
    normalized_kind = _normalize_template_package_kind(package_kind)
    data = _normalize_equipment_family_wizard_inputs(normalized_kind, wizard_inputs)

    if normalized_kind == 'pump':
        pump_style = str(data.get('pump_style') or 'variable_speed')
        horsepower = float(data.get('horsepower') or 0)
        voltage = str(data.get('voltage') or '230V')
        plumbing_size = float(data.get('plumbing_size_in') or 0)
        union_size = float(data.get('union_size_in') or 0)
        automation_integration = bool(data.get('automation_integration'))
        equipment_name = f"{horsepower:g} HP {'Variable Speed' if pump_style == 'variable_speed' else 'Single Speed'} Pump ({voltage})"
        return {
            'builder_profile': 'variable_speed_upgrade' if pump_style == 'variable_speed' else 'single_speed_swap',
            'equipment_name': equipment_name,
            'wizard_summary': f"{plumbing_size:g} in plumbing, {union_size:g} in unions, {voltage}",
            'builder_options': {
                'include_controller_integration': automation_integration,
            },
            'wizard_inputs': data,
        }

    if normalized_kind == 'filter':
        filter_style = str(data.get('filter_style') or 'cartridge')
        flow = float(data.get('target_flow_gpm') or 0)
        filter_area = float(data.get('filter_area_sqft') or 0)
        tank_diameter = float(data.get('tank_diameter_in') or 0)
        include_media = bool(data.get('include_media_charge'))
        if filter_style == 'sand':
            equipment_name = f"{tank_diameter:g} in Sand Filter"
            builder_profile = 'sand_filter_replacement'
        else:
            equipment_name = f"{filter_area:g} sqft Cartridge Filter"
            builder_profile = 'cartridge_replacement'
        return {
            'builder_profile': builder_profile,
            'equipment_name': equipment_name,
            'wizard_summary': f"Target flow {flow:g} GPM",
            'builder_options': {
                'include_media_charge': include_media,
            },
            'wizard_inputs': data,
        }

    if normalized_kind == 'salt_system':
        system_mode = str(data.get('system_mode') or 'conversion')
        pool_gallons = float(data.get('pool_gallons') or 0)
        oversize_factor = float(data.get('oversize_factor') or 1.0)
        automation_compatible = bool(data.get('automation_compatible'))
        include_startup_salt = bool(data.get('include_startup_salt'))
        rated_gallons = int(round(pool_gallons * oversize_factor / 1000.0) * 1000)
        if rated_gallons <= 0:
            rated_gallons = int(pool_gallons)
        equipment_name = (
            f"Replacement Salt Cell rated for {rated_gallons:,} gal"
            if system_mode == 'cell_replacement'
            else f"Salt System rated for {rated_gallons:,} gal"
        )
        return {
            'builder_profile': 'cell_replacement' if system_mode == 'cell_replacement' else 'salt_conversion',
            'equipment_name': equipment_name,
            'wizard_summary': f"Pool {pool_gallons:,.0f} gal, oversize factor {oversize_factor:g}",
            'builder_options': {
                'include_controller_integration': automation_compatible,
                'include_salt_charge': include_startup_salt,
            },
            'wizard_inputs': data,
        }

    if normalized_kind == 'automation':
        panel_family = str(data.get('panel_family') or 'Generic')
        relay_count = int(data.get('relay_count') or 0)
        valve_count = int(data.get('valve_count') or 0)
        body_count = int(data.get('body_count') or 1)
        include_heater_integration = bool(data.get('include_heater_integration'))
        include_salt_integration = bool(data.get('include_salt_integration'))
        include_wifi_bridge = bool(data.get('include_wifi_bridge'))
        builder_profile = 'panel_upgrade' if body_count > 1 or relay_count >= 5 else 'automation_addon'
        equipment_name = f"{panel_family} Automation Panel ({relay_count} relays, {body_count} body)"
        return {
            'builder_profile': builder_profile,
            'equipment_name': equipment_name,
            'wizard_summary': f"{valve_count} valves, heater integration {'yes' if include_heater_integration else 'no'}, salt integration {'yes' if include_salt_integration else 'no'}",
            'builder_options': {
                'include_relay_pack': relay_count >= 5,
                'include_actuator_pack': valve_count > 0,
                'include_controller_integration': include_heater_integration or include_salt_integration or include_wifi_bridge,
            },
            'wizard_inputs': data,
        }

    raise ValueError('Unsupported equipment package wizard family')


def build_equipment_package_template_from_wizard_preview(
    session: Session,
    *,
    package_kind: str,
    wizard_inputs: dict[str, Any] | None,
    equipment_unit_price: float,
    quantity: int = 1,
    saved_by: str = 'operator',
    template_name: str = '',
    template_description: str = '',
    labor_profile: str | None = None,
    misc_materials_amount: float = 0.0,
) -> dict[str, Any]:
    resolved = _derive_builder_parameters_from_wizard(package_kind, wizard_inputs or {})
    preview = build_equipment_package_template_from_builder_preview(
        session,
        package_kind=package_kind,
        builder_profile=resolved['builder_profile'],
        equipment_name=resolved['equipment_name'],
        equipment_unit_price=equipment_unit_price,
        quantity=quantity,
        saved_by=saved_by,
        template_description=(template_description or resolved.get('wizard_summary') or '').strip(),
        labor_profile=labor_profile,
        misc_materials_amount=misc_materials_amount,
        **resolved.get('builder_options', {}),
    )
    preview['wizard_inputs'] = resolved.get('wizard_inputs', {})
    preview['wizard_summary'] = resolved.get('wizard_summary', '')
    preview['resolved_builder_profile'] = resolved.get('builder_profile', '')
    preview['suggested_equipment_name'] = resolved.get('equipment_name', '')
    preview['suggested_template_name'] = template_name or f"{_resolve_equipment_family_builder_wizard(package_kind).get('default_template_name', str(package_kind).title())}"
    return preview


def create_equipment_package_template_from_wizard(
    session: Session,
    *,
    template_name: str,
    package_kind: str,
    wizard_inputs: dict[str, Any] | None,
    equipment_unit_price: float,
    quantity: int = 1,
    saved_by: str = 'operator',
    template_description: str = '',
    labor_profile: str | None = None,
    misc_materials_amount: float = 0.0,
) -> dict[str, Any]:
    preview = build_equipment_package_template_from_wizard_preview(
        session,
        package_kind=package_kind,
        wizard_inputs=wizard_inputs,
        equipment_unit_price=equipment_unit_price,
        quantity=quantity,
        saved_by=saved_by,
        template_name=template_name,
        template_description=template_description,
        labor_profile=labor_profile,
        misc_materials_amount=misc_materials_amount,
    )
    existing = _get_equipment_package_templates(session)
    template_slug = _next_available_template_slug(existing, _slugify_template_name(template_name or f"{preview['package_kind']}-wizard-package"))
    now_iso = datetime.utcnow().isoformat()
    template = {
        'template_slug': template_slug,
        'template_name': str(template_name or preview.get('suggested_template_name') or f"{preview['package_kind']} package template").strip(),
        'package_kind': preview['package_kind'],
        'saved_by': saved_by,
        'created_at': now_iso,
        'updated_at': now_iso,
        'source_quote_case_id': None,
        'source_external_link_id': None,
        'candidate': {},
        'package_summary': preview['package_summary'],
        'prepared_lines': preview['prepared_lines'],
        'original_prepared_lines': preview['prepared_lines'],
        'template_description': template_description,
        'builder_profile': preview.get('resolved_builder_profile', ''),
        'wizard_inputs': preview.get('wizard_inputs', {}),
        'wizard_summary': preview.get('wizard_summary', ''),
    }
    templates = existing + [template]
    set_setting(
        session,
        'equipment_package_templates',
        {'version': DEFAULT_EQUIPMENT_PACKAGE_TEMPLATE_CONFIG['version'], 'templates': templates},
        'Reusable equipment package templates saved from attached quote packages and later applied back into quote cases.',
    )
    return {
        'saved_template': template,
        'template_summary': get_equipment_package_template_summary(session),
        'wizard_preview': preview,
    }



def _slugify_template_name(value: str) -> str:
    slug = ''.join(ch.lower() if ch.isalnum() else '-' for ch in str(value or '').strip())
    while '--' in slug:
        slug = slug.replace('--', '-')
    return slug.strip('-') or 'equipment-package'


def _ensure_equipment_package_template_settings(session: Session) -> dict[str, Any]:
    existing = get_setting(session, 'equipment_package_templates')
    if not isinstance(existing, dict):
        existing = {}
    templates = existing.get('templates') if isinstance(existing.get('templates'), list) else []
    normalized = {
        'version': DEFAULT_EQUIPMENT_PACKAGE_TEMPLATE_CONFIG['version'],
        'templates': [item for item in templates if isinstance(item, dict)],
    }
    if existing != normalized:
        set_setting(
            session,
            'equipment_package_templates',
            normalized,
            'Reusable equipment package templates saved from attached quote packages and later applied back into quote cases.',
        )
    return normalized


def _get_equipment_package_templates(session: Session) -> list[dict[str, Any]]:
    settings = _ensure_equipment_package_template_settings(session)
    templates = settings.get('templates') if isinstance(settings.get('templates'), list) else []
    return [item for item in templates if isinstance(item, dict)]


def list_equipment_package_templates(session: Session, package_kind: str | None = None) -> list[dict[str, Any]]:
    templates = _get_equipment_package_templates(session)
    if package_kind:
        templates = [item for item in templates if str(item.get('package_kind') or '') == package_kind]
    return sorted(templates, key=lambda item: (str(item.get('template_name') or '').lower(), str(item.get('template_slug') or '').lower()))


def get_equipment_package_template_summary(session: Session) -> dict[str, Any]:
    templates = _get_equipment_package_templates(session)
    by_kind: dict[str, int] = {}
    for item in templates:
        kind = str(item.get('package_kind') or 'unknown')
        by_kind[kind] = by_kind.get(kind, 0) + 1
    return {
        'template_count': len(templates),
        'by_kind': by_kind,
        'templates': list_equipment_package_templates(session),
    }


def _next_available_template_slug(existing_templates: list[dict[str, Any]], base_slug: str) -> str:
    taken = {str(item.get('template_slug') or '') for item in existing_templates}
    if base_slug not in taken:
        return base_slug
    index = 2
    while f'{base_slug}-{index}' in taken:
        index += 1
    return f'{base_slug}-{index}'




def _normalize_template_package_kind(value: str | None) -> str:
    kind = str(value or '').strip().lower()
    return kind or 'equipment'


def _attached_package_kind_from_payload(link: QuoteCaseExternalLink, payload: dict[str, Any] | None = None) -> str:
    payload = payload or _safe_load(link.payload_json)
    package_summary = payload.get('package_summary') if isinstance(payload.get('package_summary'), dict) else {}
    source_payload = payload.get('source_payload') if isinstance(payload.get('source_payload'), dict) else {}
    candidate = payload.get('candidate') if isinstance(payload.get('candidate'), dict) else {}
    kind = (
        package_summary.get('package_kind')
        or package_summary.get('package_family')
        or source_payload.get('package_kind')
        or source_payload.get('package_family')
        or payload.get('package_kind')
    )
    if not kind and link.system_slug == 'heater_quote':
        kind = 'heater'
    if not kind and candidate.get('heater_kind'):
        kind = 'heater'
    return _normalize_template_package_kind(str(kind or 'equipment'))


def _normalize_selector_item(selector_item: object, payload: dict[str, Any]) -> dict[str, Any]:
    item = dict(selector_item) if isinstance(selector_item, dict) else {}
    if item.get('item_slug'):
        return item
    payload_dict = payload if isinstance(payload, dict) else {}
    nested = [value for value in (payload_dict.get('selector_item'), payload_dict.get('candidate'), payload_dict.get('source_payload')) if isinstance(value, dict)]
    sources = [item, *nested, payload_dict]
    for source in sources:
        for key in ('item_slug', 'slug', 'catalog_slug', 'selected_item_slug', 'selector_item_slug'):
            value = source.get(key) if isinstance(source, dict) else None
            if value not in (None, ''):
                item['item_slug'] = str(value)
                break
        if item.get('item_slug'):
            break
    if not item.get('display_name'):
        for source in sources:
            if isinstance(source, dict):
                for key in ('display_name', 'label', 'name', 'title', 'model_name'):
                    value = source.get(key)
                    if value not in (None, ''):
                        item['display_name'] = str(value)
                        break
                if item.get('display_name'):
                    break
    return item


def _serialize_attached_equipment_package_link(link: QuoteCaseExternalLink) -> dict[str, Any]:
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
    original_lines = payload.get('original_prepared_lines') or normalized_lines
    if not isinstance(original_lines, list):
        original_lines = normalized_lines
    normalized_original_lines = [item for item in original_lines if isinstance(item, dict)]
    has_overrides = normalized_lines != normalized_original_lines or bool(package_summary.get('edited'))
    package_kind = _attached_package_kind_from_payload(link, payload)
    return {
        'external_link_id': link.id,
        'external_id': link.external_id,
        'external_label': link.external_label,
        'attached_at': link.created_at.isoformat() if link.created_at else '',
        'updated_at': link.updated_at.isoformat() if link.updated_at else '',
        'candidate': payload.get('candidate') if isinstance(payload.get('candidate'), dict) else {},
        'package_kind': package_kind,
        'system_slug': link.system_slug,
        'package_summary': {
            **package_summary,
            'package_kind': package_kind,
            'equipment_total': equipment_total,
            'labor_total': labor_total,
            'materials_total': materials_total,
            'grand_total': grand_total,
            'currency_code': currency_code,
            'line_count': len(normalized_lines),
        },
        'prepared_lines': normalized_lines,
        'original_prepared_lines': normalized_original_lines,
        'has_overrides': has_overrides,
        'selector_item': _normalize_selector_item(payload.get('selector_item'), payload),
        'compatibility': payload.get('compatibility_context') if isinstance(payload.get('compatibility_context'), dict) else {},
        'attached_by': payload.get('attached_by', ''),
    }


def save_heater_package_template(
    session: Session,
    *,
    quote_case_id: int,
    external_link_id: int,
    template_name: str,
    saved_by: str = 'operator',
) -> dict[str, Any]:
    case = get_quote_case(session, quote_case_id)
    if case is None:
        raise ValueError('Quote case not found')
    link = session.get(QuoteCaseExternalLink, external_link_id)
    if link is None or link.quote_case_id != quote_case_id or link.system_slug not in {'heater_quote', 'equipment_package'}:
        raise ValueError('Attached equipment package not found')
    serialized = _serialize_attached_equipment_package_link(link)
    existing = _get_equipment_package_templates(session)
    template_slug = _next_available_template_slug(existing, _slugify_template_name(template_name or serialized.get('external_label') or 'equipment-package'))
    now_iso = datetime.utcnow().isoformat()
    template = {
        'template_slug': template_slug,
        'template_name': str(template_name or serialized.get('external_label') or 'Equipment package template').strip(),
        'package_kind': serialized.get('package_kind', 'equipment'),
        'saved_by': saved_by,
        'created_at': now_iso,
        'updated_at': now_iso,
        'source_quote_case_id': quote_case_id,
        'source_external_link_id': external_link_id,
        'candidate': serialized.get('candidate', {}),
        'package_summary': serialized.get('package_summary', {}),
        'prepared_lines': serialized.get('prepared_lines', []),
        'original_prepared_lines': serialized.get('original_prepared_lines', serialized.get('prepared_lines', [])),
    }
    templates = existing + [template]
    set_setting(
        session,
        'equipment_package_templates',
        {'version': DEFAULT_EQUIPMENT_PACKAGE_TEMPLATE_CONFIG['version'], 'templates': templates},
        'Reusable equipment package templates saved from attached quote packages and later applied back into quote cases.',
    )
    return {
        'saved_template': template,
        'template_summary': get_equipment_package_template_summary(session),
    }


def create_manual_equipment_package_template(
    session: Session,
    *,
    template_name: str,
    package_kind: str,
    lines: list[dict[str, Any]],
    saved_by: str = 'operator',
    template_description: str = '',
    currency_code: str = 'USD',
) -> dict[str, Any]:
    normalized_kind = _normalize_template_package_kind(package_kind)
    normalized_lines = _normalize_package_lines(lines, currency_code)
    package_summary = _summarize_package_lines(
        normalized_lines,
        {'currency_code': currency_code, 'package_kind': normalized_kind, 'template_description': template_description},
        edited=False,
        edited_by=saved_by,
    )
    existing = _get_equipment_package_templates(session)
    template_slug = _next_available_template_slug(existing, _slugify_template_name(template_name or f'{normalized_kind}-package'))
    now_iso = datetime.utcnow().isoformat()
    template = {
        'template_slug': template_slug,
        'template_name': str(template_name or f'{normalized_kind.title()} package template').strip(),
        'package_kind': normalized_kind,
        'saved_by': saved_by,
        'created_at': now_iso,
        'updated_at': now_iso,
        'source_quote_case_id': None,
        'source_external_link_id': None,
        'candidate': {},
        'package_summary': package_summary,
        'prepared_lines': normalized_lines,
        'original_prepared_lines': normalized_lines,
        'template_description': template_description,
    }
    templates = existing + [template]
    set_setting(
        session,
        'equipment_package_templates',
        {'version': DEFAULT_EQUIPMENT_PACKAGE_TEMPLATE_CONFIG['version'], 'templates': templates},
        'Reusable equipment package templates saved from attached quote packages and later applied back into quote cases.',
    )
    return {
        'saved_template': template,
        'template_summary': get_equipment_package_template_summary(session),
    }


def _resolve_equipment_family_builder(package_kind: str, builder_profile: str | None) -> tuple[dict[str, Any], dict[str, Any], str, str]:
    catalog = get_equipment_family_builder_catalog()
    normalized_kind = _normalize_template_package_kind(package_kind)
    family = catalog.get('families', {}).get(normalized_kind)
    if not isinstance(family, dict):
        raise ValueError('Unsupported equipment package family for builder')
    profile_slug = str(builder_profile or family.get('default_profile') or '').strip() or str(family.get('default_profile') or '')
    profiles = family.get('profiles', {}) if isinstance(family.get('profiles'), dict) else {}
    profile = profiles.get(profile_slug)
    if not isinstance(profile, dict):
        raise ValueError('Equipment package builder profile not found')
    return family, profile, normalized_kind, profile_slug


_DEF_BUILDER_OPTION_FIELDS = {
    'include_plumbing_kit': 'plumbing_kit',
    'include_pad_kit': 'pad_kit',
    'include_electrical_allowance': 'electrical_allowance',
    'include_startup_visit': 'startup_visit',
    'include_media_charge': 'media_charge',
    'include_salt_charge': 'salt_charge',
    'include_relay_pack': 'relay_pack',
    'include_actuator_pack': 'actuator_pack',
    'include_controller_integration': 'controller_integration',
}


def _builder_options_from_inputs(profile: dict[str, Any], **kwargs: Any) -> dict[str, bool]:
    defaults = profile.get('default_options', {}) if isinstance(profile.get('default_options'), dict) else {}
    resolved: dict[str, bool] = {}
    for option_name, _slug in _DEF_BUILDER_OPTION_FIELDS.items():
        if option_name in kwargs and kwargs[option_name] is not None:
            resolved[option_name] = bool(kwargs[option_name])
        else:
            resolved[option_name] = bool(defaults.get(option_name, False))
    return resolved



def _append_builder_line(lines: list[dict[str, Any]], profile: dict[str, Any], slug: str, *, enabled: bool, quantity: int, currency_code: str) -> None:
    if not enabled:
        return
    templates = profile.get('line_items', {}) if isinstance(profile.get('line_items'), dict) else {}
    template = templates.get(slug)
    if not isinstance(template, dict):
        return
    qty_mode = str(template.get('qty_mode') or 'per_system')
    line_qty = float(quantity if qty_mode == 'per_unit' else 1.0)
    lines.append(
        {
            'name': str(template.get('name') or slug.replace('_', ' ').title()),
            'description': str(template.get('description') or ''),
            'qty': line_qty,
            'amount': round(float(template.get('amount') or 0), 2),
            'category': str(template.get('category') or 'misc_materials'),
            'code': currency_code,
            'currency_code': currency_code,
        }
    )



def build_equipment_package_template_from_builder_preview(
    session: Session,
    *,
    package_kind: str,
    builder_profile: str,
    equipment_name: str,
    equipment_unit_price: float,
    quantity: int = 1,
    saved_by: str = 'operator',
    template_description: str = '',
    labor_profile: str | None = None,
    include_plumbing_kit: bool | None = None,
    include_pad_kit: bool | None = None,
    include_electrical_allowance: bool | None = None,
    include_startup_visit: bool | None = None,
    include_media_charge: bool | None = None,
    include_salt_charge: bool | None = None,
    include_relay_pack: bool | None = None,
    include_actuator_pack: bool | None = None,
    include_controller_integration: bool | None = None,
    misc_materials_amount: float = 0.0,
    labor_rate_override: float | None = None,
) -> dict[str, Any]:
    family, profile, normalized_kind, profile_slug = _resolve_equipment_family_builder(package_kind, builder_profile)
    quantity = max(int(quantity or 1), 1)
    labor_catalog = get_equipment_family_builder_catalog().get('labor_profiles', {})
    selected_labor_profile = str(labor_profile or family.get('default_labor_profile') or 'standard')
    labor_spec = labor_catalog.get(selected_labor_profile)
    if not isinstance(labor_spec, dict):
        raise ValueError('Equipment package labor profile not found')

    currency_code = 'USD'
    normalized_equipment_name = str(equipment_name or profile.get('default_equipment_name') or f'{family.get("label", normalized_kind.title())} equipment').strip()
    if not normalized_equipment_name:
        raise ValueError('Equipment name is required for a builder package')
    try:
        unit_price = round(float(equipment_unit_price or 0), 2)
    except (TypeError, ValueError):
        unit_price = 0.0
    options = _builder_options_from_inputs(
        profile,
        include_plumbing_kit=include_plumbing_kit,
        include_pad_kit=include_pad_kit,
        include_electrical_allowance=include_electrical_allowance,
        include_startup_visit=include_startup_visit,
        include_media_charge=include_media_charge,
        include_salt_charge=include_salt_charge,
        include_relay_pack=include_relay_pack,
        include_actuator_pack=include_actuator_pack,
        include_controller_integration=include_controller_integration,
    )

    lines: list[dict[str, Any]] = [
        {
            'name': normalized_equipment_name,
            'description': str(profile.get('equipment_description') or ''),
            'qty': float(quantity),
            'amount': unit_price,
            'category': 'equipment',
            'code': currency_code,
            'currency_code': currency_code,
        }
    ]
    for option_name, slug in _DEF_BUILDER_OPTION_FIELDS.items():
        _append_builder_line(lines, profile, slug, enabled=options.get(option_name, False), quantity=quantity, currency_code=currency_code)
    try:
        misc_amount = round(float(misc_materials_amount or 0), 2)
    except (TypeError, ValueError):
        misc_amount = 0.0
    if misc_amount > 0:
        lines.append(
            {
                'name': 'Miscellaneous materials allowance',
                'description': 'Additional one-off materials allowance from the family builder.',
                'qty': 1.0,
                'amount': misc_amount,
                'category': 'misc_materials',
                'code': currency_code,
                'currency_code': currency_code,
            }
        )
    labor_rate = round(float(labor_rate_override if labor_rate_override is not None else labor_spec.get('labor_rate') or 0), 2)
    labor_hours = round(float(labor_spec.get('base_hours') or 0) + (float(labor_spec.get('hours_per_unit') or 0) * quantity), 2)
    lines.append(
        {
            'name': f"{family.get('label', normalized_kind.title())} labor",
            'description': f"{profile.get('label', profile_slug)} labor using {labor_spec.get('label', selected_labor_profile)} profile.",
            'qty': labor_hours,
            'amount': labor_rate,
            'category': 'labor',
            'code': currency_code,
            'currency_code': currency_code,
        }
    )
    normalized_lines = _normalize_package_lines(lines, currency_code)
    package_summary = _summarize_package_lines(
        normalized_lines,
        {
            'currency_code': currency_code,
            'package_kind': normalized_kind,
            'builder_profile': profile_slug,
            'builder_profile_label': profile.get('label', profile_slug),
            'builder_family_label': family.get('label', normalized_kind.title()),
            'labor_profile': selected_labor_profile,
            'labor_profile_label': labor_spec.get('label', selected_labor_profile),
            'template_description': template_description,
            'quantity': quantity,
            'equipment_name': normalized_equipment_name,
            'equipment_unit_price': unit_price,
            'builder_options': options,
        },
        edited=False,
        edited_by=saved_by,
    )
    return {
        'package_kind': normalized_kind,
        'builder_profile': profile_slug,
        'builder_profile_label': profile.get('label', profile_slug),
        'builder_family_label': family.get('label', normalized_kind.title()),
        'labor_profile': selected_labor_profile,
        'labor_profile_label': labor_spec.get('label', selected_labor_profile),
        'builder_options': options,
        'prepared_lines': normalized_lines,
        'package_summary': package_summary,
    }



def create_equipment_package_template_from_builder(
    session: Session,
    *,
    template_name: str,
    package_kind: str,
    builder_profile: str,
    equipment_name: str,
    equipment_unit_price: float,
    quantity: int = 1,
    saved_by: str = 'operator',
    template_description: str = '',
    labor_profile: str | None = None,
    include_plumbing_kit: bool | None = None,
    include_pad_kit: bool | None = None,
    include_electrical_allowance: bool | None = None,
    include_startup_visit: bool | None = None,
    include_media_charge: bool | None = None,
    include_salt_charge: bool | None = None,
    include_relay_pack: bool | None = None,
    include_actuator_pack: bool | None = None,
    include_controller_integration: bool | None = None,
    misc_materials_amount: float = 0.0,
    labor_rate_override: float | None = None,
) -> dict[str, Any]:
    preview = build_equipment_package_template_from_builder_preview(
        session,
        package_kind=package_kind,
        builder_profile=builder_profile,
        equipment_name=equipment_name,
        equipment_unit_price=equipment_unit_price,
        quantity=quantity,
        saved_by=saved_by,
        template_description=template_description,
        labor_profile=labor_profile,
        include_plumbing_kit=include_plumbing_kit,
        include_pad_kit=include_pad_kit,
        include_electrical_allowance=include_electrical_allowance,
        include_startup_visit=include_startup_visit,
        include_media_charge=include_media_charge,
        include_salt_charge=include_salt_charge,
        include_relay_pack=include_relay_pack,
        include_actuator_pack=include_actuator_pack,
        include_controller_integration=include_controller_integration,
        misc_materials_amount=misc_materials_amount,
        labor_rate_override=labor_rate_override,
    )
    existing = _get_equipment_package_templates(session)
    template_slug = _next_available_template_slug(existing, _slugify_template_name(template_name or f"{preview['package_kind']}-package"))
    now_iso = datetime.utcnow().isoformat()
    template = {
        'template_slug': template_slug,
        'template_name': str(template_name or f"{preview['builder_family_label']} template").strip(),
        'package_kind': preview['package_kind'],
        'saved_by': saved_by,
        'created_at': now_iso,
        'updated_at': now_iso,
        'source_quote_case_id': None,
        'source_external_link_id': None,
        'candidate': {},
        'package_summary': preview['package_summary'],
        'prepared_lines': preview['prepared_lines'],
        'original_prepared_lines': preview['prepared_lines'],
        'template_description': template_description,
        'builder_profile': preview['builder_profile'],
        'builder_profile_label': preview['builder_profile_label'],
        'builder_family_label': preview['builder_family_label'],
        'builder_options': preview['builder_options'],
    }
    templates = existing + [template]
    set_setting(
        session,
        'equipment_package_templates',
        {'version': DEFAULT_EQUIPMENT_PACKAGE_TEMPLATE_CONFIG['version'], 'templates': templates},
        'Reusable equipment package templates saved from attached quote packages and later applied back into quote cases.',
    )
    return {
        'saved_template': template,
        'template_summary': get_equipment_package_template_summary(session),
        'builder_preview': preview,
    }


def delete_equipment_package_template(session: Session, template_slug: str) -> dict[str, Any]:
    templates = _get_equipment_package_templates(session)
    remaining = [item for item in templates if str(item.get('template_slug') or '') != template_slug]
    if len(remaining) == len(templates):
        raise ValueError('Equipment package template not found')
    set_setting(
        session,
        'equipment_package_templates',
        {'version': DEFAULT_EQUIPMENT_PACKAGE_TEMPLATE_CONFIG['version'], 'templates': remaining},
        'Reusable equipment package templates saved from attached quote packages and later applied back into quote cases.',
    )
    return {
        'deleted_template_slug': template_slug,
        'template_summary': get_equipment_package_template_summary(session),
    }


def apply_equipment_package_template_to_quote_case(
    session: Session,
    *,
    template_slug: str,
    quote_case_id: int,
    attached_by: str = 'operator',
    replace_existing: bool = False,
) -> dict[str, Any]:
    case = get_quote_case(session, quote_case_id)
    if case is None:
        raise ValueError('Quote case not found')
    template = next((item for item in _get_equipment_package_templates(session) if str(item.get('template_slug') or '') == template_slug), None)
    if template is None:
        raise ValueError('Equipment package template not found')

    package_kind = _normalize_template_package_kind(str(template.get('package_kind') or 'equipment'))

    removed_existing_count = 0
    if replace_existing:
        existing_links = _list_quote_case_equipment_links(session, quote_case_id, package_kind=package_kind)
        removed_existing_count = len(existing_links)
        for existing_link in existing_links:
            session.delete(existing_link)
        if existing_links:
            session.commit()

    package_summary = template.get('package_summary') if isinstance(template.get('package_summary'), dict) else {}
    candidate = template.get('candidate') if isinstance(template.get('candidate'), dict) else {}
    currency_code = str(package_summary.get('currency_code') or candidate.get('currency_code') or 'USD')
    original_lines = template.get('original_prepared_lines') if isinstance(template.get('original_prepared_lines'), list) else template.get('prepared_lines')
    prepared_lines = template.get('prepared_lines') if isinstance(template.get('prepared_lines'), list) else []
    normalized_original = _normalize_package_lines(original_lines or prepared_lines, currency_code)
    normalized_lines = _normalize_package_lines(prepared_lines or original_lines, currency_code)
    package_summary = _summarize_package_lines(
        normalized_lines,
        {**package_summary, 'package_kind': package_kind},
        edited=bool(package_summary.get('edited')),
        edited_by=str(package_summary.get('edited_by') or attached_by),
    )

    system_slug = 'heater_quote' if package_kind == 'heater' else 'equipment_package'
    link = add_external_link(
        session,
        quote_case_id=quote_case_id,
        system_slug=system_slug,
        external_type='template',
        external_id=f"template:{template_slug}:{quote_case_id}:{int(datetime.utcnow().timestamp())}",
        external_label=str(template.get('template_name') or template_slug),
        sync_direction='local_only',
        sync_status='attached',
        payload={
            'attached_by': attached_by,
            'template_slug': template_slug,
            'template_name': template.get('template_name', ''),
            'run_summary': {'source_mode': 'equipment_package_template'},
            'candidate': candidate,
            'package_summary': package_summary,
            'prepared_line': normalized_lines[0] if normalized_lines else {},
            'prepared_lines': normalized_lines,
            'original_prepared_lines': normalized_original,
            'original_package_summary': {**package_summary, 'edited': False},
            'selector_item': template.get('selector_item') if isinstance(template.get('selector_item'), dict) else {},
            'compatibility_context': template.get('compatibility_context') if isinstance(template.get('compatibility_context'), dict) else {},
            'selector_scoring': template.get('selector_scoring') if isinstance(template.get('selector_scoring'), dict) else {},
            'selector_preferred_branch': str(template.get('selector_preferred_branch') or ''),
            'source_payload': {'template_slug': template_slug, 'package_kind': package_kind},
        },
    )
    return {
        'quote_case': serialize_quote_case(session, case),
        'external_link': link.model_dump(),
        'removed_existing_count': removed_existing_count,
        'package_workspace': get_quote_case_equipment_package_workspace(session, quote_case_id),
        'applied_template': template,
        'template_summary': get_equipment_package_template_summary(session),
    }

def _merge_heater_quote_config(config: dict[str, Any] | None) -> dict[str, Any]:
    merged = loads(dumps(DEFAULT_HEATER_QUOTE_CONFIG), {})
    if isinstance(config, dict):
        merged.update({key: value for key, value in config.items() if key not in {'defaults', 'sizing', 'heritage', 'package_profiles', 'labor_profiles'}})
        merged['defaults'].update(config.get('defaults') or {})
        merged['sizing'].update(config.get('sizing') or {})
        merged['heritage'].update(config.get('heritage') or {})
        merged['selector_scoring'].update(config.get('selector_scoring') or {})
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
    merged.setdefault('selector_scoring', DEFAULT_HEATER_QUOTE_CONFIG['selector_scoring'])
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





def _list_quote_case_equipment_links(session: Session, quote_case_id: int, package_kind: str | None = None) -> list[QuoteCaseExternalLink]:
    links = list(
        session.exec(
            select(QuoteCaseExternalLink).where(
                QuoteCaseExternalLink.quote_case_id == quote_case_id,
                QuoteCaseExternalLink.system_slug.in_(['heater_quote', 'equipment_package']),
            ).order_by(QuoteCaseExternalLink.created_at)
        ).all()
    )
    if package_kind:
        normalized_kind = _normalize_template_package_kind(package_kind)
        links = [link for link in links if _attached_package_kind_from_payload(link) == normalized_kind]
    return links


def _list_quote_case_heater_links(session: Session, quote_case_id: int) -> list[QuoteCaseExternalLink]:
    return _list_quote_case_equipment_links(session, quote_case_id, package_kind='heater')


def _line_total(line: dict[str, Any]) -> float:
    try:
        return round(float(line.get('qty') or 0) * float(line.get('amount') or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def _serialize_heater_package_link(link: QuoteCaseExternalLink) -> dict[str, Any]:
    return _serialize_attached_equipment_package_link(link)


def _normalize_package_lines(lines: list[dict[str, Any]], currency_code: str) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in lines:
        if not isinstance(item, dict):
            continue
        name = str(item.get('name') or '').strip()
        if not name:
            continue
        description = str(item.get('description') or '').strip()
        category = str(item.get('category') or 'misc_materials').strip() or 'misc_materials'
        try:
            qty = float(item.get('qty') or 0)
        except (TypeError, ValueError):
            qty = 0.0
        if qty <= 0:
            qty = 1.0
        try:
            amount = round(float(item.get('amount') or item.get('unit_amount') or 0), 2)
        except (TypeError, ValueError):
            amount = 0.0
        normalized.append(
            {
                'type': int(item.get('type', 0) or 0),
                'name': name,
                'description': description,
                'qty': qty,
                'amount': amount,
                'code': str(item.get('code') or item.get('currency_code') or currency_code or 'USD'),
                'currency_code': str(item.get('currency_code') or item.get('code') or currency_code or 'USD'),
                'taxName1': item.get('taxName1', ''),
                'taxAmount1': float(item.get('taxAmount1', 0) or 0),
                'taxName2': item.get('taxName2', ''),
                'taxAmount2': float(item.get('taxAmount2', 0) or 0),
                'category': category,
            }
        )
    if not normalized:
        raise ValueError('At least one valid package line is required.')
    return normalized



def _summarize_package_lines(lines: list[dict[str, Any]], package_summary: dict[str, Any], *, edited: bool, edited_by: str) -> dict[str, Any]:
    equipment_total = round(sum(_line_total(item) for item in lines if str(item.get('category') or '') == 'equipment'), 2)
    labor_total = round(sum(_line_total(item) for item in lines if str(item.get('category') or '') == 'labor'), 2)
    materials_total = round(sum(_line_total(item) for item in lines if str(item.get('category') or '') not in {'equipment', 'labor'}), 2)
    grand_total = round(equipment_total + labor_total + materials_total, 2)
    updated_summary = {
        **(package_summary or {}),
        'equipment_total': equipment_total,
        'labor_total': labor_total,
        'materials_total': materials_total,
        'package_total': grand_total,
        'line_count': len(lines),
        'edited': edited,
    }
    if edited:
        updated_summary['edited_by'] = edited_by
        updated_summary['edited_at'] = datetime.utcnow().isoformat()
    else:
        updated_summary.pop('edited_by', None)
        updated_summary.pop('edited_at', None)
    return updated_summary



def update_heater_package_lines(
    session: Session,
    *,
    quote_case_id: int,
    external_link_id: int,
    edited_lines: list[dict[str, Any]],
    edited_by: str = 'operator',
) -> dict[str, Any]:
    case = get_quote_case(session, quote_case_id)
    if case is None:
        raise ValueError('Quote case not found')
    link = session.get(QuoteCaseExternalLink, external_link_id)
    if link is None or link.quote_case_id != quote_case_id or link.system_slug not in {'heater_quote', 'equipment_package'}:
        raise ValueError('Attached heater package not found')
    payload = _safe_load(link.payload_json)
    currency_code = str((payload.get('package_summary') or {}).get('currency_code') or (payload.get('candidate') or {}).get('currency_code') or 'USD')
    original_lines = payload.get('original_prepared_lines') or payload.get('prepared_lines') or []
    if not isinstance(original_lines, list):
        original_lines = payload.get('prepared_lines') if isinstance(payload.get('prepared_lines'), list) else []
    normalized_original = _normalize_package_lines(original_lines, currency_code) if original_lines else []
    normalized_lines = _normalize_package_lines(edited_lines, currency_code)
    if normalized_original and normalized_lines == normalized_original:
        edited = False
    else:
        edited = True
    payload['original_prepared_lines'] = normalized_original or normalized_lines
    payload['original_package_summary'] = payload.get('original_package_summary') or {**(payload.get('package_summary') or {})}
    payload['prepared_lines'] = normalized_lines
    payload['prepared_line'] = normalized_lines[0] if normalized_lines else {}
    payload['package_summary'] = _summarize_package_lines(normalized_lines, payload.get('package_summary') or {}, edited=edited, edited_by=edited_by)
    link.payload_json = dumps(payload)
    link.updated_at = datetime.utcnow()
    session.add(link)
    session.commit()
    return {
        'external_link_id': external_link_id,
        'quote_case_id': quote_case_id,
        'package_workspace': get_quote_case_equipment_package_workspace(session, quote_case_id),
    }



def reset_heater_package_lines(session: Session, *, quote_case_id: int, external_link_id: int) -> dict[str, Any]:
    case = get_quote_case(session, quote_case_id)
    if case is None:
        raise ValueError('Quote case not found')
    link = session.get(QuoteCaseExternalLink, external_link_id)
    if link is None or link.quote_case_id != quote_case_id or link.system_slug not in {'heater_quote', 'equipment_package'}:
        raise ValueError('Attached heater package not found')
    payload = _safe_load(link.payload_json)
    currency_code = str((payload.get('package_summary') or {}).get('currency_code') or (payload.get('candidate') or {}).get('currency_code') or 'USD')
    original_lines = payload.get('original_prepared_lines') or payload.get('prepared_lines') or []
    if not isinstance(original_lines, list) or not original_lines:
        raise ValueError('No original package lines are stored for this attachment.')
    normalized_original = _normalize_package_lines(original_lines, currency_code)
    original_summary = payload.get('original_package_summary') if isinstance(payload.get('original_package_summary'), dict) else {}
    payload['prepared_lines'] = normalized_original
    payload['prepared_line'] = normalized_original[0] if normalized_original else {}
    payload['package_summary'] = _summarize_package_lines(normalized_original, original_summary, edited=False, edited_by='')
    link.payload_json = dumps(payload)
    link.updated_at = datetime.utcnow()
    session.add(link)
    session.commit()
    return {
        'external_link_id': external_link_id,
        'quote_case_id': quote_case_id,
        'package_workspace': get_quote_case_equipment_package_workspace(session, quote_case_id),
    }




def get_quote_case_equipment_package_workspace(session: Session, quote_case_id: int, package_kind: str | None = None) -> dict[str, Any]:
    packages = [_serialize_attached_equipment_package_link(link) for link in _list_quote_case_equipment_links(session, quote_case_id, package_kind=package_kind)]
    currency_code = next((pkg.get('package_summary', {}).get('currency_code') for pkg in packages if pkg.get('package_summary', {}).get('currency_code')), 'USD')
    equipment_total = round(sum(float(pkg.get('package_summary', {}).get('equipment_total') or 0) for pkg in packages), 2)
    labor_total = round(sum(float(pkg.get('package_summary', {}).get('labor_total') or 0) for pkg in packages), 2)
    materials_total = round(sum(float(pkg.get('package_summary', {}).get('materials_total') or 0) for pkg in packages), 2)
    grand_total = round(sum(float(pkg.get('package_summary', {}).get('grand_total') or 0) for pkg in packages), 2)
    by_kind: dict[str, int] = {}
    for pkg in packages:
        kind = str(pkg.get('package_kind') or 'equipment')
        by_kind[kind] = by_kind.get(kind, 0) + 1
    return {
        'quote_case_id': quote_case_id,
        'package_kind': package_kind,
        'package_count': len(packages),
        'currency_code': currency_code,
        'equipment_total': equipment_total,
        'labor_total': labor_total,
        'materials_total': materials_total,
        'grand_total': grand_total,
        'by_kind': by_kind,
        'packages': packages,
    }


def get_quote_case_heater_package_workspace(session: Session, quote_case_id: int) -> dict[str, Any]:
    return get_quote_case_equipment_package_workspace(session, quote_case_id, package_kind='heater')


def list_quote_case_equipment_package_lines(session: Session, quote_case_id: int, package_kind: str | None = None) -> list[dict[str, Any]]:
    prepared_lines: list[dict[str, Any]] = []
    for package in get_quote_case_equipment_package_workspace(session, quote_case_id, package_kind=package_kind).get('packages', []):
        lines = package.get('prepared_lines') or []
        prepared_lines.extend([item for item in lines if isinstance(item, dict)])
    return prepared_lines


def list_quote_case_heater_package_lines(session: Session, quote_case_id: int) -> list[dict[str, Any]]:
    # Legacy name retained because the FreshBooks sync layer already imports it.
    return list_quote_case_equipment_package_lines(session, quote_case_id)


def remove_equipment_package_from_quote_case(session: Session, *, quote_case_id: int, external_link_id: int) -> dict[str, Any]:
    case = get_quote_case(session, quote_case_id)
    if case is None:
        raise ValueError('Quote case not found')
    link = session.get(QuoteCaseExternalLink, external_link_id)
    if link is None or link.quote_case_id != quote_case_id or link.system_slug not in {'heater_quote', 'equipment_package'}:
        raise ValueError('Attached equipment package not found')
    removed_external_id = link.external_id
    session.delete(link)
    session.commit()
    return {
        'removed_external_link_id': external_link_id,
        'removed_external_id': removed_external_id,
        'quote_case_id': quote_case_id,
        'workspace': get_quote_case_equipment_package_workspace(session, quote_case_id),
    }


def remove_heater_package_from_quote_case(session: Session, *, quote_case_id: int, external_link_id: int) -> dict[str, Any]:
    return remove_equipment_package_from_quote_case(session, quote_case_id=quote_case_id, external_link_id=external_link_id)

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
                'equipment_total': round(sum(_line_total(item) for item in package_preview['lines'] if str(item.get('category') or '') == 'equipment'), 2),
                'labor_total': round(sum(_line_total(item) for item in package_preview['lines'] if str(item.get('category') or '') == 'labor'), 2),
                'materials_total': round(sum(_line_total(item) for item in package_preview['lines'] if str(item.get('category') or '') not in {'equipment', 'labor'}), 2),
                'line_count': len(package_preview['lines']),
                'package_kind': 'heater',
                'edited': False,
            },
            'prepared_line': package_preview['lines'][0] if package_preview['lines'] else {},
            'prepared_lines': package_preview['lines'],
            'original_prepared_lines': package_preview['lines'],
            'original_package_summary': {
                'package_profile': package_preview['package_profile'],
                'labor_profile': package_preview['labor_profile'],
                'package_total': package_preview['package_total'],
                'currency_code': package_preview['currency_code'],
                'options': package_preview['options'],
                'equipment_total': round(sum(_line_total(item) for item in package_preview['lines'] if str(item.get('category') or '') == 'equipment'), 2),
                'labor_total': round(sum(_line_total(item) for item in package_preview['lines'] if str(item.get('category') or '') == 'labor'), 2),
                'materials_total': round(sum(_line_total(item) for item in package_preview['lines'] if str(item.get('category') or '') not in {'equipment', 'labor'}), 2),
                'line_count': len(package_preview['lines']),
                'package_kind': 'heater',
                'edited': False,
            },
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
        'package_workspace': get_quote_case_equipment_package_workspace(session, quote_case_id),
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
        'template_summary': get_equipment_package_template_summary(session),
        'settings': config,
    }
