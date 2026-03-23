from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session

from app.core.database import engine
from app.services.estimate_reporting import render_estimate_html, render_estimate_json
from app.services.estimator import EstimateInput, calculate_estimate
from app.services.estimate_workspace import compare_saved_runs, delete_saved_run, get_saved_estimate_bundle, list_saved_estimate_runs

router = APIRouter(prefix='/estimates', tags=['estimates'])


class EstimateRequest(BaseModel):
    property_id: int
    vessel_id: int | None = None
    model_family: str
    gallons: float
    visits_per_month: float
    minutes_on_site: float
    drive_minutes_round_trip: float
    techs_on_visit: int = 1
    bath_score: int = 5
    debris_score: int = 5
    filtration_score: int = 5
    overflow_score: int = 5
    backwash_score: int = 5
    target_margin_pct: float = 35.0
    global_adjustment_pct: float = 0.0


@router.post('/calculate')
def calculate(payload: EstimateRequest):
    with Session(engine) as session:
        result = calculate_estimate(session, EstimateInput(**payload.model_dump()))
        return asdict(result)


@router.get('/saved')
def saved_estimates(account_type: str | None = None, property_id: int | None = None, vessel_id: int | None = None, limit: int = 200):
    with Session(engine) as session:
        return list_saved_estimate_runs(session, account_type=account_type, property_id=property_id, vessel_id=vessel_id, limit=limit)


@router.get('/saved/{run_id}')
def saved_estimate_detail(run_id: int):
    with Session(engine) as session:
        bundle = get_saved_estimate_bundle(session, run_id)
        if not bundle:
            raise HTTPException(status_code=404, detail='Estimate run not found')
        return {'row': bundle['row'], 'input_snapshot': bundle['input_snapshot'], 'output_snapshot': bundle['output_snapshot'], 'context': bundle['context']}


@router.get('/saved/{run_id}/report')
def saved_estimate_report(run_id: int, format: str = Query(default='json')):
    with Session(engine) as session:
        bundle = get_saved_estimate_bundle(session, run_id)
        if not bundle or not bundle['context']:
            raise HTTPException(status_code=404, detail='Estimate report not found')
        fmt = format.lower().strip()
        if fmt == 'html':
            return {'format': 'html', 'content': render_estimate_html(bundle['context'], include_print_button=False)}
        return {'format': 'json', 'content': render_estimate_json(bundle['context'])}


@router.get('/compare')
def compare(run_ids: list[int] = Query(default=[])):
    if len(run_ids) < 2:
        raise HTTPException(status_code=400, detail='Provide at least two run_ids to compare')
    with Session(engine) as session:
        rows = compare_saved_runs(session, run_ids)
        if not rows:
            raise HTTPException(status_code=404, detail='No matching runs found')
        return rows


@router.delete('/saved/{run_id}')
def delete_saved_estimate(run_id: int):
    with Session(engine) as session:
        ok = delete_saved_run(session, run_id)
        if not ok:
            raise HTTPException(status_code=404, detail='Estimate run not found')
        return {'ok': True, 'deleted_run_id': run_id}
