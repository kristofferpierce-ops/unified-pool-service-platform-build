"""Locks the LSI water-balance chemistry engine."""
import math

from app.services.chemistry import (
    balance_recommendations,
    carbonate_alkalinity,
    check_ranges,
    classify_lsi,
    langelier_index,
    temperature_factor,
    water_balance_report,
)


def test_temperature_factor_table_and_interpolation():
    assert temperature_factor(84) == 0.7            # exact table point
    assert temperature_factor(32) == 0.0            # bottom clamp
    assert temperature_factor(105) == 0.9           # top clamp
    # 90F sits between 84 (0.7) and 94 (0.8): 0.7 + 6/10*0.1 = 0.76
    assert abs(temperature_factor(90) - 0.76) < 1e-6


def test_lsi_balanced_case():
    # pH 7.5, 84F (TF .7), CH 200 (log10=2.301, CF=1.901), TA 100 (AF=2.0), TDS<=1000.
    # 7.5 + 0.7 + 1.901 + 2.0 - 12.1 = 0.001 -> rounds to 0.0, balanced.
    lsi = langelier_index(ph=7.5, temp_f=84, calcium_hardness=200, total_alkalinity=100)
    assert lsi == 0.0
    assert classify_lsi(lsi) == 'balanced'


def test_lsi_corrosive_and_scaling():
    corrosive = langelier_index(ph=7.2, temp_f=60, calcium_hardness=150, total_alkalinity=80)
    assert corrosive < -0.3
    assert classify_lsi(corrosive) == 'corrosive'

    scaling = langelier_index(ph=8.0, temp_f=90, calcium_hardness=400, total_alkalinity=150)
    assert scaling > 0.3
    assert classify_lsi(scaling) == 'scaling'


def test_cya_correction_lowers_carbonate_alkalinity_and_lsi():
    plain = langelier_index(ph=7.5, temp_f=84, calcium_hardness=200, total_alkalinity=100)
    corrected = langelier_index(ph=7.5, temp_f=84, calcium_hardness=200, total_alkalinity=100, cyanuric_acid=80)
    # CYA correction removes carbonate alkalinity -> lower LSI.
    assert corrected < plain
    assert carbonate_alkalinity(100, 7.5, 80) < 100


def test_range_checks_flag_out_of_range():
    statuses = {s.parameter: s.status for s in check_ranges(
        {'ph': 7.9, 'total_alkalinity': 60, 'calcium_hardness': 300, 'cyanuric_acid': 40, 'free_chlorine': 3.0})}
    assert statuses['ph'] == 'high'
    assert statuses['total_alkalinity'] == 'low'
    assert statuses['calcium_hardness'] == 'ok'
    assert statuses['free_chlorine'] == 'ok'


def test_dosing_recommends_bicarb_for_low_alkalinity():
    # TA 60 in a 15,000 gal pool -> raise to mid (100), delta 40 ppm.
    # 1.5 lb/10k/10ppm * 1.5 (15k) * 4 (40ppm) = 9.0 lb sodium bicarbonate.
    recs = {r.parameter: r for r in balance_recommendations(
        {'ph': 7.5, 'total_alkalinity': 60, 'calcium_hardness': 300, 'cyanuric_acid': 40, 'free_chlorine': 3.0},
        gallons=15000)}
    assert 'total_alkalinity' in recs
    r = recs['total_alkalinity']
    assert r.product == 'Sodium Bicarbonate'
    assert r.action == 'add'
    assert math.isclose(r.amount, 9.0, abs_tol=0.01)


def test_full_report():
    report = water_balance_report(ph=7.2, temp_f=60, calcium_hardness=150,
                                  total_alkalinity=70, free_chlorine=1.0, gallons=15000)
    assert report.classification == 'corrosive'
    assert any(p.status != 'ok' for p in report.parameters)
    assert len(report.recommendations) >= 1
