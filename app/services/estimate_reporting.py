from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
from html import escape
from io import BytesIO
from pathlib import Path
from textwrap import wrap
from typing import Any

from PIL import Image, ImageDraw, ImageFont


def _money(value: Any) -> str:
    try:
        return f"${float(value):,.2f}"
    except Exception:
        return "$0.00"


def _qty(value: Any) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value):,.2f}"
    except Exception:
        return str(value)


def _slug(text: str) -> str:
    cleaned = ''.join(ch.lower() if ch.isalnum() else '_' for ch in (text or 'estimate'))
    while '__' in cleaned:
        cleaned = cleaned.replace('__', '_')
    return cleaned.strip('_') or 'estimate'


def _ensure_dict(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    if is_dataclass(value):
        return asdict(value)
    return getattr(value, 'model_dump', lambda: dict(value))() if value is not None else {}


def build_commercial_estimate_context(
    *,
    property_record: Any,
    vessel_record: Any,
    assets: list[Any],
    account_name: str,
    scenario_name: str,
    training_weeks: int,
    model_version_name: str,
    estimate_input: Any,
    estimate_output: Any,
    separate_chemical_pricing: bool,
    saved_run_id: int | None = None,
    saved_at: str | None = None,
) -> dict:
    prop = _ensure_dict(property_record)
    vessel = _ensure_dict(vessel_record)
    input_data = _ensure_dict(estimate_input)
    output_data = _ensure_dict(estimate_output)
    service_costs = output_data.get('service_costs', {}) or {}
    chemical_quantities = output_data.get('chemical_quantities', {}) or {}
    chemical_costs = output_data.get('chemical_costs', {}) or {}
    margin_divisor = max(0.01, 1.0 - float(input_data.get('target_margin_pct', 0.0) or 0.0) / 100.0)

    chemicals = []
    for chemical_name, values in chemical_quantities.items():
        costs = chemical_costs.get(chemical_name, {}) or {}
        monthly_real = float(costs.get('monthly_cost', 0.0) or 0.0)
        annual_real = float(costs.get('annual_cost', 0.0) or 0.0)
        chemicals.append({
            'chemical': chemical_name,
            'annual_qty': float(values.get('annual_quantity', 0.0) or 0.0),
            'monthly_qty': float(values.get('monthly_quantity', 0.0) or 0.0),
            'monthly_real_cost': monthly_real,
            'monthly_sell_price': float(costs.get('monthly_sell_price', monthly_real / margin_divisor) or 0.0),
            'annual_real_cost': annual_real,
            'annual_sell_price': float(costs.get('annual_sell_price', annual_real / margin_divisor) or 0.0),
            'unit_cost': float(costs.get('unit_cost', 0.0) or 0.0),
            'unit': str(costs.get('unit', '') or ''),
        })

    context = {
        'report_title': 'Commercial Estimate',
        'generated_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
        'saved_run_id': saved_run_id,
        'saved_at': saved_at,
        'account_name': account_name or '',
        'scenario_name': scenario_name,
        'baseline_model_version': model_version_name,
        'separate_chemical_pricing': bool(separate_chemical_pricing),
        'property': {
            'id': prop.get('id'),
            'name': prop.get('name', ''),
            'account_type': prop.get('account_type', ''),
            'address_line_1': prop.get('address_line_1', ''),
            'city': prop.get('city', ''),
            'state': prop.get('state', ''),
            'postal_code': prop.get('postal_code', ''),
            'drive_minutes_round_trip': float(prop.get('drive_minutes_round_trip', 0.0) or 0.0),
        },
        'vessel': {
            'id': vessel.get('id'),
            'name': vessel.get('name', ''),
            'gallons': float(vessel.get('gallons', 0.0) or 0.0),
            'surface_type': vessel.get('surface_type', ''),
            'covered': bool(vessel.get('covered', False)),
            'indoor': bool(vessel.get('indoor', False)),
            'heated': bool(vessel.get('heated', False)),
            'service_frequency_per_month': float(vessel.get('service_frequency_per_month', 0.0) or 0.0),
            'training_weeks_per_year': int(vessel.get('training_weeks_per_year', 0) or 0),
            'minutes_on_site': float(vessel.get('minutes_on_site', 0.0) or 0.0),
        },
        'inputs': {
            'gallons': float(input_data.get('gallons', 0.0) or 0.0),
            'visits_per_month': float(input_data.get('visits_per_month', 0.0) or 0.0),
            'minutes_on_site': float(input_data.get('minutes_on_site', 0.0) or 0.0),
            'drive_minutes_round_trip': float(input_data.get('drive_minutes_round_trip', 0.0) or 0.0),
            'techs_on_visit': int(input_data.get('techs_on_visit', 1) or 1),
            'bath_score': int(input_data.get('bath_score', 0) or 0),
            'debris_score': int(input_data.get('debris_score', 0) or 0),
            'filtration_score': int(input_data.get('filtration_score', 0) or 0),
            'overflow_score': int(input_data.get('overflow_score', 0) or 0),
            'backwash_score': int(input_data.get('backwash_score', 0) or 0),
            'target_margin_pct': float(input_data.get('target_margin_pct', 0.0) or 0.0),
            'global_adjustment_pct': float(input_data.get('global_adjustment_pct', 0.0) or 0.0),
            'training_weeks': int(training_weeks or 0),
        },
        'totals': {
            'monthly_real_cost': float(output_data.get('monthly_real_cost', 0.0) or 0.0),
            'monthly_sell_price': float(output_data.get('monthly_sell_price', 0.0) or 0.0),
            'annual_real_cost': float(output_data.get('annual_real_cost', 0.0) or 0.0),
            'annual_sell_price': float(output_data.get('annual_sell_price', 0.0) or 0.0),
            'visit_sell_price': float(output_data.get('visit_sell_price', 0.0) or 0.0),
            'monthly_chemical_real_cost': float(output_data.get('monthly_chemical_real_cost', 0.0) or 0.0),
            'monthly_chemical_sell_price': float(output_data.get('monthly_chemical_sell_price', 0.0) or 0.0),
            'annual_chemical_real_cost': float(output_data.get('annual_chemical_real_cost', 0.0) or 0.0),
            'annual_chemical_sell_price': float(output_data.get('annual_chemical_sell_price', 0.0) or 0.0),
            'monthly_service_real_cost': float(output_data.get('monthly_service_real_cost', 0.0) or 0.0),
            'monthly_service_sell_price': float(output_data.get('monthly_service_sell_price', 0.0) or 0.0),
            'annual_service_real_cost': float(output_data.get('annual_service_real_cost', 0.0) or 0.0),
            'annual_service_sell_price': float(output_data.get('annual_service_sell_price', 0.0) or 0.0),
        },
        'service_details': {
            'adjusted_site_minutes': float(service_costs.get('adjusted_site_minutes', 0.0) or 0.0),
            'adjusted_drive_minutes': float(service_costs.get('adjusted_drive_minutes', 0.0) or 0.0),
            'hours_per_visit': float(service_costs.get('hours_per_visit', 0.0) or 0.0),
            'direct_labor_rate': float(service_costs.get('direct_labor_rate', 0.0) or 0.0),
            'overhead_rate': float(service_costs.get('overhead_rate', 0.0) or 0.0),
            'direct_labor_cost_per_visit': float(service_costs.get('direct_labor_cost_per_visit', 0.0) or 0.0),
            'overhead_cost_per_visit': float(service_costs.get('overhead_cost_per_visit', 0.0) or 0.0),
        },
        'chemicals': chemicals,
        'equipment_assets': [
            {
                'asset_type': getattr(asset, 'asset_type', '') if not isinstance(asset, dict) else asset.get('asset_type', ''),
                'manufacturer': getattr(asset, 'manufacturer', '') if not isinstance(asset, dict) else asset.get('manufacturer', ''),
                'model_number': getattr(asset, 'model_number', '') if not isinstance(asset, dict) else asset.get('model_number', ''),
                'part_number': getattr(asset, 'part_number', '') if not isinstance(asset, dict) else asset.get('part_number', ''),
                'reference_tag': getattr(asset, 'reference_tag', '') if not isinstance(asset, dict) else asset.get('reference_tag', ''),
                'notes': getattr(asset, 'notes', '') if not isinstance(asset, dict) else asset.get('notes', ''),
            }
            for asset in assets
        ],
    }
    context['file_name_base'] = _slug(
        f"{context['property']['name']}_{context['vessel']['name']}_{context['scenario_name']}"
    )
    return context


def render_estimate_html(context: dict, include_print_button: bool = True) -> str:
    prop = context['property']
    vessel = context['vessel']
    inputs = context['inputs']
    totals = context['totals']
    service = context['service_details']

    address = ', '.join(part for part in [prop.get('address_line_1', ''), prop.get('city', ''), prop.get('state', ''), prop.get('postal_code', '')] if part)

    def table_row(label: str, value: str) -> str:
        return f"<tr><th>{escape(label)}</th><td>{escape(value)}</td></tr>"

    chemical_rows = ''.join(
        f"<tr>"
        f"<td>{escape(row['chemical'])}</td>"
        f"<td>{escape(_qty(row['monthly_qty']))}</td>"
        f"<td>{escape(_qty(row['annual_qty']))}</td>"
        f"<td>{escape(_money(row['monthly_real_cost']))}</td>"
        f"<td>{escape(_money(row['monthly_sell_price']))}</td>"
        f"<td>{escape(_money(row['annual_real_cost']))}</td>"
        f"<td>{escape(_money(row['annual_sell_price']))}</td>"
        f"</tr>"
        for row in context['chemicals']
    )
    chemical_rows += (
        f"<tr class='total-row'>"
        f"<td>TOTAL CHEMICALS</td><td></td><td></td>"
        f"<td>{escape(_money(totals['monthly_chemical_real_cost']))}</td>"
        f"<td>{escape(_money(totals['monthly_chemical_sell_price']))}</td>"
        f"<td>{escape(_money(totals['annual_chemical_real_cost']))}</td>"
        f"<td>{escape(_money(totals['annual_chemical_sell_price']))}</td>"
        f"</tr>"
    )

    asset_rows = ''.join(
        f"<tr>"
        f"<td>{escape(asset['asset_type'])}</td>"
        f"<td>{escape(asset['manufacturer'])}</td>"
        f"<td>{escape(asset['model_number'])}</td>"
        f"<td>{escape(asset['part_number'])}</td>"
        f"<td>{escape(asset['reference_tag'])}</td>"
        f"<td>{escape(asset['notes'])}</td>"
        f"</tr>"
        for asset in context['equipment_assets']
    ) or "<tr><td colspan='6'>No equipment assets recorded for this vessel.</td></tr>"

    print_button = "<button class='no-print print-btn' onclick='window.print()'>Print estimate</button>" if include_print_button else ""
    saved_line = f"<p><strong>Saved estimate run:</strong> #{context['saved_run_id']}</p>" if context.get('saved_run_id') else ""

    separate_breakdown = ""
    if context.get('separate_chemical_pricing'):
        separate_breakdown = f"""
        <section>
            <h2>Separate pricing breakdown</h2>
            <table>
                <thead>
                    <tr>
                        <th>Line item</th>
                        <th>Monthly real cost</th>
                        <th>Monthly sell price</th>
                        <th>Annual real cost</th>
                        <th>Annual sell price</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Service</td>
                        <td>{escape(_money(totals['monthly_service_real_cost']))}</td>
                        <td>{escape(_money(totals['monthly_service_sell_price']))}</td>
                        <td>{escape(_money(totals['annual_service_real_cost']))}</td>
                        <td>{escape(_money(totals['annual_service_sell_price']))}</td>
                    </tr>
                    <tr>
                        <td>Chemicals</td>
                        <td>{escape(_money(totals['monthly_chemical_real_cost']))}</td>
                        <td>{escape(_money(totals['monthly_chemical_sell_price']))}</td>
                        <td>{escape(_money(totals['annual_chemical_real_cost']))}</td>
                        <td>{escape(_money(totals['annual_chemical_sell_price']))}</td>
                    </tr>
                    <tr class='total-row'>
                        <td>Combined total</td>
                        <td>{escape(_money(totals['monthly_real_cost']))}</td>
                        <td>{escape(_money(totals['monthly_sell_price']))}</td>
                        <td>{escape(_money(totals['annual_real_cost']))}</td>
                        <td>{escape(_money(totals['annual_sell_price']))}</td>
                    </tr>
                </tbody>
            </table>
        </section>
        """

    return f"""
    <!doctype html>
    <html>
    <head>
        <meta charset='utf-8'>
        <title>{escape(context['report_title'])}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 24px; color: #222; }}
            h1, h2, h3 {{ margin-bottom: 8px; }}
            h1 {{ border-bottom: 2px solid #222; padding-bottom: 8px; }}
            .meta {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
            table {{ width: 100%; border-collapse: collapse; margin: 10px 0 22px; }}
            th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; vertical-align: top; }}
            th {{ background: #f3f3f3; width: 30%; }}
            .metric-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 16px 0; }}
            .metric {{ border: 1px solid #ddd; padding: 12px; border-radius: 8px; background: #fafafa; }}
            .metric .label {{ font-size: 12px; color: #666; }}
            .metric .value {{ font-size: 20px; font-weight: 700; margin-top: 4px; }}
            .print-btn {{ padding: 10px 16px; border: 0; background: #0e7490; color: white; border-radius: 8px; cursor: pointer; margin-bottom: 16px; }}
            .total-row {{ font-weight: 700; background: #f8fafc; }}
            .small {{ color: #666; font-size: 12px; }}
            @media print {{
                .no-print {{ display: none !important; }}
                body {{ margin: 0.35in; }}
            }}
        </style>
    </head>
    <body>
        {print_button}
        <h1>{escape(context['report_title'])}</h1>
        <p><strong>Generated:</strong> {escape(context['generated_at'])}</p>
        {saved_line}
        <p><strong>Scenario:</strong> {escape(context['scenario_name'])}</p>
        <p><strong>Baseline model:</strong> {escape(context['baseline_model_version'])}</p>

        <div class='meta'>
            <section>
                <h2>Account and property</h2>
                <table>
                    {table_row('Account', context.get('account_name', ''))}
                    {table_row('Property', prop.get('name', ''))}
                    {table_row('Address', address)}
                    {table_row('Account type', prop.get('account_type', ''))}
                    {table_row('Drive minutes round trip', _qty(prop.get('drive_minutes_round_trip')))}
                </table>
            </section>
            <section>
                <h2>Vessel</h2>
                <table>
                    {table_row('Vessel', vessel.get('name', ''))}
                    {table_row('Gallons', _qty(vessel.get('gallons')))}
                    {table_row('Surface', vessel.get('surface_type', ''))}
                    {table_row('Covered', 'Yes' if vessel.get('covered') else 'No')}
                    {table_row('Indoor', 'Yes' if vessel.get('indoor') else 'No')}
                    {table_row('Heated', 'Yes' if vessel.get('heated') else 'No')}
                    {table_row('Service frequency per month', _qty(vessel.get('service_frequency_per_month')))}
                </table>
            </section>
        </div>

        <section>
            <h2>Inputs and operating assumptions</h2>
            <table>
                {table_row('Gallons used for estimate', _qty(inputs['gallons']))}
                {table_row('Visits per month', _qty(inputs['visits_per_month']))}
                {table_row('Minutes on site', _qty(inputs['minutes_on_site']))}
                {table_row('Drive minutes round trip', _qty(inputs['drive_minutes_round_trip']))}
                {table_row('Techs on visit', str(inputs['techs_on_visit']))}
                {table_row('Training or peak weeks per year', str(inputs['training_weeks']))}
                {table_row('Target margin percent', _qty(inputs['target_margin_pct']))}
                {table_row('Global adjustment percent', _qty(inputs['global_adjustment_pct']))}
                {table_row('Bath score', str(inputs['bath_score']))}
                {table_row('Debris score', str(inputs['debris_score']))}
                {table_row('Filtration score', str(inputs['filtration_score']))}
                {table_row('Overflow score', str(inputs['overflow_score']))}
                {table_row('Backwash score', str(inputs['backwash_score']))}
            </table>
        </section>

        <section>
            <h2>Combined totals</h2>
            <div class='metric-grid'>
                <div class='metric'><div class='label'>Monthly real cost</div><div class='value'>{escape(_money(totals['monthly_real_cost']))}</div></div>
                <div class='metric'><div class='label'>Monthly sell price</div><div class='value'>{escape(_money(totals['monthly_sell_price']))}</div></div>
                <div class='metric'><div class='label'>Annual real cost</div><div class='value'>{escape(_money(totals['annual_real_cost']))}</div></div>
                <div class='metric'><div class='label'>Annual sell price</div><div class='value'>{escape(_money(totals['annual_sell_price']))}</div></div>
            </div>
            <p><strong>Per visit sell price:</strong> {escape(_money(totals['visit_sell_price']))}</p>
        </section>

        {separate_breakdown}

        <section>
            <h2>Service cost detail</h2>
            <table>
                {table_row('Adjusted site minutes', _qty(service['adjusted_site_minutes']))}
                {table_row('Adjusted drive minutes', _qty(service['adjusted_drive_minutes']))}
                {table_row('Hours per visit', _qty(service['hours_per_visit']))}
                {table_row('Direct labor rate', _money(service['direct_labor_rate']))}
                {table_row('Overhead rate', _money(service['overhead_rate']))}
                {table_row('Direct labor cost per visit', _money(service['direct_labor_cost_per_visit']))}
                {table_row('Overhead cost per visit', _money(service['overhead_cost_per_visit']))}
                {table_row('Monthly service real cost', _money(totals['monthly_service_real_cost']))}
                {table_row('Monthly service sell price', _money(totals['monthly_service_sell_price']))}
                {table_row('Annual service real cost', _money(totals['annual_service_real_cost']))}
                {table_row('Annual service sell price', _money(totals['annual_service_sell_price']))}
            </table>
        </section>

        <section>
            <h2>Chemical cost schedule</h2>
            <table>
                <thead>
                    <tr>
                        <th>Chemical</th>
                        <th>Monthly qty</th>
                        <th>Annual qty</th>
                        <th>Monthly real cost</th>
                        <th>Monthly sell price</th>
                        <th>Annual real cost</th>
                        <th>Annual sell price</th>
                    </tr>
                </thead>
                <tbody>
                    {chemical_rows}
                </tbody>
            </table>
        </section>

        <section>
            <h2>Equipment assets</h2>
            <table>
                <thead>
                    <tr>
                        <th>Type</th>
                        <th>Manufacturer</th>
                        <th>Model</th>
                        <th>Part number</th>
                        <th>Reference tag</th>
                        <th>Notes</th>
                    </tr>
                </thead>
                <tbody>
                    {asset_rows}
                </tbody>
            </table>
        </section>

        <p class='small'>This estimate report includes the selected property, vessel, estimate inputs, service costing detail, chemical schedule, equipment list, and combined pricing totals.</p>
    </body>
    </html>
    """


def render_estimate_json(context: dict) -> bytes:
    return json_dumps(context).encode('utf-8')


def json_dumps(value: Any) -> str:
    import json
    return json.dumps(value, indent=2, sort_keys=True, default=str)


def _load_font(size: int = 20):
    candidates = [
        'C:/Windows/Fonts/consola.ttf',
        'C:/Windows/Fonts/arial.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        str(Path.home() / '.fonts' / 'DejaVuSansMono.ttf'),
    ]
    for path in candidates:
        try:
            if Path(path).exists():
                return ImageFont.truetype(path, size=size)
        except Exception:
            continue
    return ImageFont.load_default()


def _report_lines(context: dict) -> list[str]:
    prop = context['property']
    vessel = context['vessel']
    inputs = context['inputs']
    totals = context['totals']
    service = context['service_details']
    address = ', '.join(part for part in [prop.get('address_line_1', ''), prop.get('city', ''), prop.get('state', ''), prop.get('postal_code', '')] if part)

    lines = [
        context['report_title'],
        f"Generated: {context['generated_at']}",
        f"Scenario: {context['scenario_name']}",
        f"Baseline model: {context['baseline_model_version']}",
    ]
    if context.get('saved_run_id'):
        lines.append(f"Saved estimate run: #{context['saved_run_id']}")
    lines += [
        '',
        'ACCOUNT AND PROPERTY',
        f"Account: {context.get('account_name', '')}",
        f"Property: {prop.get('name', '')}",
        f"Address: {address}",
        f"Account type: {prop.get('account_type', '')}",
        f"Drive minutes round trip: {_qty(prop.get('drive_minutes_round_trip'))}",
        '',
        'VESSEL',
        f"Vessel: {vessel.get('name', '')}",
        f"Gallons: {_qty(vessel.get('gallons'))}",
        f"Surface: {vessel.get('surface_type', '')}",
        f"Covered: {'Yes' if vessel.get('covered') else 'No'}",
        f"Indoor: {'Yes' if vessel.get('indoor') else 'No'}",
        f"Heated: {'Yes' if vessel.get('heated') else 'No'}",
        f"Service frequency per month: {_qty(vessel.get('service_frequency_per_month'))}",
        '',
        'INPUTS AND OPERATING ASSUMPTIONS',
        f"Gallons used for estimate: {_qty(inputs['gallons'])}",
        f"Visits per month: {_qty(inputs['visits_per_month'])}",
        f"Minutes on site: {_qty(inputs['minutes_on_site'])}",
        f"Drive minutes round trip: {_qty(inputs['drive_minutes_round_trip'])}",
        f"Techs on visit: {inputs['techs_on_visit']}",
        f"Training or peak weeks per year: {inputs['training_weeks']}",
        f"Target margin percent: {_qty(inputs['target_margin_pct'])}",
        f"Global adjustment percent: {_qty(inputs['global_adjustment_pct'])}",
        f"Bath score: {inputs['bath_score']}",
        f"Debris score: {inputs['debris_score']}",
        f"Filtration score: {inputs['filtration_score']}",
        f"Overflow score: {inputs['overflow_score']}",
        f"Backwash score: {inputs['backwash_score']}",
        '',
        'COMBINED TOTALS',
        f"Monthly real cost: {_money(totals['monthly_real_cost'])}",
        f"Monthly sell price: {_money(totals['monthly_sell_price'])}",
        f"Annual real cost: {_money(totals['annual_real_cost'])}",
        f"Annual sell price: {_money(totals['annual_sell_price'])}",
        f"Per visit sell price: {_money(totals['visit_sell_price'])}",
        '',
        'SEPARATE PRICING BREAKDOWN',
        f"Service monthly real cost: {_money(totals['monthly_service_real_cost'])}",
        f"Service monthly sell price: {_money(totals['monthly_service_sell_price'])}",
        f"Service annual real cost: {_money(totals['annual_service_real_cost'])}",
        f"Service annual sell price: {_money(totals['annual_service_sell_price'])}",
        f"Chemicals monthly real cost: {_money(totals['monthly_chemical_real_cost'])}",
        f"Chemicals monthly sell price: {_money(totals['monthly_chemical_sell_price'])}",
        f"Chemicals annual real cost: {_money(totals['annual_chemical_real_cost'])}",
        f"Chemicals annual sell price: {_money(totals['annual_chemical_sell_price'])}",
        '',
        'SERVICE COST DETAIL',
        f"Adjusted site minutes: {_qty(service['adjusted_site_minutes'])}",
        f"Adjusted drive minutes: {_qty(service['adjusted_drive_minutes'])}",
        f"Hours per visit: {_qty(service['hours_per_visit'])}",
        f"Direct labor rate: {_money(service['direct_labor_rate'])}",
        f"Overhead rate: {_money(service['overhead_rate'])}",
        f"Direct labor cost per visit: {_money(service['direct_labor_cost_per_visit'])}",
        f"Overhead cost per visit: {_money(service['overhead_cost_per_visit'])}",
        '',
        'CHEMICAL COST SCHEDULE',
    ]
    for row in context['chemicals']:
        lines.append(
            f"{row['chemical']}: monthly qty {_qty(row['monthly_qty'])}, annual qty {_qty(row['annual_qty'])}, "
            f"monthly real {_money(row['monthly_real_cost'])}, monthly sell {_money(row['monthly_sell_price'])}, "
            f"annual real {_money(row['annual_real_cost'])}, annual sell {_money(row['annual_sell_price'])}"
        )
    lines += [
        f"TOTAL CHEMICALS monthly real: {_money(totals['monthly_chemical_real_cost'])}",
        f"TOTAL CHEMICALS monthly sell: {_money(totals['monthly_chemical_sell_price'])}",
        f"TOTAL CHEMICALS annual real: {_money(totals['annual_chemical_real_cost'])}",
        f"TOTAL CHEMICALS annual sell: {_money(totals['annual_chemical_sell_price'])}",
        '',
        'EQUIPMENT ASSETS',
    ]
    if context['equipment_assets']:
        for asset in context['equipment_assets']:
            lines.append(
                f"{asset['asset_type']} | {asset['manufacturer']} | {asset['model_number']} | {asset['part_number']} | {asset['reference_tag']} | {asset['notes']}"
            )
    else:
        lines.append('No equipment assets recorded for this vessel.')
    return lines


def render_estimate_pdf(context: dict) -> bytes:
    width, height = 1654, 2339
    margin_x = 90
    margin_y = 90
    font = _load_font(20)
    line_height = 28
    max_chars = 115

    wrapped_lines: list[str] = []
    for line in _report_lines(context):
        parts = wrap(line, width=max_chars) or ['']
        wrapped_lines.extend(parts)

    pages: list[Image.Image] = []
    current = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(current)
    y = margin_y

    for line in wrapped_lines:
        if y > height - margin_y - line_height:
            pages.append(current)
            current = Image.new('RGB', (width, height), 'white')
            draw = ImageDraw.Draw(current)
            y = margin_y
        draw.text((margin_x, y), line, fill='black', font=font)
        y += line_height

    pages.append(current)
    buffer = BytesIO()
    pages[0].save(buffer, format='PDF', resolution=150.0, save_all=True, append_images=pages[1:])
    return buffer.getvalue()
