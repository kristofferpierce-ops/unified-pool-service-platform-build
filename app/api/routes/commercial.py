from __future__ import annotations

from fastapi import APIRouter
from sqlmodel import Session, select

from app.core.database import engine
from app.models.tables import CommercialDelivery, CommercialVendorOrder

router = APIRouter(prefix="/commercial", tags=["commercial"])


@router.get("/orders")
def get_orders() -> list[CommercialVendorOrder]:
    with Session(engine) as session:
        return list(session.exec(select(CommercialVendorOrder)).all())


@router.get("/deliveries")
def get_deliveries() -> list[CommercialDelivery]:
    with Session(engine) as session:
        return list(session.exec(select(CommercialDelivery)).all())
