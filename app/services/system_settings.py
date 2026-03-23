from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlmodel import Session, select

from app.models.system_tables import SystemSetting
from app.utils.serialization import dumps, loads


def get_setting(session: Session, key: str, default: Any = None) -> Any:
    record = session.exec(select(SystemSetting).where(SystemSetting.key == key)).first()
    if not record:
        return default
    return loads(record.value_json, default)


def set_setting(session: Session, key: str, value: Any, description: str = '') -> SystemSetting:
    record = session.exec(select(SystemSetting).where(SystemSetting.key == key)).first()
    if not record:
        record = SystemSetting(key=key, description=description)
        session.add(record)
    record.value_json = dumps(value)
    if description:
        record.description = description
    record.updated_at = datetime.utcnow()
    session.commit()
    session.refresh(record)
    return record
