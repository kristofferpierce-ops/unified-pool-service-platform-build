from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter
from sqlmodel import Session

from app.core.database import engine
from app.services.commercial import direct_delivery_report_dataframe

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/commercial-direct-deliveries")
def direct_deliveries(start_date: str, end_date: str) -> list[dict]:
    start_dt = datetime.fromisoformat(start_date)
    end_dt = datetime.fromisoformat(end_date)
    with Session(engine) as session:
        df = direct_delivery_report_dataframe(session, start_dt, end_dt)
        return df.to_dict(orient="records")
