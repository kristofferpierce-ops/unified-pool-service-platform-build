from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from sqlmodel import Session, select

from app.models.tables import Account, BaselineModelVersion, EquipmentAsset, EstimateRun, EstimateScenario, PoolVessel, Property
from app.services.estimate_reporting import build_commercial_estimate_context
from app.services.estimator import EstimateInput, commercial_breakout_dict
from app.utils.serialization import loads


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if is_dataclass(value):
        return asdict(value)
    model_dump = getattr(value, 'model_dump', None)
    if callable(model_dump):
        return model_dump()
    raise TypeError('Unsupported estimate payload')


def _collect_maps(session: Session) -> tuple[dict[int, EstimateScenario], dict[int, Property], dict[int, PoolVessel], dict[int, Account]]:
    scenarios = {row.id: row for row in session.exec(select(EstimateScenario)).all() if row.id is not None}
    properties = {row.id: row for row in session.exec(select(Property)).all() if row.id is not None}
    vessels = {row.id: row for row in session.exec(select(PoolVessel)).all() if row.id is not None}
    accounts = {row.id: row for row in session.exec(select(Account)).all() if row.id is not None}
    return scenarios, properties, vessels, accounts


def _run_row(run: EstimateRun, scenario: EstimateScenario | None, prop: Property | None, vessel: PoolVessel | None, account: Account | None) -> dict[str, Any]:
    input_snapshot = loads(run.input_snapshot_json, {})
    output_snapshot = loads(run.output_snapshot_json, {})
    target_margin = float(input_snapshot.get('target_margin_pct', scenario.target_margin_pct if scenario else 35.0) or 35.0)
    output_snapshot.update(commercial_breakout_dict(output_snapshot, target_margin))
    return {
        'run_id': run.id,
        'scenario_id': run.scenario_id,
        'saved_at': run.run_timestamp.isoformat(),
        'scenario_name': scenario.scenario_name if scenario else '',
        'account_id': account.id if account else None,
        'account_name': account.name if account else '',
        'account_type': account.account_type if account else (prop.account_type if prop else ''),
        'property_id': prop.id if prop else run.property_id,
        'property_name': prop.name if prop else '',
        'property_address': prop.address_line_1 if prop else '',
        'vessel_id': vessel.id if vessel else run.vessel_id,
        'vessel_name': vessel.name if vessel else '',
        'target_margin_pct': target_margin,
        'monthly_sell_price': float(output_snapshot.get('monthly_sell_price', run.monthly_sell_price or 0.0) or 0.0),
        'annual_sell_price': float(output_snapshot.get('annual_sell_price', 0.0) or 0.0),
        'monthly_real_cost': float(output_snapshot.get('monthly_real_cost', run.monthly_real_cost or 0.0) or 0.0),
        'annual_real_cost': float(output_snapshot.get('annual_real_cost', run.annual_real_cost or 0.0) or 0.0),
        'monthly_chemical_sell_price': float(output_snapshot.get('monthly_chemical_sell_price', 0.0) or 0.0),
        'monthly_service_sell_price': float(output_snapshot.get('monthly_service_sell_price', 0.0) or 0.0),
        'input_snapshot': input_snapshot,
        'output_snapshot': output_snapshot,
    }


def list_saved_estimate_runs(session: Session, *, account_type: str | None = None, property_id: int | None = None, vessel_id: int | None = None, limit: int = 250) -> list[dict[str, Any]]:
    scenarios, properties, vessels, accounts = _collect_maps(session)
    runs = list(session.exec(select(EstimateRun).order_by(EstimateRun.run_timestamp.desc())).all())
    rows: list[dict[str, Any]] = []
    for run in runs:
        prop = properties.get(run.property_id)
        vessel = vessels.get(run.vessel_id) if run.vessel_id else None
        account = accounts.get(prop.account_id) if prop else None
        scenario = scenarios.get(run.scenario_id)
        if property_id and run.property_id != property_id:
            continue
        if vessel_id and run.vessel_id != vessel_id:
            continue
        inferred_account_type = account.account_type if account else (prop.account_type if prop else '')
        if account_type and inferred_account_type != account_type:
            continue
        rows.append(_run_row(run, scenario, prop, vessel, account))
        if len(rows) >= limit:
            break
    return rows


def get_saved_estimate_bundle(session: Session, run_id: int) -> dict[str, Any] | None:
    run = session.get(EstimateRun, run_id)
    if not run:
        return None
    scenario = session.get(EstimateScenario, run.scenario_id)
    prop = session.get(Property, run.property_id)
    vessel = session.get(PoolVessel, run.vessel_id) if run.vessel_id else None
    account = session.get(Account, prop.account_id) if prop else None
    assets = list(session.exec(select(EquipmentAsset).where(EquipmentAsset.vessel_id == vessel.id)).all()) if vessel else []
    model_version = session.get(BaselineModelVersion, scenario.baseline_model_version_id) if scenario else None

    input_snapshot = loads(run.input_snapshot_json, {})
    output_snapshot = loads(run.output_snapshot_json, {})
    target_margin = float(input_snapshot.get('target_margin_pct', scenario.target_margin_pct if scenario else 35.0) or 35.0)
    output_snapshot.update(commercial_breakout_dict(output_snapshot, target_margin))

    context = None
    if prop and vessel:
        context = build_commercial_estimate_context(
            property_record=prop,
            vessel_record=vessel,
            assets=assets,
            account_name=account.name if account else '',
            scenario_name=scenario.scenario_name if scenario else f'Saved run {run.id}',
            training_weeks=int(input_snapshot.get('training_weeks', vessel.training_weeks_per_year if vessel else 0) or 0),
            model_version_name=model_version.version_name if model_version else '',
            estimate_input=input_snapshot,
            estimate_output=output_snapshot,
            separate_chemical_pricing=bool(output_snapshot.get('monthly_chemical_sell_price')),
            saved_run_id=run.id,
            saved_at=run.run_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC'),
        )

    return {
        'run': run,
        'scenario': scenario,
        'property': prop,
        'vessel': vessel,
        'account': account,
        'assets': assets,
        'model_version': model_version,
        'input_snapshot': input_snapshot,
        'output_snapshot': output_snapshot,
        'context': context,
        'row': _run_row(run, scenario, prop, vessel, account),
    }


def compare_saved_runs(session: Session, run_ids: list[int]) -> list[dict[str, Any]]:
    bundles = [get_saved_estimate_bundle(session, run_id) for run_id in run_ids]
    return [bundle['row'] for bundle in bundles if bundle]


def delete_saved_run(session: Session, run_id: int) -> bool:
    run = session.get(EstimateRun, run_id)
    if not run:
        return False
    scenario_id = run.scenario_id
    session.delete(run)
    session.commit()
    remaining = list(session.exec(select(EstimateRun).where(EstimateRun.scenario_id == scenario_id)).all())
    if not remaining:
        scenario = session.get(EstimateScenario, scenario_id)
        if scenario:
            session.delete(scenario)
            session.commit()
    return True


def clone_estimate_input(session: Session, run_id: int) -> dict[str, Any] | None:
    bundle = get_saved_estimate_bundle(session, run_id)
    if not bundle:
        return None
    input_snapshot = dict(bundle['input_snapshot'])
    if bundle['property']:
        input_snapshot['property_id'] = bundle['property'].id
    if bundle['vessel']:
        input_snapshot['vessel_id'] = bundle['vessel'].id
    return input_snapshot


def estimate_input_from_snapshot(snapshot: dict[str, Any]) -> EstimateInput:
    return EstimateInput(**snapshot)
