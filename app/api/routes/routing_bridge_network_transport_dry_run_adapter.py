from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.routing_bridge_network_transport_dry_run_adapter import (
    bridge_routing_network_transport_dry_run_adapter_status,
    build_bridge_routing_network_transport_dry_run_adapter,
)

router = APIRouter(prefix="/front-desk/routing/bridge-network-transport-dry-run-adapter", tags=["front-desk-routing-bridge-network-transport-dry-run-adapter"])


class BridgeRoutingNetworkTransportDryRunAdapterRequest(BaseModel):
    guard_report_path: str
    operator_name: str = ""
    transport_confirmation_phrase: str = ""


@router.get("/status")
def get_bridge_routing_network_transport_dry_run_adapter_status() -> dict:
    return bridge_routing_network_transport_dry_run_adapter_status()


@router.post("/simulate")
def post_bridge_routing_network_transport_dry_run_adapter_simulate(request: BridgeRoutingNetworkTransportDryRunAdapterRequest) -> dict:
    return build_bridge_routing_network_transport_dry_run_adapter(
        guard_report_path=request.guard_report_path,
        operator_name=request.operator_name,
        transport_confirmation_phrase=request.transport_confirmation_phrase,
    )
