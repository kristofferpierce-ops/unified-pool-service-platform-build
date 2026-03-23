from __future__ import annotations

from fastapi import APIRouter
from sqlmodel import Session

from app.core.database import engine
from app.models.tables import ExpenseItem
from app.services.expenses import list_expenses

router = APIRouter(prefix="/expenses", tags=["expenses"])


@router.get("/")
def get_expenses() -> list[ExpenseItem]:
    with Session(engine) as session:
        return list_expenses(session)
