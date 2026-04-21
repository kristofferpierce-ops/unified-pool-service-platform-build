from __future__ import annotations

from fastapi import APIRouter, Query
from sqlmodel import Session

from app.core.database import engine
from app.services.routing_bridge_apply_preview import (
    list_routing_bridge_apply_preview,
    routing_bridge_apply_preview_status,
)

router = APIRouter(prefix="/front-desk/routing/bridge-apply-preview", tags=["front-desk-routing-bridge-preview"])


@router.get("/status")
def get_bridge_apply_preview_status() -> dict:
    with Session(engine) as session:
        return routing_bridge_apply_preview_status(session)


@router.get("")
def get_bridge_apply_preview(
    limit: int = Query(default=250, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    include_blocked: bool = Query(default=True),
) -> dict:
    with Session(engine) as session:
        return list_routing_bridge_apply_preview(
            session,
            limit=limit,
            offset=offset,
            include_blocked=include_blocked,
        )
