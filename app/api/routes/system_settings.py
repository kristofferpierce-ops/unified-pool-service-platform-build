from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from app.core.database import engine
from app.services.system_settings import get_setting, set_setting

router = APIRouter(prefix='/system-settings', tags=['system-settings'])


class SettingBody(BaseModel):
    value: dict
    description: str = ''


@router.get('/{key}')
def read_setting(key: str):
    with Session(engine) as session:
        value = get_setting(session, key, None)
        if value is None:
            raise HTTPException(status_code=404, detail='Setting not found')
        return {'key': key, 'value': value}


@router.put('/{key}')
def write_setting(key: str, body: SettingBody):
    with Session(engine) as session:
        record = set_setting(session, key, body.value, body.description)
        return {'id': record.id, 'key': record.key, 'value': body.value}
