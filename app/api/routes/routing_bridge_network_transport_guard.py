from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.routing_bridge_network_transport_guard import (
    bridge_routing_network_transport_guard_status,
    build_bridge_routing_network_transport_guard_preview,
)

router = APIRouter(prefix="/front-desk/routing/bridge-network-transport-guard", tags=["front-desk-routing-bridge-network-transport-guard"])


class BridgeRoutingNetworkTransportGuardPreviewRequest(BaseModel):
    release_checkpoint_path: str
    operator_name: str = ""
    transport_confirmation_phrase: str = ""
    bridge_write_confirmation_phrase: str = ""


@router.get("/status")
def get_bridge_routing_network_transport_guard_status() -> dict:
    return bridge_routing_network_transport_guard_status()


@router.post("/preview")
def post_bridge_routing_network_transport_guard_preview(request: BridgeRoutingNetworkTransportGuardPreviewRequest) -> dict:
    return build_bridge_routing_network_transport_guard_preview(
        release_checkpoint_path=request.release_checkpoint_path,
        operator_name=request.operator_name,
        transport_confirmation_phrase=request.transport_confirmation_phrase,
        bridge_write_confirmation_phrase=request.bridge_write_confirmation_phrase,
    )
