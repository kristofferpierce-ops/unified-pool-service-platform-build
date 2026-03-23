from fastapi import APIRouter
from sqlmodel import select

from app.core.database import get_session
from app.models.tables import CompanyExpense, SystemSetting

router = APIRouter()


@router.get("/settings")
def list_settings():
    with get_session() as session:
        return list(session.exec(select(SystemSetting)).all())


@router.get("/expenses")
def list_expenses():
    with get_session() as session:
        return list(session.exec(select(CompanyExpense)).all())
