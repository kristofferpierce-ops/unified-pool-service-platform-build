from app.services.estimate_reporting import build_commercial_estimate_context, render_estimate_html
from app.services.estimator import commercial_breakout_dict


def test_commercial_breakout_from_legacy_payload():
    legacy_output = {
        'chemical_costs': {
            'liquid_chlorine_12pct_gal': {'monthly_cost': 100.0, 'annual_cost': 1200.0},
            'muriatic_acid_gal': {'monthly_cost': 25.0, 'annual_cost': 300.0},
        },
        'service_costs': {'monthly_service_cost': 400.0, 'annual_service_cost': 4800.0},
        'monthly_real_cost': 525.0,
        'annual_real_cost': 6300.0,
    }
    breakout = commercial_breakout_dict(legacy_output, 35.0)
    assert breakout['monthly_chemical_real_cost'] == 125.0
    assert breakout['annual_chemical_real_cost'] == 1500.0
    assert breakout['monthly_service_real_cost'] == 400.0
    assert breakout['annual_service_real_cost'] == 4800.0
    assert breakout['monthly_service_sell_price'] > breakout['monthly_service_real_cost']


def test_render_estimate_html_contains_full_sections():
    context = build_commercial_estimate_context(
        property_record={'id': 1, 'name': 'Pier Pool', 'account_type': 'commercial', 'address_line_1': '123 Harbor', 'city': 'Key West', 'state': 'FL', 'postal_code': '33040', 'drive_minutes_round_trip': 18},
        vessel_record={'id': 2, 'name': 'Main Vessel', 'gallons': 20000, 'surface_type': 'plaster', 'covered': False, 'indoor': False, 'heated': True, 'service_frequency_per_month': 8, 'training_weeks_per_year': 4, 'minutes_on_site': 50},
        assets=[{'asset_type': 'Pump', 'manufacturer': 'Jandy', 'model_number': 'VSF', 'part_number': '123', 'reference_tag': 'P-1', 'notes': 'Primary pump'}],
        account_name='Harbor Resort',
        scenario_name='Summer quote',
        training_weeks=4,
        model_version_name='commercial-v1',
        estimate_input={'gallons': 20000, 'visits_per_month': 8, 'minutes_on_site': 50, 'drive_minutes_round_trip': 18, 'techs_on_visit': 1, 'bath_score': 6, 'debris_score': 4, 'filtration_score': 5, 'overflow_score': 4, 'backwash_score': 5, 'target_margin_pct': 35.0, 'global_adjustment_pct': 0.0},
        estimate_output={
            'service_costs': {'adjusted_site_minutes': 55, 'adjusted_drive_minutes': 18, 'hours_per_visit': 1.2, 'direct_labor_rate': 30, 'overhead_rate': 20, 'direct_labor_cost_per_visit': 36, 'overhead_cost_per_visit': 24},
            'chemical_quantities': {'liquid_chlorine_12pct_gal': {'monthly_quantity': 10, 'annual_quantity': 120}},
            'chemical_costs': {'liquid_chlorine_12pct_gal': {'monthly_cost': 90, 'annual_cost': 1080, 'monthly_sell_price': 138.46, 'annual_sell_price': 1661.52, 'unit_cost': 9, 'unit': 'gal'}},
            'monthly_real_cost': 570,
            'monthly_sell_price': 876.92,
            'annual_real_cost': 6840,
            'annual_sell_price': 10523.04,
            'visit_sell_price': 109.615,
            'monthly_chemical_real_cost': 90,
            'monthly_chemical_sell_price': 138.46,
            'annual_chemical_real_cost': 1080,
            'annual_chemical_sell_price': 1661.52,
            'monthly_service_real_cost': 480,
            'monthly_service_sell_price': 738.46,
            'annual_service_real_cost': 5760,
            'annual_service_sell_price': 8861.52,
        },
        separate_chemical_pricing=True,
        saved_run_id=77,
        saved_at='2026-03-18 20:00:00 UTC',
    )
    html = render_estimate_html(context, include_print_button=False)
    assert 'Commercial Estimate' in html
    assert 'TOTAL CHEMICALS' in html
    assert 'Separate pricing breakdown' in html
    assert 'Harbor Resort' in html
