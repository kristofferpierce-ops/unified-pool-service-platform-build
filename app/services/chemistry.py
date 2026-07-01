"""Deterministic pool water-balance chemistry engine.

The Langelier Saturation Index (LSI) is the industry standard for whether pool
water is corrosive, balanced, or scaling. This computes it from a water test
(pH, temperature, calcium hardness, total alkalinity, TDS, and optional CYA
correction), classifies the result, checks each parameter against ideal ranges,
and recommends dosing to bring the water into balance.

Formula (Taylor/APSP factor method, expressed as continuous logs that reproduce
the standard factor tables):

    LSI = pH + TF + CF + AF - TDSF
      TF   = temperature factor (interpolated from the standard table)
      CF   = log10(calcium_hardness) - 0.4
      AF   = log10(carbonate_alkalinity)
      TDSF = 12.1 (TDS <= 1000) else 12.2 (salt/high-TDS)

Carbonate alkalinity subtracts the cyanurate contribution when CYA is supplied,
using the pH-dependent APSP factor.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

# Temperature (deg F) -> factor, standard Taylor table (interpolated between points).
_TEMP_TABLE = [(32, 0.0), (37, 0.1), (46, 0.2), (53, 0.3), (60, 0.4),
               (66, 0.5), (76, 0.6), (84, 0.7), (94, 0.8), (105, 0.9)]

# pH -> cyanurate alkalinity correction factor (APSP-11, interpolated).
_CYA_FACTOR = [(7.0, 0.15), (7.2, 0.22), (7.4, 0.30), (7.5, 0.33),
               (7.6, 0.36), (7.8, 0.44), (8.0, 0.51)]

IDEAL_RANGES = {
    'ph': (7.4, 7.6),
    'total_alkalinity': (80.0, 120.0),
    'calcium_hardness': (200.0, 400.0),
    'cyanuric_acid': (30.0, 50.0),
    'free_chlorine': (2.0, 4.0),
    'lsi': (-0.3, 0.3),
}

# Dosing rates per 10,000 gallons to raise a parameter by one "step".
# (product, amount, unit, step_amount, step_param_delta)
_RAISE_DOSING = {
    'total_alkalinity': ('Sodium Bicarbonate', 1.5, 'lb', 10.0),   # 1.5 lb -> +10 ppm TA
    'calcium_hardness': ('Calcium Chloride', 1.25, 'lb', 10.0),    # 1.25 lb -> +10 ppm CH
    'cyanuric_acid': ('Cyanuric Acid', 0.81, 'lb', 10.0),          # 13 oz -> +10 ppm CYA
    'free_chlorine': ('Liquid Chlorine 12%', 11.0, 'fl oz', 1.0),  # 11 fl oz -> +1 ppm FC
}


def _interp(table: list[tuple[float, float]], x: float) -> float:
    if x <= table[0][0]:
        return table[0][1]
    if x >= table[-1][0]:
        return table[-1][1]
    for (x0, y0), (x1, y1) in zip(table, table[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return table[-1][1]


def temperature_factor(temp_f: float) -> float:
    return round(_interp(_TEMP_TABLE, temp_f), 3)


def carbonate_alkalinity(total_alkalinity: float, ph: float, cyanuric_acid: float = 0.0) -> float:
    """Total alkalinity minus the cyanurate contribution (0 if no CYA)."""
    if cyanuric_acid <= 0:
        return total_alkalinity
    correction = cyanuric_acid * _interp(_CYA_FACTOR, ph)
    return max(1.0, total_alkalinity - correction)


def langelier_index(
    *,
    ph: float,
    temp_f: float,
    calcium_hardness: float,
    total_alkalinity: float,
    tds: float = 1000.0,
    cyanuric_acid: float = 0.0,
) -> float:
    """Langelier Saturation Index. Negative = corrosive, ~0 = balanced, positive = scaling."""
    ch = max(1.0, calcium_hardness)
    carb_alk = carbonate_alkalinity(total_alkalinity, ph, cyanuric_acid)
    tf = temperature_factor(temp_f)
    cf = math.log10(ch) - 0.4
    af = math.log10(carb_alk)
    tdsf = 12.1 if tds <= 1000 else 12.2
    return round(ph + tf + cf + af - tdsf, 2)


def classify_lsi(lsi: float) -> str:
    low, high = IDEAL_RANGES['lsi']
    if lsi < low:
        return 'corrosive'
    if lsi > high:
        return 'scaling'
    return 'balanced'


@dataclass
class ParameterStatus:
    parameter: str
    value: float
    low: float
    high: float
    status: str  # low | ok | high


@dataclass
class DoseRecommendation:
    parameter: str
    product: str
    action: str        # 'add' | 'reduce'
    amount: float      # 0 for qualitative (pH)
    unit: str
    detail: str


@dataclass
class WaterBalanceReport:
    lsi: float
    classification: str
    parameters: list = field(default_factory=list)      # list[ParameterStatus]
    recommendations: list = field(default_factory=list)  # list[DoseRecommendation]


def check_ranges(readings: dict) -> list[ParameterStatus]:
    out: list[ParameterStatus] = []
    for key, (low, high) in IDEAL_RANGES.items():
        if key == 'lsi' or key not in readings:
            continue
        value = readings[key]
        status = 'ok' if low <= value <= high else ('low' if value < low else 'high')
        out.append(ParameterStatus(parameter=key, value=value, low=low, high=high, status=status))
    return out


def _dose_amount(parameter: str, delta: float, gallons: float) -> tuple[str, float, str]:
    product, rate, unit, step = _RAISE_DOSING[parameter]
    amount = rate * (gallons / 10000.0) * (delta / step)
    return product, round(amount, 2), unit


def balance_recommendations(readings: dict, gallons: float) -> list[DoseRecommendation]:
    """Dosing to bring each out-of-range parameter to the middle of its ideal range.

    Amounts are approximate industry rates per 10,000 gallons; pH is handled
    qualitatively because it is buffered by alkalinity and needs incremental
    dosing with retesting.
    """
    recs: list[DoseRecommendation] = []
    for key, (low, high) in IDEAL_RANGES.items():
        if key == 'lsi' or key not in readings:
            continue
        value = readings[key]
        target = (low + high) / 2.0
        if low <= value <= high:
            continue

        if key == 'ph':
            if value < low:
                recs.append(DoseRecommendation('ph', 'Soda Ash', 'add', 0.0, '',
                                               'pH low: add soda ash gradually and retest (buffered by alkalinity).'))
            else:
                recs.append(DoseRecommendation('ph', 'Muriatic Acid', 'add', 0.0, '',
                                               'pH high: add muriatic acid gradually and retest.'))
            continue

        if value < low and key in _RAISE_DOSING:
            product, amount, unit = _dose_amount(key, target - value, gallons)
            recs.append(DoseRecommendation(key, product, 'add', amount, unit,
                                           f'{key.replace("_", " ")} low ({value:g}); add ~{amount:g} {unit} to reach ~{target:g}.'))
        elif value > high:
            if key == 'total_alkalinity':
                recs.append(DoseRecommendation(key, 'Muriatic Acid', 'add', 0.0, '',
                                               'Alkalinity high: lower with muriatic acid (also lowers pH — rebalance after).'))
            else:
                recs.append(DoseRecommendation(key, '(dilution)', 'reduce', 0.0, '',
                                               f'{key.replace("_", " ")} high ({value:g}); reduce by partial drain + refill.'))
    return recs


def water_balance_report(
    *,
    ph: float,
    temp_f: float,
    calcium_hardness: float,
    total_alkalinity: float,
    free_chlorine: float = 0.0,
    cyanuric_acid: float = 0.0,
    tds: float = 1000.0,
    gallons: float = 0.0,
) -> WaterBalanceReport:
    lsi = langelier_index(ph=ph, temp_f=temp_f, calcium_hardness=calcium_hardness,
                          total_alkalinity=total_alkalinity, tds=tds, cyanuric_acid=cyanuric_acid)
    readings = {
        'ph': ph, 'total_alkalinity': total_alkalinity, 'calcium_hardness': calcium_hardness,
        'cyanuric_acid': cyanuric_acid, 'free_chlorine': free_chlorine,
    }
    return WaterBalanceReport(
        lsi=lsi,
        classification=classify_lsi(lsi),
        parameters=check_ranges(readings),
        recommendations=balance_recommendations(readings, gallons) if gallons > 0 else [],
    )
