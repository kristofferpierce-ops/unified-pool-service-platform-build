from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.core.database import engine
from app.services.heater_quote import (
    apply_equipment_package_template_to_quote_case,
    attach_heater_candidate_to_quote_case,
    build_heater_package_preview,
    create_heater_quote_run,
    delete_equipment_package_template,
    delete_heater_quote_run,
    get_equipment_package_template_summary,
    get_heater_quote_dashboard_summary,
    get_heater_quote_settings,
    get_quote_case_heater_package_workspace,
    list_equipment_package_templates,
    list_heater_quote_runs,
    reset_heater_package_lines,
    save_heater_package_template,
    serialize_heater_quote_run,
    update_heater_package_lines,
)

router = APIRouter(prefix='/heater-quotes', tags=['heater-quotes'])


class HeaterQuoteCreateBody(BaseModel):
    title: str = ''
    quote_case_id: int | None = None
    direct_gallons: float | None = None
    shape: str = 'direct'
    length_ft: float = 0.0
    width_ft: float = 0.0
    avg_depth_ft: float = 0.0
    diameter_ft: float = 0.0
    current_water_temp_f: float = 78.0
    target_water_temp_f: float = 84.0
    ambient_air_temp_f: float = 80.0
    desired_heatup_hours: float = 24.0
    wind_mph: float = 0.0
    covered: bool = False
    heater_kind_preference: str = 'auto'
    fuel_preference: str = 'auto'
    unit_count: int = Field(default=1, ge=1, le=12)


class HeaterQuoteAttachBody(BaseModel):
    quote_case_id: int
    candidate_id: int
    attached_by: str = 'operator'
    package_profile: str = 'auto'
    labor_profile: str = 'standard'
    include_bypass_kit: bool | None = None
    include_pad_kit: bool | None = None
    include_gas_allowance: bool | None = None
    include_electrical_allowance: bool | None = None
    include_automation_integration: bool | None = None
    include_startup_visit: bool | None = None
    misc_materials_amount: float = 0.0
    labor_rate_override: float | None = None


class HeaterQuotePackagePreviewBody(BaseModel):
    candidate_id: int
    package_profile: str = 'auto'
    labor_profile: str = 'standard'
    include_bypass_kit: bool | None = None
    include_pad_kit: bool | None = None
    include_gas_allowance: bool | None = None
    include_electrical_allowance: bool | None = None
    include_automation_integration: bool | None = None
    include_startup_visit: bool | None = None
    misc_materials_amount: float = 0.0
    labor_rate_override: float | None = None


class HeaterPackageLineBody(BaseModel):
    name: str
    description: str = ''
    qty: float = Field(default=1.0, gt=0)
    amount: float = 0.0
    category: str = 'misc_materials'


class HeaterPackageUpdateBody(BaseModel):
    lines: list[HeaterPackageLineBody]
    edited_by: str = 'operator'


class HeaterPackageResetBody(BaseModel):
    edited_by: str = 'operator'



class SaveEquipmentPackageTemplateBody(BaseModel):
    quote_case_id: int
    external_link_id: int
    template_name: str
    saved_by: str = 'operator'


class ApplyEquipmentPackageTemplateBody(BaseModel):
    quote_case_id: int
    attached_by: str = 'operator'
    replace_existing: bool = False


@router.get('/config')
def heater_quote_config():
    with Session(engine) as session:
        settings = get_heater_quote_settings(session)
        dashboard = get_heater_quote_dashboard_summary(session)
        return {
            'settings': settings,
            'heritage_connection': dashboard['heritage_connection'],
        }


@router.get('/dashboard')
def heater_quote_dashboard():
    with Session(engine) as session:
        return get_heater_quote_dashboard_summary(session)


@router.get('/runs')
def heater_quote_runs(limit: int = 50):
    with Session(engine) as session:
        return list_heater_quote_runs(session, limit=limit)


@router.get('/runs/{run_id}')
def heater_quote_run_detail(run_id: int):
    with Session(engine) as session:
        try:
            return serialize_heater_quote_run(session, run_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post('/runs')
def create_heater_quote(body: HeaterQuoteCreateBody):
    with Session(engine) as session:
        try:
            return create_heater_quote_run(
                session,
                title=body.title,
                quote_case_id=body.quote_case_id,
                direct_gallons=body.direct_gallons,
                shape=body.shape,
                length_ft=body.length_ft,
                width_ft=body.width_ft,
                avg_depth_ft=body.avg_depth_ft,
                diameter_ft=body.diameter_ft,
                current_water_temp_f=body.current_water_temp_f,
                target_water_temp_f=body.target_water_temp_f,
                ambient_air_temp_f=body.ambient_air_temp_f,
                desired_heatup_hours=body.desired_heatup_hours,
                wind_mph=body.wind_mph,
                covered=body.covered,
                heater_kind_preference=body.heater_kind_preference,
                fuel_preference=body.fuel_preference,
                unit_count=body.unit_count,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/runs/{run_id}/package-preview')
def heater_quote_package_preview(run_id: int, body: HeaterQuotePackagePreviewBody):
    with Session(engine) as session:
        try:
            return build_heater_package_preview(
                session,
                run_id=run_id,
                candidate_id=body.candidate_id,
                package_profile=body.package_profile,
                labor_profile=body.labor_profile,
                include_bypass_kit=body.include_bypass_kit,
                include_pad_kit=body.include_pad_kit,
                include_gas_allowance=body.include_gas_allowance,
                include_electrical_allowance=body.include_electrical_allowance,
                include_automation_integration=body.include_automation_integration,
                include_startup_visit=body.include_startup_visit,
                misc_materials_amount=body.misc_materials_amount,
                labor_rate_override=body.labor_rate_override,
            )
        except ValueError as exc:
            message = str(exc).lower()
            status_code = 404 if 'not found' in message else 400
            raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.post('/runs/{run_id}/attach')
def attach_heater_quote(run_id: int, body: HeaterQuoteAttachBody):
    with Session(engine) as session:
        try:
            return attach_heater_candidate_to_quote_case(
                session,
                run_id=run_id,
                candidate_id=body.candidate_id,
                quote_case_id=body.quote_case_id,
                attached_by=body.attached_by,
                package_profile=body.package_profile,
                labor_profile=body.labor_profile,
                include_bypass_kit=body.include_bypass_kit,
                include_pad_kit=body.include_pad_kit,
                include_gas_allowance=body.include_gas_allowance,
                include_electrical_allowance=body.include_electrical_allowance,
                include_automation_integration=body.include_automation_integration,
                include_startup_visit=body.include_startup_visit,
                misc_materials_amount=body.misc_materials_amount,
                labor_rate_override=body.labor_rate_override,
            )
        except ValueError as exc:
            message = str(exc).lower()
            status_code = 404 if 'not found' in message else 400
            raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.get('/workspace/{quote_case_id}')
def heater_quote_workspace(quote_case_id: int):
    with Session(engine) as session:
        return get_quote_case_heater_package_workspace(session, quote_case_id)


@router.post('/workspace/{quote_case_id}/packages/{external_link_id}')
def update_heater_workspace_package(quote_case_id: int, external_link_id: int, body: HeaterPackageUpdateBody):
    with Session(engine) as session:
        try:
            return update_heater_package_lines(
                session,
                quote_case_id=quote_case_id,
                external_link_id=external_link_id,
                edited_lines=[item.model_dump() for item in body.lines],
                edited_by=body.edited_by,
            )
        except ValueError as exc:
            message = str(exc).lower()
            status_code = 404 if 'not found' in message else 400
            raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.post('/workspace/{quote_case_id}/packages/{external_link_id}/reset')
def reset_heater_workspace_package(quote_case_id: int, external_link_id: int, body: HeaterPackageResetBody | None = None):
    with Session(engine) as session:
        try:
            return reset_heater_package_lines(
                session,
                quote_case_id=quote_case_id,
                external_link_id=external_link_id,
            )
        except ValueError as exc:
            message = str(exc).lower()
            status_code = 404 if 'not found' in message else 400
            raise HTTPException(status_code=status_code, detail=str(exc)) from exc




@router.get('/templates')
def heater_quote_templates(package_kind: str | None = None):
    with Session(engine) as session:
        return {
            'templates': list_equipment_package_templates(session, package_kind=package_kind),
            'summary': get_equipment_package_template_summary(session),
        }


@router.post('/templates/save')
def save_equipment_package_template(body: SaveEquipmentPackageTemplateBody):
    with Session(engine) as session:
        try:
            return save_heater_package_template(
                session,
                quote_case_id=body.quote_case_id,
                external_link_id=body.external_link_id,
                template_name=body.template_name,
                saved_by=body.saved_by,
            )
        except ValueError as exc:
            message = str(exc).lower()
            status_code = 404 if 'not found' in message else 400
            raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.post('/templates/{template_slug}/apply')
def apply_equipment_package_template(template_slug: str, body: ApplyEquipmentPackageTemplateBody):
    with Session(engine) as session:
        try:
            return apply_equipment_package_template_to_quote_case(
                session,
                template_slug=template_slug,
                quote_case_id=body.quote_case_id,
                attached_by=body.attached_by,
                replace_existing=body.replace_existing,
            )
        except ValueError as exc:
            message = str(exc).lower()
            status_code = 404 if 'not found' in message else 400
            raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.delete('/templates/{template_slug}')
def delete_equipment_package_template_route(template_slug: str):
    with Session(engine) as session:
        try:
            return delete_equipment_package_template(session, template_slug)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

@router.delete('/runs/{run_id}')
def delete_heater_quote(run_id: int):
    with Session(engine) as session:
        try:
            return delete_heater_quote_run(session, run_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
