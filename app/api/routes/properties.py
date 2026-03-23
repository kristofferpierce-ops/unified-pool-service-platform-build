from __future__ import annotations

from fastapi import APIRouter
from sqlmodel import Session, select

from app.core.database import engine
from app.models.tables import Account, PoolVessel, Property

router = APIRouter(prefix="/properties", tags=["properties"])


@router.get("/accounts")
def get_accounts() -> list[Account]:
    with Session(engine) as session:
        return list(session.exec(select(Account)).all())


@router.get("/")
def get_properties() -> list[Property]:
    with Session(engine) as session:
        return list(session.exec(select(Property)).all())


@router.get("/vessels")
def get_vessels() -> list[PoolVessel]:
    with Session(engine) as session:
        return list(session.exec(select(PoolVessel)).all())
