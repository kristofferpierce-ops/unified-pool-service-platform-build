from __future__ import annotations

from fastapi import APIRouter
from sqlmodel import Session

from app.core.database import create_db_and_tables, engine
from app.services.bootstrap import seed_defaults

router = APIRouter(prefix='/admin', tags=['admin'])


@router.post('/bootstrap')
def bootstrap() -> dict[str, str]:
    create_db_and_tables()
    with Session(engine) as session:
        seed_defaults(session)
    return {'status': 'bootstrapped'}
