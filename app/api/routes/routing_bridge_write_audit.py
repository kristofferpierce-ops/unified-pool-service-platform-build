from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.core.database import engine
from app.services.routing_bridge_write_audit import (
    get_routing_bridge_write_audit,
    list_routing_bridge_write_audits,
    preview_audit_from_rehearsal,
    routing_bridge_write_audit_status,
)

router = APIRouter(prefix="/front-desk/routing/bridge-write-audit", tags=["front-desk-routing-bridge-audit"])


class BridgeWriteAuditPreviewRequest(BaseModel):
    rehearsal_row: dict[str, Any] = Field(default_factory=dict)


@router.get("/status")
def get_bridge_write_audit_status() -> dict:
    with Session(engine) as session:
        return routing_bridge_write_audit_status(session)


@router.get("")
def get_bridge_write_audits(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict:
    with Session(engine) as session:
        return list_routing_bridge_write_audits(session, limit=limit, offset=offset)


@router.get("/{audit_id}")
def get_bridge_write_audit_detail(audit_id: int) -> dict:
    with Session(engine) as session:
        audit = get_routing_bridge_write_audit(session, audit_id)
        if audit is None:
            raise HTTPException(status_code=404, detail="Routing bridge write audit not found")
        return audit


@router.post("/preview-from-rehearsal")
def post_bridge_write_audit_preview_from_rehearsal(request: BridgeWriteAuditPreviewRequest) -> dict:
    return preview_audit_from_rehearsal(request.rehearsal_row)
