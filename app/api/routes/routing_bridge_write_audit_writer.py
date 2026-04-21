from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter
from sqlmodel import Session

from app.core.database import engine
from app.services.routing_bridge_write_audit_writer import (
    bridge_routing_audit_writer_gate,
    preview_bridge_routing_audit_write,
    run_bridge_routing_audit_write,
)

router = APIRouter(prefix="/front-desk/routing/bridge-write-audit-writer", tags=["front-desk-routing-bridge-audit-writer"])


class BridgeRoutingAuditWriteRequest(BaseModel):
    plan_path: str
    dry_run: bool = True
    confirmation_phrase: str = ""


@router.get("/status")
def get_bridge_routing_audit_writer_status() -> dict:
    gate = bridge_routing_audit_writer_gate()
    return {
        **gate,
        "default_dry_run": True,
        "safe_default": "dry_run",
    }


@router.post("/run")
def post_bridge_routing_audit_writer_run(request: BridgeRoutingAuditWriteRequest) -> dict:
    with Session(engine) as session:
        if request.dry_run:
            return preview_bridge_routing_audit_write(session, plan_path=request.plan_path)
        return run_bridge_routing_audit_write(
            session,
            plan_path=request.plan_path,
            dry_run=False,
            confirmation_phrase=request.confirmation_phrase,
        )
