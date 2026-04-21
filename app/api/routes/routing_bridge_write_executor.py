from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter

from app.services.routing_bridge_write_executor import (
    bridge_routing_write_executor_gate,
    preview_bridge_routing_write_execution,
)

router = APIRouter(prefix="/front-desk/routing/bridge-write-executor", tags=["front-desk-routing-bridge-executor"])


class BridgeRoutingWriteExecutorPreviewRequest(BaseModel):
    implementation_plan_path: str
    cutover_packet_path: str | None = None
    dry_run: bool = True
    confirmation_phrase: str = ""


@router.get("/status")
def get_bridge_routing_write_executor_status() -> dict:
    gate = bridge_routing_write_executor_gate()
    return {
        **gate,
        "executor_endpoint_available": True,
        "execution_endpoint_available": False,
    }


@router.post("/preview")
def post_bridge_routing_write_executor_preview(request: BridgeRoutingWriteExecutorPreviewRequest) -> dict:
    return preview_bridge_routing_write_execution(
        implementation_plan_path=request.implementation_plan_path,
        cutover_packet_path=request.cutover_packet_path,
        dry_run=request.dry_run,
        confirmation_phrase=request.confirmation_phrase,
    )
