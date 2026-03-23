from __future__ import annotations

from fastapi import APIRouter
from sqlmodel import Session, select

from app.core.database import engine
from app.models.tables import BaselineModelVersion

router = APIRouter(prefix="/baseline-models", tags=["baseline"])


@router.get("/")
def get_baseline_models() -> list[BaselineModelVersion]:
    with Session(engine) as session:
        return list(session.exec(select(BaselineModelVersion)).all())
