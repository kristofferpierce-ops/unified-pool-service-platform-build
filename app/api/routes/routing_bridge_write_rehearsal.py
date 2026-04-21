from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.routing_bridge_write_rehearsal import (
    bridge_routing_write_rehearsal_status,
    rehearse_bridge_routing_write,
)

router = APIRouter(prefix="/front-desk/routing/bridge-write-rehearsal", tags=["front-desk-routing-bridge-rehearsal"])


class BridgeRoutingWriteRehearsalRequest(BaseModel):
    preview_row: dict[str, Any] = Field(default_factory=dict)
    confirmation_phrase: str = ""


@router.get("/status")
def get_bridge_routing_write_rehearsal_status() -> dict:
    return bridge_routing_write_rehearsal_status()


@router.post("/rehearse")
def post_bridge_routing_write_rehearsal(request: BridgeRoutingWriteRehearsalRequest) -> dict:
    return rehearse_bridge_routing_write(
        preview_row=request.preview_row,
        confirmation_phrase=request.confirmation_phrase,
    )
