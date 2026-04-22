from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.routing_bridge_network_transport_interface_scaffold import (
    bridge_routing_network_transport_interface_scaffold_status,
    build_bridge_routing_network_transport_interface_scaffold_preview,
)

router = APIRouter(prefix="/front-desk/routing/bridge-network-transport-interface-scaffold", tags=["front-desk-routing-bridge-network-transport-interface-scaffold"])


class BridgeRoutingNetworkTransportInterfaceScaffoldRequest(BaseModel):
    implementation_plan_path: str
    operator_name: str = ""
    transport_confirmation_phrase: str = ""


@router.get("/status")
def get_bridge_routing_network_transport_interface_scaffold_status() -> dict:
    return bridge_routing_network_transport_interface_scaffold_status()


@router.post("/preview")
def post_bridge_routing_network_transport_interface_scaffold_preview(request: BridgeRoutingNetworkTransportInterfaceScaffoldRequest) -> dict:
    return build_bridge_routing_network_transport_interface_scaffold_preview(
        implementation_plan_path=request.implementation_plan_path,
        operator_name=request.operator_name,
        transport_confirmation_phrase=request.transport_confirmation_phrase,
    )
