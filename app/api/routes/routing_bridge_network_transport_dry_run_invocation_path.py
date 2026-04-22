from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.routing_bridge_network_transport_dry_run_invocation_path import (
    bridge_routing_network_transport_dry_run_invocation_path_status,
    build_bridge_routing_network_transport_dry_run_invocation_path_preview,
)

router = APIRouter(prefix="/front-desk/routing/bridge-network-transport-dry-run-invocation-path", tags=["front-desk-routing-bridge-network-transport-dry-run-invocation-path"])


class BridgeRoutingNetworkTransportDryRunInvocationPathRequest(BaseModel):
    interface_scaffold_release_checkpoint_path: str
    operator_name: str = ""
    transport_confirmation_phrase: str = ""


@router.get("/status")
def get_bridge_routing_network_transport_dry_run_invocation_path_status() -> dict:
    return bridge_routing_network_transport_dry_run_invocation_path_status()


@router.post("/preview")
def post_bridge_routing_network_transport_dry_run_invocation_path_preview(request: BridgeRoutingNetworkTransportDryRunInvocationPathRequest) -> dict:
    return build_bridge_routing_network_transport_dry_run_invocation_path_preview(
        interface_scaffold_release_checkpoint_path=request.interface_scaffold_release_checkpoint_path,
        operator_name=request.operator_name,
        transport_confirmation_phrase=request.transport_confirmation_phrase,
    )
